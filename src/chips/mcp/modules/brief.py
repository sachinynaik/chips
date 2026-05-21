from __future__ import annotations

from typing import Callable

import psycopg
from mcp.server.fastmcp import FastMCP

from chips.compiler.builder import BriefBuilder
from chips.compiler.compressor import OllamaCompressor
from chips.compiler.policy import PolicyLoader
from chips.harvester.embedding import OllamaEmbedder


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

    def get_context_brief(self, task: str, scope: str | None = None) -> dict:
        conn = self._conn_factory()
        try:
            builder = BriefBuilder(
                conn,
                self._embedder,
                self._compressor,
                policy_loader=self._policy_loader,
            )
            brief = builder.build(task, scope=scope)
        finally:
            conn.close()

        return {
            "brief_id": str(brief.brief_id),
            "task": brief.task,
            "task_kind": brief.task_kind,
            "scope": brief.scope,
            "generated_at": brief.generated_at.isoformat(),
            "latency_ms": brief.latency_ms,
            "hard_constraints": brief.hard_constraints,
            "compressed_context": brief.compressed_context,
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
        }

    def register(self, app: FastMCP) -> None:
        app.tool()(self.get_context_brief)
