from __future__ import annotations

from typing import Literal
from uuid import UUID

import psycopg

OutcomeValue = Literal["accepted", "rejected", "ignored"]


class BriefOutcomeRepository:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def record(
        self,
        brief_id: UUID,
        outcome: OutcomeValue,
        note: str | None = None,
        tenant_id: str | None = None,
    ) -> UUID:
        """Append an outcome for a brief. Append-only — never overwrites."""
        row = self._conn.execute(
            """
            INSERT INTO cortex_brief_outcomes (brief_id, tenant_id, outcome, note)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (str(brief_id), tenant_id, outcome, note),
        ).fetchone()
        self._conn.commit()
        assert row is not None
        return UUID(str(row[0]))

    def get_for_brief(
        self, brief_id: UUID, tenant_id: str | None = None
    ) -> list[dict]:
        """Return all outcomes for a brief ordered by created_at asc."""
        conditions = ["brief_id = %s"]
        params: list = [str(brief_id)]
        if tenant_id is not None:
            conditions.append("tenant_id = %s")
            params.append(tenant_id)
        rows = self._conn.execute(  # type: ignore[arg-type]
            f"SELECT id, brief_id, tenant_id, outcome, note, created_at FROM cortex_brief_outcomes WHERE {' AND '.join(conditions)} ORDER BY created_at ASC, id ASC",
            tuple(params),
        ).fetchall()
        return [
            {
                "id": str(row[0]),
                "brief_id": str(row[1]),
                "tenant_id": str(row[2]) if row[2] else None,
                "outcome": row[3],
                "note": row[4],
                "created_at": row[5].isoformat() if row[5] else None,
            }
            for row in rows
        ]
