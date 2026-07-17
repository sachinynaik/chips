from __future__ import annotations

from datetime import datetime

import psycopg

from chips.tenant import build_tenant_scope
from chips.verifier.durability import AdverseEvent


def adverse_events_for_files(
    conn: psycopg.Connection,
    files: list[str],
    after: datetime,
    before: datetime,
    tenant_id: str | None = None,
) -> list[AdverseEvent]:
    """Return AdverseEvents for revert/hotfix/bug/defect commits that touched any of `files`
    in the half-open window [after, before). One AdverseEvent per (matched file, commit).
    Deterministic order. Empty `files` -> []."""
    if not files:
        return []

    conditions: list[str] = [
        "g.committed_at >= %s",
        "g.committed_at < %s",
        "g.files_changed && %s::text[]",
        "(d.revert_of_sha IS NOT NULL OR d.has_hotfix_keyword "
        "OR d.has_bug_keyword OR d.has_defect_keyword)",
    ]
    params: list = [after, before, files]

    scope = build_tenant_scope(conditions, params, tenant_id, column="d.tenant_id")

    rows = conn.execute(
        f"""
        SELECT g.sha, g.committed_at, g.files_changed, d.revert_of_sha
        FROM cortex_git_commits g
        JOIN cortex_defect_corpus d ON g.sha = d.sha
        WHERE {' AND '.join(scope.conditions)}
        """,
        tuple(scope.params),
    ).fetchall()

    requested = set(files)
    events: list[AdverseEvent] = []
    for sha, committed_at, files_changed, revert_of_sha in rows:
        changed = set(files_changed) if files_changed else set()
        kind = "revert" if revert_of_sha else "hotfix"
        for file_path in sorted(changed & requested):
            events.append(
                AdverseEvent(
                    file_path=file_path,
                    occurred_at=committed_at,
                    kind=kind,
                    ref=sha,
                )
            )

    events.sort(key=lambda event: (event.occurred_at, event.file_path, event.ref))
    return events
