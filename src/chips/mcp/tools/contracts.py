from __future__ import annotations

import psycopg


def get_contracts(
    conn: psycopg.Connection,
    scope: str | None = None,
    limit: int = 20,
) -> dict:
    """Return contract-type memories, optionally filtered by scope."""
    if scope is not None:
        rows = conn.execute(
            """
            SELECT id, scope, content, tags, confidence
            FROM cortex_memories
            WHERE type = 'contract' AND archived_at IS NULL AND scope = %s
            ORDER BY confidence DESC
            LIMIT %s
            """,
            (scope, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT id, scope, content, tags, confidence
            FROM cortex_memories
            WHERE type = 'contract' AND archived_at IS NULL
            ORDER BY confidence DESC
            LIMIT %s
            """,
            (limit,),
        ).fetchall()

    return {
        "contracts": [
            {
                "id": str(id_),
                "scope": sc,
                "content": content,
                "tags": list(tags) if tags else [],
                "confidence": confidence,
            }
            for id_, sc, content, tags, confidence in rows
        ],
        "scope": scope,
        "status": "ok",
    }
