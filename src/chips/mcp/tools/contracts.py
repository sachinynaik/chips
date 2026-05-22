from __future__ import annotations

import psycopg


def get_contracts(
    conn: psycopg.Connection,
    scope: str | None = None,
    limit: int = 20,
    tenant_id: str | None = None,
) -> dict:
    """Return contract-type memories, optionally filtered by scope and tenant."""
    conditions = ["type = 'contract'", "archived_at IS NULL"]
    params: list = []

    if scope is not None:
        conditions.append("scope = %s")
        params.append(scope)
    if tenant_id is not None:
        conditions.append("tenant_id = %s")
        params.append(tenant_id)
    params.append(limit)

    sql = f"""
        SELECT id, scope, content, tags, confidence
        FROM cortex_memories
        WHERE {' AND '.join(conditions)}
        ORDER BY confidence DESC
        LIMIT %s
    """
    rows = conn.execute(sql, tuple(params)).fetchall()  # type: ignore[arg-type]

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
