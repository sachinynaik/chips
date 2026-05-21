from __future__ import annotations

import psycopg

from chips.mcp.tools.diffs import get_diffs_for_scope as _get_diffs_for_scope
from chips.mcp.tools.memory import search_memory as _search_memory


def retrieve_memories(
    conn: psycopg.Connection,
    embedding: list[float],
    scope: str | None = None,
    limit: int = 5,
) -> list[dict]:
    return _search_memory(conn, embedding, scope=scope, limit=limit)


def retrieve_file_signals(
    conn: psycopg.Connection,
    files: list[str],
) -> list[dict]:
    if not files:
        return []
    rows = conn.execute(
        """
        SELECT file_path, churn_score, failure_count, last_changed_at
        FROM cortex_file_signals
        WHERE file_path = ANY(%s)
        """,
        (files,),
    ).fetchall()
    return [
        {
            "file_path": row[0],
            "churn_score": row[1],
            "failure_count": row[2],
            "last_changed_at": row[3],
        }
        for row in rows
    ]


def retrieve_diffs(
    conn: psycopg.Connection,
    scope: str | None = None,
    limit: int = 10,
) -> list[dict]:
    return _get_diffs_for_scope(conn, scope=scope, limit=limit)["commits"]


def retrieve_cochanges(
    conn: psycopg.Connection,
    files: list[str],
    limit: int = 10,
) -> list[dict]:
    if not files:
        return []
    rows = conn.execute(
        """
        SELECT file_a, file_b, frequency, last_seen_at
        FROM cortex_cochange_pairs
        WHERE file_a = ANY(%s) OR file_b = ANY(%s)
        ORDER BY frequency DESC
        LIMIT %s
        """,
        (files, files, limit),
    ).fetchall()
    return [
        {"file_a": row[0], "file_b": row[1], "frequency": row[2], "last_seen_at": row[3]}
        for row in rows
    ]
