from __future__ import annotations

from typing import Callable

import psycopg
from mcp.server.fastmcp import FastMCP

from chips.compiler.builder import BriefBuilder
from chips.compiler.compressor import OllamaCompressor
from chips.compiler.models import EvidenceBundle, EvidenceItem
from chips.compiler.policy import PolicyLoader
from chips.harvester.embedding import OllamaEmbedder


def _evidence_item_to_wire(e: EvidenceItem) -> dict:
    return {
        "evidence_id": e.evidence_id,
        "kind": e.kind,
        "label": e.label,
        "text": e.text,
        "weight": e.weight,
        "constraint_kind": e.constraint_kind,
        "target": e.target,
        "refs": e.refs,
    }


def evidence_bundle_to_wire(bundle: EvidenceBundle | None) -> dict | None:
    """Serialize an EvidenceBundle for the MCP wire (UUID → str; lists of items).

    Shared by ``BriefModule.get_context_brief`` and ``server.get_context_brief`` so the
    two brief serializers cannot drift on the bundle shape (contract §I.5).
    """
    if bundle is None:
        return None
    return {
        "bundle_id": str(bundle.bundle_id),
        "constraints": [_evidence_item_to_wire(c) for c in bundle.constraints],
        "evidence": [_evidence_item_to_wire(e) for e in bundle.evidence],
    }


class BriefModule:
    name = "brief"

    def __init__(
        self,
        conn_factory: Callable[[], psycopg.Connection],
        embedder: OllamaEmbedder,
        compressor: OllamaCompressor,
        policy_loader: PolicyLoader,
    ) -> None:
        self._conn_factory = conn_factory
        self._embedder = embedder
        self._compressor = compressor
        self._policy_loader = policy_loader

    def get_context_brief(
        self,
        task: str,
        scope: str | None = None,
        files: list[str] | None = None,
        tenant_id: str | None = None,
    ) -> dict:
        from chips.tenant import require_tenant
        require_tenant(tenant_id)

        conn = self._conn_factory()
        try:
            builder = BriefBuilder(
                conn,
                self._embedder,
                self._compressor,
                policy_loader=self._policy_loader,
            )
            brief = builder.build(task, scope=scope, files=files, tenant_id=tenant_id)
        finally:
            conn.close()

        return {
            "brief_id": str(brief.brief_id),
            "task": brief.task,
            "task_kind": brief.task_kind,
            "scope": brief.scope,
            "tenant_id": brief.tenant_id,
            "generated_at": brief.generated_at.isoformat(),
            "latency_ms": brief.latency_ms,
            "hard_constraints": brief.hard_constraints,
            "compressed_context": brief.compressed_context,
            "schema_version": brief.schema_version,
            "data_sources": {
                k: {
                    "status": v.status,
                    "detail": v.detail,
                    "checked_at": v.checked_at.isoformat() if v.checked_at else None,
                }
                for k, v in brief.data_sources.items()
            },
            "ranked_signals": [
                {
                    "item_id": s.item_id,
                    "item_type": s.item_type,
                    "score": s.score,
                    "signal_breakdown": s.signal_breakdown,
                }
                for s in brief.ranked_signals
            ],
            "retrieved_memories": brief.retrieved.memories,
            "forbidden_edits": brief.forbidden_edits,
            "allowed_edits": brief.allowed_edits,
            "evidence_bundle": evidence_bundle_to_wire(brief.evidence_bundle),
        }

    def register(self, app: FastMCP) -> None:
        app.tool()(self.get_context_brief)
