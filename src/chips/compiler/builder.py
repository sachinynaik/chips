from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone

import psycopg

from chips.compiler.classifier import classify_task
from chips.compiler.compressor import OllamaCompressor
from chips.compiler.models import ContextBrief, RankedSignal, RetrievedItems
from chips.compiler.ranker import rank_signals
from chips.compiler.retrieval import retrieve_file_signals, retrieve_memories
from chips.harvester.embedding import OllamaEmbedder


class BriefBuilder:
    def __init__(
        self,
        conn: psycopg.Connection,
        embedder: OllamaEmbedder,
        compressor: OllamaCompressor,
    ) -> None:
        self._conn = conn
        self._embedder = embedder
        self._compressor = compressor

    def build(self, task: str, scope: str | None = None) -> ContextBrief:
        start = time.monotonic()

        task_kind = classify_task(task)
        embedding = self._embedder.embed(task)

        memories = retrieve_memories(self._conn, embedding, scope=scope)
        file_signals = retrieve_file_signals(self._conn, [])

        ranked = rank_signals(memories, file_signals)

        hard_constraints = [
            m["content"] for m in memories
            if m.get("type") in ("invariant", "contract")
        ]
        soft_items = [
            m["content"] for m in memories
            if m.get("type") not in ("invariant", "contract")
        ]

        compressed = self._compressor.compress(hard_constraints, soft_items, task)

        latency_ms = int((time.monotonic() - start) * 1000)
        brief_id = uuid.uuid4()
        generated_at = datetime.now(timezone.utc)

        brief = ContextBrief(
            brief_id=brief_id,
            task=task,
            scope=scope,
            generated_at=generated_at,
            latency_ms=latency_ms,
            task_kind=str(task_kind),
            retrieved=RetrievedItems(memories=memories),
            ranked_signals=ranked,
            hard_constraints=hard_constraints,
            compressed_context=compressed,
        )

        self._persist(brief)
        return brief

    def _persist(self, brief: ContextBrief) -> None:
        self._conn.execute(
            """
            INSERT INTO cortex_briefs (
                brief_id, task, scope, generated_at, latency_ms,
                retrieved_memories, compressed_context, hard_constraints
            ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb)
            """,
            (
                str(brief.brief_id),
                brief.task,
                brief.scope,
                brief.generated_at,
                brief.latency_ms,
                json.dumps(brief.retrieved.memories),
                brief.compressed_context,
                json.dumps(brief.hard_constraints),
            ),
        )
        self._conn.commit()
