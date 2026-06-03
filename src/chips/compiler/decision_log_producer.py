"""Foundation: turn a finished brief into one ``cortex_decision_log`` row.

Wiring the bandit-design "log-count = brief-count" gate (step 3): every brief
``BriefBuilder.build`` produces emits exactly one decision row. The assembly is a
pure function (``build_decision_fields``) so the context/action mapping is
unit-testable without a database; ``record_brief_decision`` is the thin DB seam
the builder calls at its single chokepoint.

Foundation logs the deterministic policy decision only (propensity=1.0, reward
columns NULL); reward consumption is Activation, gated on the Phase-3 verifier.
"""

from __future__ import annotations

from uuid import UUID

import psycopg

from chips.compiler.decision_log_repository import DecisionLogRepository
from chips.compiler.models import ContextBrief
from chips.compiler.policy_version import FEATURE_SCHEMA_VERSION, active_policy_version


def build_decision_fields(brief: ContextBrief, *, files: list[str] | None) -> dict:
    """Project a finished brief into ``DecisionLogRepository.record`` kwargs.

    ``files`` is the only input not already on the brief (it drives ``has_files``).
    Everything else is read from the brief's already-computed fields, so this adds
    no recomputation and no coupling to the build's inner retrieval logic.
    """
    gov = brief.governor_decision or {}
    file_status = brief.data_sources.get("file_signals")
    context_features = {
        "task_kind": brief.task_kind,
        "scope": brief.scope,
        "has_files": bool(files),
        "memory_count": len(brief.retrieved.memories),
        "governor_mean_confidence": gov.get("mean_confidence"),
        "governor_item_count": gov.get("item_count"),
    }
    action = {
        "governor_triggered": gov.get("triggered"),
        "skipped_sources": gov.get("skipped_sources", []),
        "ranked_count": len(brief.ranked_signals),
        "file_signals_status": file_status.status if file_status else None,
    }
    return {
        "brief_id": brief.brief_id,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "policy_version": active_policy_version(),
        "context_features": context_features,
        "action": action,
        "propensity": 1.0,
        "evidence_used": [s.item_id for s in brief.ranked_signals],
        "latency_ms": brief.latency_ms,
        "scope": brief.scope,
        "tenant_id": brief.tenant_id,
    }


def record_brief_decision(
    conn: psycopg.Connection, brief: ContextBrief, *, files: list[str] | None = None
) -> UUID:
    """Append the one decision row for ``brief`` and return its id."""
    return DecisionLogRepository(conn).record(
        **build_decision_fields(brief, files=files)
    )
