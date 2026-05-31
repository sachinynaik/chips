from __future__ import annotations

import json
import time
from collections import defaultdict

import psycopg

from chips.observability.metrics import observe_learning_recompute


class BriefLearningService:
    _last_recompute_by_tenant: dict[str, float] = {}

    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    @staticmethod
    def _tenant_key(tenant_id: str | None) -> str:
        return tenant_id or ""

    def maybe_recompute(
        self, tenant_id: str | None = None, min_interval_seconds: int = 300
    ) -> int:
        tenant_key = self._tenant_key(tenant_id)
        now = time.monotonic()
        last = self._last_recompute_by_tenant.get(tenant_key)
        if last is not None and now - last < min_interval_seconds:
            return 0
        updated = self.recompute(tenant_id=tenant_id)
        self._last_recompute_by_tenant[tenant_key] = now
        return updated

    def recompute(self, tenant_id: str | None = None) -> int:
        start = time.monotonic()
        rows = self._fetch_learning_rows(tenant_id=tenant_id)
        aggregates: dict[str, dict[str, float | int]] = defaultdict(
            lambda: {
                "adjustment": 0.0,
                "accepted_count": 0,
                "rejected_count": 0,
                "ignored_count": 0,
            }
        )
        outcome_weights = {"accepted": 0.05, "rejected": -0.10, "ignored": 0.0}

        for outcome, retrieved_memories_json, ranked_signals_json in rows:
            try:
                retrieved_memories = json.loads(retrieved_memories_json or "[]")
            except (TypeError, json.JSONDecodeError):
                retrieved_memories = []
            try:
                ranked_signals = json.loads(ranked_signals_json or "[]")
            except (TypeError, json.JSONDecodeError):
                ranked_signals = []

            memory_scores = {
                str(item.get("item_id")): float(item.get("score") or 0.0)
                for item in ranked_signals
                if item.get("item_type") == "memory"
            }
            outcome_weight = outcome_weights.get(str(outcome), 0.0)
            for memory in retrieved_memories:
                memory_id = str(memory.get("id", ""))
                if not memory_id:
                    continue
                score = max(memory_scores.get(memory_id, 0.0), 0.1)
                aggregate = aggregates[memory_id]
                aggregate["adjustment"] = float(aggregate["adjustment"]) + (
                    outcome_weight * score
                )
                aggregate[f"{outcome}_count"] = int(aggregate[f"{outcome}_count"]) + 1

        tenant_key = self._tenant_key(tenant_id)
        self._conn.execute(
            "DELETE FROM cortex_memory_feedback_scores WHERE tenant_id = %s",
            (tenant_key,),
        )
        for memory_id, aggregate in aggregates.items():
            adjustment = max(min(float(aggregate["adjustment"]), 0.5), -0.5)
            self._conn.execute(
                """
                INSERT INTO cortex_memory_feedback_scores (
                    memory_id, tenant_id, confidence_adjustment,
                    accepted_count, rejected_count, ignored_count
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    memory_id,
                    tenant_key,
                    adjustment,
                    int(aggregate["accepted_count"]),
                    int(aggregate["rejected_count"]),
                    int(aggregate["ignored_count"]),
                ),
            )
        self._conn.commit()
        observe_learning_recompute(
            status="success", duration_s=time.monotonic() - start
        )
        return len(aggregates)

    def load_adjustments(self, tenant_id: str | None = None) -> dict[str, float]:
        tenant_key = self._tenant_key(tenant_id)
        rows = self._conn.execute(
            """
            SELECT memory_id, confidence_adjustment
            FROM cortex_memory_feedback_scores
            WHERE tenant_id = %s
            """,
            (tenant_key,),
        ).fetchall()
        return {str(memory_id): float(adjustment) for memory_id, adjustment in rows}

    def _fetch_learning_rows(self, tenant_id: str | None = None) -> list[tuple]:
        from chips.tenant import build_tenant_scope

        scoped = build_tenant_scope(["1 = 1"], [], tenant_id, column="b.tenant_id")
        return self._conn.execute(
            f"""
            SELECT o.outcome, b.retrieved_memories, b.ranked_signals
            FROM cortex_briefs b
            JOIN cortex_brief_outcomes o ON o.brief_id = b.brief_id
            WHERE {' AND '.join(scoped.conditions)}
            """,
            tuple(scoped.params),
        ).fetchall()
