from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

import psycopg

OutcomeValue = Literal["accepted", "rejected", "ignored"]


@dataclass(frozen=True)
class RecordedOutcome:
    outcome_id: UUID
    brief_id: UUID
    tenant_id: str | None
    outcome: OutcomeValue
    note: str | None
    created_at: datetime | None
    deduplicated: bool = False


class BriefOutcomeRepository:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def record(
        self,
        brief_id: UUID,
        outcome: OutcomeValue,
        note: str | None = None,
        tenant_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> UUID:
        """Append an outcome for a brief. Append-only — never overwrites.

        If idempotency_key is provided and a row with the same (brief_id,
        idempotency_key) already exists, the existing outcome ID is returned
        without error (idempotent retry).

        Raises:
            ValueError: brief_id not found in cortex_briefs.
            ValueError: tenant_id does not match the brief's stored tenant_id.
        """
        # Brief existence + tenant validation
        brief_row = self._conn.execute(
            "SELECT tenant_id FROM cortex_briefs WHERE brief_id = %s",
            (str(brief_id),),
        ).fetchone()
        if brief_row is None:
            raise ValueError(f"brief_id not found: {brief_id}")
        stored_tenant = str(brief_row[0]) if brief_row[0] else None
        if stored_tenant is not None and tenant_id is not None and stored_tenant != tenant_id:
            raise ValueError(
                f"tenant_id mismatch: brief belongs to tenant {stored_tenant!r}, "
                f"got {tenant_id!r}"
            )

        # Idempotency: return existing ID if already recorded with this key
        if idempotency_key is not None:
            existing = self._conn.execute(
                "SELECT id FROM cortex_brief_outcomes WHERE brief_id = %s AND idempotency_key = %s",
                (str(brief_id), idempotency_key),
            ).fetchone()
            if existing is not None:
                return UUID(str(existing[0]))

        row = self._conn.execute(
            """
            INSERT INTO cortex_brief_outcomes (brief_id, tenant_id, outcome, note, idempotency_key)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (str(brief_id), tenant_id, outcome, note, idempotency_key),
        ).fetchone()
        self._conn.commit()
        assert row is not None
        return UUID(str(row[0]))

    def record_with_ack(
        self,
        brief_id: UUID,
        outcome: OutcomeValue,
        note: str | None = None,
        tenant_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> RecordedOutcome:
        brief_row = self._conn.execute(
            "SELECT tenant_id FROM cortex_briefs WHERE brief_id = %s",
            (str(brief_id),),
        ).fetchone()
        if brief_row is None:
            raise ValueError(f"brief_id not found: {brief_id}")
        stored_tenant = str(brief_row[0]) if brief_row[0] else None
        if stored_tenant is not None and tenant_id is not None and stored_tenant != tenant_id:
            raise ValueError(
                f"tenant_id mismatch: brief belongs to tenant {stored_tenant!r}, "
                f"got {tenant_id!r}"
            )

        if idempotency_key is not None:
            existing = self._conn.execute(
                """
                SELECT id, tenant_id, outcome, note, created_at
                FROM cortex_brief_outcomes
                WHERE brief_id = %s AND idempotency_key = %s
                """,
                (str(brief_id), idempotency_key),
            ).fetchone()
            if existing is not None:
                return RecordedOutcome(
                    outcome_id=UUID(str(existing[0])),
                    brief_id=brief_id,
                    tenant_id=str(existing[1]) if existing[1] else None,
                    outcome=str(existing[2]),  # type: ignore[arg-type]
                    note=existing[3],
                    created_at=existing[4],
                    deduplicated=True,
                )

        row = self._conn.execute(
            """
            INSERT INTO cortex_brief_outcomes (brief_id, tenant_id, outcome, note, idempotency_key)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, tenant_id, outcome, note, created_at
            """,
            (str(brief_id), tenant_id, outcome, note, idempotency_key),
        ).fetchone()
        self._conn.commit()
        assert row is not None
        return RecordedOutcome(
            outcome_id=UUID(str(row[0])),
            brief_id=brief_id,
            tenant_id=str(row[1]) if row[1] else None,
            outcome=str(row[2]),  # type: ignore[arg-type]
            note=row[3],
            created_at=row[4],
            deduplicated=False,
        )

    def get_for_brief(
        self, brief_id: UUID, tenant_id: str | None = None
    ) -> list[dict]:
        """Return all outcomes for a brief ordered by created_at asc."""
        from chips.tenant import build_tenant_scope
        scoped = build_tenant_scope(["brief_id = %s"], [str(brief_id)], tenant_id)
        rows = self._conn.execute(  # type: ignore[arg-type]
            f"SELECT id, brief_id, tenant_id, outcome, note, created_at FROM cortex_brief_outcomes WHERE {' AND '.join(scoped.conditions)} ORDER BY created_at ASC, id ASC",
            tuple(scoped.params),
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
