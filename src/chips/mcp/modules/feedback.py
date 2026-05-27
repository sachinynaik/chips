from __future__ import annotations

from typing import Callable

import psycopg
from mcp.server.fastmcp import FastMCP

from chips.compiler.learning import BriefLearningService
from chips.memory.outcome_repository import BriefOutcomeRepository, OutcomeValue


class FeedbackModule:
    name = "feedback"

    def __init__(self, conn_factory: Callable[[], psycopg.Connection]) -> None:
        self._conn_factory = conn_factory

    def submit_brief_feedback(
        self,
        brief_id: str,
        outcome: OutcomeValue,
        note: str | None = None,
        tenant_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict:
        from chips.tenant import require_tenant
        from uuid import UUID

        require_tenant(tenant_id)
        conn = self._conn_factory()
        try:
            repo = BriefOutcomeRepository(conn)
            result = repo.record_with_ack(
                UUID(brief_id),
                outcome=outcome,
                note=note,
                tenant_id=tenant_id,
                idempotency_key=idempotency_key,
            )
            BriefLearningService(conn).maybe_recompute(tenant_id=tenant_id)
        finally:
            conn.close()

        return {
            "outcome_id": str(result.outcome_id),
            "brief_id": str(result.brief_id),
            "tenant_id": result.tenant_id,
            "outcome": result.outcome,
            "note": result.note,
            "recorded_at": result.created_at.isoformat() if result.created_at else None,
            "deduplicated": result.deduplicated,
        }

    def register(self, app: FastMCP) -> None:
        app.tool()(self.submit_brief_feedback)
