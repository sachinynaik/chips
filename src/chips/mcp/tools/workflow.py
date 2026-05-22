from __future__ import annotations

import os

import psycopg


def get_workflow_state(scope: str | None = None) -> dict:
    """Return failed/pending DBOS workflows. Returns status 'unavailable' if unconfigured."""
    db_url = os.getenv("DBOS_DB_URL")
    if not db_url:
        return {"workflows": [], "scope": scope, "status": "unavailable"}

    conn = None
    try:
        conn = psycopg.connect(db_url)
        if scope:
            rows = conn.execute(
                """
                SELECT workflow_uuid, status, name, updated_at
                FROM dbos.workflow_status
                WHERE status IN ('ERROR', 'RETRIES_EXCEEDED', 'PENDING')
                  AND name ILIKE %s
                ORDER BY updated_at DESC
                LIMIT 20
                """,
                (f"%{scope}%",),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT workflow_uuid, status, name, updated_at
                FROM dbos.workflow_status
                WHERE status IN ('ERROR', 'RETRIES_EXCEEDED', 'PENDING')
                ORDER BY updated_at DESC
                LIMIT 20
                """,
                (),
            ).fetchall()

        return {
            "workflows": [
                {
                    "workflow_uuid": wf_uuid,
                    "status": status,
                    "name": name,
                    "updated_at": updated_at.isoformat() if updated_at else None,
                }
                for wf_uuid, status, name, updated_at in rows
            ],
            "scope": scope,
            "status": "ok",
        }
    except Exception as exc:
        return {"workflows": [], "scope": scope, "status": f"error: {type(exc).__name__}"}
    finally:
        if conn is not None:
            conn.close()
