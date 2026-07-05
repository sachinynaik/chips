"""GitHub issue-metadata capture for defect-label verification.

Raw capture only: fetches issue metadata for refs already present in
cortex_defect_corpus and stores it in cortex_issue_refs. The defect label
remains a query over stored data (label_tier_sql); nothing here decides
anything. Statuses are truthful (the L11 lesson): a failed fetch is recorded
as failed, never as "no issue". Missing metadata degrades a label tier, it
never deletes evidence.

See docs/design_docs/05_07/chips-defect-corpus-harvest-spec.md (Gaps B, C).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

import httpx

_GITHUB_NUMERIC_RE = re.compile(r"^#(\d+)$")

_API_BASE = "https://api.github.com"


@dataclass(frozen=True)
class IssueRefRecord:
    ref: str
    repo: str
    fetch_status: str  # ok / not_found / rate_limited / failed / skipped
    issue_number: int | None = None
    state: str | None = None
    labels: list[str] | None = None
    issue_type: str | None = None
    title: str | None = None
    closed_at: str | None = None
    raw: dict | None = None


def parse_github_issue_number(ref: str) -> int | None:
    """'#123' -> 123. Key-style refs (JIRA etc.) are not GitHub-fetchable."""
    match = _GITHUB_NUMERIC_RE.match(ref.strip())
    return int(match.group(1)) if match else None


class IssueRefFetcher:
    def __init__(
        self,
        repo: str,
        *,
        token: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self._repo = repo
        self._token = token
        self._client = client

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github+json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def fetch(self, ref: str) -> IssueRefRecord:
        number = parse_github_issue_number(ref)
        if number is None:
            # Non-GitHub tracker ref: recorded, never silently dropped.
            return IssueRefRecord(ref=ref, repo=self._repo, fetch_status="skipped")

        url = f"{_API_BASE}/repos/{self._repo}/issues/{number}"
        try:
            if self._client is not None:
                resp = self._client.get(url, headers=self._headers())
            else:
                with httpx.Client() as client:
                    resp = client.get(url, headers=self._headers())
        except httpx.HTTPError:
            return IssueRefRecord(
                ref=ref, repo=self._repo, issue_number=number, fetch_status="failed"
            )

        if resp.status_code == 404:
            return IssueRefRecord(
                ref=ref, repo=self._repo, issue_number=number, fetch_status="not_found"
            )
        if resp.status_code in (403, 429):
            return IssueRefRecord(
                ref=ref, repo=self._repo, issue_number=number, fetch_status="rate_limited"
            )
        if resp.status_code != 200:
            return IssueRefRecord(
                ref=ref, repo=self._repo, issue_number=number, fetch_status="failed"
            )

        payload = resp.json()
        return IssueRefRecord(
            ref=ref,
            repo=self._repo,
            issue_number=number,
            fetch_status="ok",
            state=payload.get("state"),
            labels=sorted(
                label.get("name", "")
                for label in payload.get("labels", [])
                if isinstance(label, dict)
            ),
            issue_type=(payload.get("type") or {}).get("name")
            if isinstance(payload.get("type"), dict)
            else payload.get("type"),
            title=payload.get("title"),
            closed_at=payload.get("closed_at"),
            raw=payload,
        )


def pending_refs(conn, repo: str, *, limit: int = 50) -> list[str]:
    """Refs present in the defect corpus with no cortex_issue_refs row yet.

    rate_limited rows are retried (re-selected); ok/not_found/failed/skipped
    are terminal until manually cleared.
    """
    rows = conn.execute(
        """
        SELECT DISTINCT ref
        FROM (
            SELECT unnest(issue_refs) AS ref FROM cortex_defect_corpus
        ) refs
        LEFT JOIN cortex_issue_refs i
            ON i.ref = refs.ref AND i.repo = %s
        WHERE i.ref IS NULL OR i.fetch_status = 'rate_limited'
        ORDER BY ref
        LIMIT %s
        """,
        (repo, limit),
    ).fetchall()
    return [row[0] for row in rows]


def store_issue_ref(conn, record: IssueRefRecord) -> None:
    conn.execute(
        """
        INSERT INTO cortex_issue_refs (
            ref, repo, issue_number, state, labels, issue_type,
            title, closed_at, fetch_status, raw, fetched_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
        ON CONFLICT (repo, ref) DO UPDATE SET
            issue_number = EXCLUDED.issue_number,
            state        = EXCLUDED.state,
            labels       = EXCLUDED.labels,
            issue_type   = EXCLUDED.issue_type,
            title        = EXCLUDED.title,
            closed_at    = EXCLUDED.closed_at,
            fetch_status = EXCLUDED.fetch_status,
            raw          = EXCLUDED.raw,
            fetched_at   = now()
        """,
        (
            record.ref,
            record.repo,
            record.issue_number,
            record.state,
            record.labels or [],
            record.issue_type,
            record.title,
            record.closed_at,
            record.fetch_status,
            json.dumps(record.raw) if record.raw is not None else None,
        ),
    )


def harvest_issue_refs(conn, repo: str, *, fetcher: IssueRefFetcher | None = None, limit: int = 50) -> dict:
    """Batch: fetch + store pending refs. Never raises; returns truthful counts."""
    fetcher = fetcher or IssueRefFetcher(repo)
    counts = {"ok": 0, "not_found": 0, "rate_limited": 0, "failed": 0, "skipped": 0}
    for ref in pending_refs(conn, repo, limit=limit):
        record = fetcher.fetch(ref)
        store_issue_ref(conn, record)
        counts[record.fetch_status] += 1
        if record.fetch_status == "rate_limited":
            break  # stop the batch; remaining refs stay pending
    return counts


_BUG_LABEL_SQL = (
    "EXISTS (SELECT 1 FROM unnest({i}.labels) l "
    "WHERE l ILIKE '%%bug%%' OR l ILIKE '%%defect%%')"
)


def label_tier_sql(corpus_alias: str = "d", issue_alias: str = "i") -> str:
    """Tier CASE expression per harvest-spec Gap C. Computed at query time,
    never stored — broadening a tier is a query edit, not a re-harvest.

    T1 issue-verified bug > T2 issue-linked + keyword > T3 revert-linked >
    T4 keyword-only hotfix/incident; NULL = no defect evidence.
    """
    bug_label = _BUG_LABEL_SQL.format(i=issue_alias)
    return (
        "CASE "
        f"WHEN {issue_alias}.fetch_status = 'ok' AND {bug_label} THEN 'T1' "
        f"WHEN cardinality({corpus_alias}.issue_refs) > 0 "
        f"AND ({corpus_alias}.has_bug_keyword = TRUE OR {corpus_alias}.has_defect_keyword = TRUE) THEN 'T2' "
        f"WHEN {corpus_alias}.revert_of_sha IS NOT NULL THEN 'T3' "
        f"WHEN {corpus_alias}.has_hotfix_keyword = TRUE OR {corpus_alias}.has_incident_keyword = TRUE THEN 'T4' "
        "ELSE NULL END"
    )
