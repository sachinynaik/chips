"""Phase 0: ConstraintRepository — durable anti-regression / policy constraints.

The dynamic policy layer beside the static PolicyLoader. Add is idempotent
(SELECT-then-insert for friendly behavior) and race-safe (DB partial-unique index
on active rows; UniqueViolation falls back to the existing row). Retire is soft.
"""
from __future__ import annotations

import json
from uuid import UUID

import psycopg

from chips.compiler.constraints import dedup_hash
from chips.compiler.models import Constraint

_SELECT_COLS = (
    "id, tenant_id, scope_pattern, kind, constraint_text, reason, "
    "source_kind, source_ref, target, status, created_at"
)


class ConstraintRepository:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def add(
        self,
        *,
        scope_pattern: str,
        kind: str,
        text: str,
        reason: str | None = None,
        source_kind: str | None = None,
        source_ref: str | None = None,
        target: dict | None = None,
        tenant_id: str | None = None,
    ) -> UUID:
        """Insert a constraint, idempotent on the dedup identity (active rows)."""
        dh = dedup_hash(tenant_id, scope_pattern, kind, text, target)
        existing = self._find_active(dh)
        if existing is not None:
            return existing
        try:
            row = self._conn.execute(
                """
                INSERT INTO cortex_constraints
                    (tenant_id, scope_pattern, kind, constraint_text, reason,
                     source_kind, source_ref, target, dedup_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                RETURNING id
                """,
                (
                    tenant_id, scope_pattern, kind, text, reason,
                    source_kind, source_ref, json.dumps(target or {}), dh,
                ),
            ).fetchone()
            self._conn.commit()
            assert row is not None
            return UUID(str(row[0]))
        except psycopg.errors.UniqueViolation:
            # Lost a race to a concurrent active insert — return the winner.
            self._conn.rollback()
            existing = self._find_active(dh)
            if existing is None:
                raise
            return existing

    def retire(self, constraint_id: UUID, tenant_id: str | None = None) -> bool:
        """Soft-retire: status active → superseded (never hard-delete; audit trail)."""
        from chips.tenant import build_tenant_scope

        scoped = build_tenant_scope(["id = %s"], [str(constraint_id)], tenant_id)
        self._conn.execute(  # type: ignore[arg-type]
            f"UPDATE cortex_constraints SET status = 'superseded', updated_at = now() "
            f"WHERE {' AND '.join(scoped.conditions)}",
            tuple(scoped.params),
        )
        self._conn.commit()
        return True

    def for_scope(self, scope: str | None, tenant_id: str | None = None) -> list[Constraint]:
        """Active constraints for a scope: '*' (global) or exact match, mirroring
        PolicyLoader.for_scope; tenant-isolated; ordered recent-first.
        """
        from chips.tenant import build_tenant_scope

        scoped = build_tenant_scope(
            ["(scope_pattern = '*' OR scope_pattern = %s)", "status = 'active'"],
            [scope],
            tenant_id,
        )
        rows = self._conn.execute(  # type: ignore[arg-type]
            f"SELECT {_SELECT_COLS} FROM cortex_constraints "
            f"WHERE {' AND '.join(scoped.conditions)} "
            f"ORDER BY created_at DESC, id ASC",
            tuple(scoped.params),
        ).fetchall()
        return [self._row_to_constraint(r) for r in rows]

    def _find_active(self, dedup: str) -> UUID | None:
        row = self._conn.execute(
            "SELECT id FROM cortex_constraints WHERE dedup_hash = %s AND status = 'active'",
            (dedup,),
        ).fetchone()
        return UUID(str(row[0])) if row else None

    @staticmethod
    def _row_to_constraint(r) -> Constraint:
        return Constraint(
            id=UUID(str(r[0])),
            tenant_id=str(r[1]) if r[1] else None,
            scope_pattern=r[2],
            kind=r[3],
            text=r[4],
            reason=r[5],
            source_kind=r[6],
            source_ref=r[7],
            target=r[8] or {},
            status=r[9],
            created_at=r[10],
        )
