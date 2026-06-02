"""Foundation: DecisionLogRepository — append-only policy decision/reward log.

One row per brief decision (cortex_decision_log, migration 008). Foundation
writes only context/action/propensity/policy_version/evidence/latency with a
versioned feature schema; the reward-consuming columns stay NULL until the
Activation phase (Phase-3 verifier). Mirrors ConstraintRepository's raw-SQL +
tenant-scope conventions. Governed by docs/02_06_execution_ledger.md.
"""
from __future__ import annotations

import json
from uuid import UUID

import psycopg

from chips.compiler.models import DecisionLogEntry
from chips.tenant import build_tenant_scope

_SELECT_COLS = (
    "id, brief_id, tenant_id, scope, feature_schema_version, context_features, "
    "action, propensity, policy_version, evidence_used, latency_ms, feedback, "
    "verifier_outcome, downstream_success, composite_reward, created_at"
)


class DecisionLogRepository:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def record(
        self,
        *,
        brief_id: UUID,
        feature_schema_version: str,
        policy_version: str,
        context_features: dict | None = None,
        action: dict | None = None,
        propensity: float | None = 1.0,
        evidence_used: list | None = None,
        latency_ms: int | None = None,
        scope: str | None = None,
        tenant_id: str | None = None,
    ) -> UUID:
        """Append one decision row and return its id.

        Reward columns (feedback/verifier_outcome/downstream_success/
        composite_reward) are intentionally left NULL — Foundation does not
        compute reward (ledger: that is Activation, gated on the verifier).
        """
        row = self._conn.execute(
            """
            INSERT INTO cortex_decision_log
                (brief_id, tenant_id, scope, feature_schema_version,
                 context_features, action, propensity, policy_version,
                 evidence_used, latency_ms)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s::jsonb, %s)
            RETURNING id
            """,
            (
                str(brief_id), tenant_id, scope, feature_schema_version,
                json.dumps(context_features or {}), json.dumps(action or {}),
                propensity, policy_version,
                json.dumps(evidence_used or []), latency_ms,
            ),
        ).fetchone()
        self._conn.commit()
        assert row is not None
        return UUID(str(row[0]))

    def get(
        self, decision_id: UUID, tenant_id: str | None = None
    ) -> DecisionLogEntry | None:
        """Read one decision by id, tenant-scoped (None = unscoped/admin read)."""
        scoped = build_tenant_scope(["id = %s"], [str(decision_id)], tenant_id)
        row = self._conn.execute(  # type: ignore[arg-type]
            f"SELECT {_SELECT_COLS} FROM cortex_decision_log "
            f"WHERE {' AND '.join(scoped.conditions)}",
            tuple(scoped.params),
        ).fetchone()
        return self._row_to_entry(row) if row else None

    def for_brief(
        self, brief_id: UUID, tenant_id: str | None = None
    ) -> list[DecisionLogEntry]:
        """All decisions logged for a brief, oldest first, tenant-scoped."""
        scoped = build_tenant_scope(["brief_id = %s"], [str(brief_id)], tenant_id)
        rows = self._conn.execute(  # type: ignore[arg-type]
            f"SELECT {_SELECT_COLS} FROM cortex_decision_log "
            f"WHERE {' AND '.join(scoped.conditions)} "
            f"ORDER BY created_at ASC, id ASC",
            tuple(scoped.params),
        ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    @staticmethod
    def _row_to_entry(r) -> DecisionLogEntry:
        return DecisionLogEntry(
            id=UUID(str(r[0])),
            brief_id=UUID(str(r[1])),
            tenant_id=str(r[2]) if r[2] else None,
            scope=r[3],
            feature_schema_version=r[4],
            context_features=r[5] or {},
            action=r[6] or {},
            propensity=r[7],
            policy_version=r[8],
            evidence_used=r[9] or [],
            latency_ms=r[10],
            feedback=r[11],
            verifier_outcome=r[12],
            downstream_success=r[13],
            composite_reward=r[14],
            created_at=r[15],
        )
