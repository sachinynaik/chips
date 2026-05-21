from __future__ import annotations

import psycopg

_VALID_OUTCOMES = ("success", "partial", "failure", "abandoned")


def get_brief(conn: psycopg.Connection, brief_id: str) -> dict:
    row = conn.execute(
        """
        SELECT brief_id, task, scope, generated_at, latency_ms,
               compressed_context, post_task_outcome, outcome_recorded_at
        FROM cortex_briefs
        WHERE brief_id = %s
        """,
        (brief_id,),
    ).fetchone()
    if row is None:
        return {"status": "not_found", "brief_id": brief_id}
    return {
        "status": "ok",
        "brief_id": str(row[0]),
        "task": row[1],
        "scope": row[2],
        "generated_at": str(row[3]) if row[3] else None,
        "latency_ms": row[4],
        "compressed_context": row[5],
        "post_task_outcome": row[6],
        "outcome_recorded_at": str(row[7]) if row[7] else None,
    }


def record_outcome(
    conn: psycopg.Connection,
    brief_id: str,
    outcome: str,
    notes: str | None = None,
) -> dict:
    if outcome not in _VALID_OUTCOMES:
        return {
            "status": "error",
            "message": f"Invalid outcome {outcome!r}. Must be one of: {_VALID_OUTCOMES}",
        }
    result = conn.execute(
        """
        UPDATE cortex_briefs
        SET post_task_outcome    = %s,
            outcome_recorded_at  = now(),
            soft_context         = COALESCE(soft_context || E'\\n' || %s, %s)
        WHERE brief_id = %s
        """,
        (outcome, notes, notes, brief_id),
    )
    if result.rowcount == 0:
        return {"status": "not_found", "brief_id": brief_id}
    conn.commit()
    return {"status": "ok", "brief_id": brief_id, "outcome": outcome}
