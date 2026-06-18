from __future__ import annotations

import psycopg

from chips.mcp.tools.diffs import get_diffs_for_scope as _get_diffs_for_scope
from chips.mcp.tools.memory import search_memory as _search_memory


def retrieve_memories(
    conn: psycopg.Connection,
    embedding: list[float],
    scope: str | None = None,
    limit: int = 5,
    tenant_id: str | None = None,
) -> list[dict]:
    return _search_memory(conn, embedding, scope=scope, limit=limit, tenant_id=tenant_id)


def retrieve_file_signals(
    conn: psycopg.Connection,
    files: list[str],
    tenant_id: str | None = None,
) -> list[dict]:
    if not files:
        return []
    from chips.tenant import build_tenant_scope
    scoped = build_tenant_scope(["file_path = ANY(%s)"], [files], tenant_id)
    rows = conn.execute(  # type: ignore[arg-type]
        f"""
        SELECT
            file_path,
            churn_score,
            cochange_entropy,
            (
                SELECT COUNT(DISTINCT g.sha)
                FROM cortex_git_commits g
                JOIN cortex_defect_corpus d ON d.sha = g.sha
                WHERE g.files_changed && ARRAY[cortex_file_signals.file_path]
                  AND (
                    cardinality(d.issue_refs) > 0
                    OR d.revert_of_sha IS NOT NULL
                    OR d.has_hotfix_keyword = TRUE
                    OR d.has_incident_keyword = TRUE
                  )
            ) AS defect_history_count,
            failure_count,
            last_changed_at
        FROM cortex_file_signals
        WHERE {' AND '.join(scoped.conditions)}
        """,
        tuple(scoped.params),
    ).fetchall()
    return [
        {
            "file_path": row[0],
            "churn_score": row[1],
            "cochange_entropy": row[2],
            "defect_history_count": row[3],
            "fragility": _fragility_score(row[1], row[2], row[3]),
            "failure_count": row[4],
            "last_changed_at": row[5],
        }
        for row in rows
    ]


def _fragility_score(
    churn_score: float | None,
    cochange_entropy: float | None,
    defect_history_count: int | None,
) -> float:
    churn = float(churn_score or 0.0)
    entropy = float(cochange_entropy or 0.0)
    defect_presence = 1.0 if (defect_history_count or 0) > 0 else 0.0
    raw = (0.45 * churn) + (0.35 * entropy) + (0.15 * defect_presence)
    return round(min(raw, 1.0), 2)


def retrieve_diffs(
    conn: psycopg.Connection,
    scope: str | None = None,
    limit: int = 10,
    tenant_id: str | None = None,
) -> list[dict]:
    return _get_diffs_for_scope(conn, scope=scope, limit=limit, tenant_id=tenant_id)["commits"]


def retrieve_cochanges(
    conn: psycopg.Connection,
    files: list[str],
    limit: int = 10,
    tenant_id: str | None = None,
) -> list[dict]:
    if not files:
        return []
    from chips.tenant import build_tenant_scope
    scoped = build_tenant_scope(
        ["(file_a = ANY(%s) OR file_b = ANY(%s))"],
        [files, files],
        tenant_id,
    )
    rows = conn.execute(  # type: ignore[arg-type]
        f"SELECT file_a, file_b, frequency, last_seen_at FROM cortex_cochange_pairs WHERE {' AND '.join(scoped.conditions)} ORDER BY frequency DESC LIMIT %s",
        (*scoped.params, limit),
    ).fetchall()
    return [
        {"file_a": row[0], "file_b": row[1], "frequency": row[2], "last_seen_at": row[3]}
        for row in rows
    ]
