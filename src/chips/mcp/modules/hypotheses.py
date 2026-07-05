from __future__ import annotations

from typing import Callable

import psycopg
from mcp.server.fastmcp import FastMCP

from chips.mcp.tools.hypotheses import get_constraint_candidates as _get_constraint_candidates
from chips.mcp.tools.hypotheses import review_constraint_candidate as _review_constraint_candidate
from chips.mcp.tools.hypotheses import submit_hypotheses as _submit_hypotheses


class HypothesesModule:
    name = "hypotheses"

    def __init__(self, conn_factory: Callable[[], psycopg.Connection]) -> None:
        self._conn_factory = conn_factory

    def submit_hypotheses(
        self,
        *,
        evidence_bundle: dict,
        hypotheses: list[dict],
        rejected_hypothesis_ids: list[str] | None = None,
        scope: str | None = None,
        tenant_id: str | None = None,
    ) -> dict:
        from chips.tenant import require_tenant

        require_tenant(tenant_id)
        conn = self._conn_factory()
        try:
            return _submit_hypotheses(
                evidence_bundle=evidence_bundle,
                hypotheses=hypotheses,
                rejected_hypothesis_ids=rejected_hypothesis_ids,
                scope=scope,
                tenant_id=tenant_id,
                conn=conn,
            )
        finally:
            conn.close()

    def get_constraint_candidates(
        self,
        *,
        scope: str | None = None,
        status: str = "pending",
        tenant_id: str | None = None,
    ) -> dict:
        from chips.tenant import require_tenant

        require_tenant(tenant_id)
        conn = self._conn_factory()
        try:
            return _get_constraint_candidates(conn, scope=scope, status=status, tenant_id=tenant_id)
        finally:
            conn.close()

    def review_constraint_candidate(
        self,
        *,
        candidate_id: str,
        resolution: str,
        promoted_constraint_id: str | None = None,
        tenant_id: str | None = None,
    ) -> dict:
        from chips.tenant import require_tenant

        require_tenant(tenant_id)
        conn = self._conn_factory()
        try:
            return _review_constraint_candidate(
                conn,
                candidate_id=candidate_id,
                resolution=resolution,
                promoted_constraint_id=promoted_constraint_id,
                tenant_id=tenant_id,
            )
        finally:
            conn.close()

    def register(self, app: FastMCP) -> None:
        app.tool()(self.submit_hypotheses)
        app.tool()(self.get_constraint_candidates)
        app.tool()(self.review_constraint_candidate)
