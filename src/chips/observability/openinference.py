"""OpenInference span-kind + ``chips.*`` attribute registry (snapshot).

This module is the single, pinned source of truth for the span schema CHIPS
emits. Per the observability design (``02_06_observability_analysis_architecture``
and ``research/openinference-assessment``): adopt the OpenInference *semantic
conventions* as a thin attribute-naming standard for CHIPS's
retriever/reranker/embedding/tool/chain spans, emit them **manually** (no
auto-instrumentors), and carry CHIPS-domain concepts under a namespaced
``chips.*`` custom-attribute space because OpenInference has no vocabulary for
them. Treating the convention as a *snapshot* (not a hard dependency) means an
upstream spec change cannot silently churn CHIPS span attributes — this file is
the contract, asserted by the span contract test.
"""

from __future__ import annotations

# ── OpenInference standard ────────────────────────────────────────────────────

#: Standard OpenInference key carrying the span kind.
SPAN_KIND_KEY = "openinference.span.kind"


class SpanKind:
    """OpenInference span kinds CHIPS uses.

    LLM/AGENT kinds are intentionally omitted: CHIPS bars LLM generation in the
    hot path, so only the retrieval/ranking/tool/orchestration kinds apply.
    """

    CHAIN = "CHAIN"
    RETRIEVER = "RETRIEVER"
    RERANKER = "RERANKER"
    EMBEDDING = "EMBEDDING"
    TOOL = "TOOL"


# ── chips.* custom attributes (domain concepts OpenInference cannot model) ─────

# Root CHAIN span (the brief build).
ATTR_TASK_KIND = "chips.task_kind"
ATTR_SCOPE = "chips.scope"
ATTR_TENANT_ID = "chips.tenant_id"
ATTR_BRIEF_ID = "chips.brief_id"
ATTR_LATENCY_MS = "chips.latency_ms"
ATTR_GOVERNOR_TRIGGERED = "chips.governor.triggered"

# EMBEDDING span.
ATTR_EMBEDDING_DIMENSIONS = "chips.embedding.dimensions"

# RETRIEVER span.
ATTR_RETRIEVER_MEMORY_COUNT = "chips.retriever.memory_count"
ATTR_RETRIEVER_DIFF_COUNT = "chips.retriever.diff_count"
ATTR_RETRIEVER_FILE_SIGNAL_COUNT = "chips.retriever.file_signal_count"
ATTR_RETRIEVER_STRUCTURAL_COUNT = "chips.retriever.structural_count"

# RERANKER span.
ATTR_RERANKER_INPUT_COUNT = "chips.reranker.input_count"
ATTR_RERANKER_OUTPUT_COUNT = "chips.reranker.output_count"


#: Frozen snapshot of every ``chips.*`` attribute key CHIPS emits. The span
#: contract test pins this so a renamed/added key is a deliberate, reviewed
#: change rather than silent drift.
CHIPS_ATTRIBUTE_KEYS: tuple[str, ...] = (
    ATTR_TASK_KIND,
    ATTR_SCOPE,
    ATTR_TENANT_ID,
    ATTR_BRIEF_ID,
    ATTR_LATENCY_MS,
    ATTR_GOVERNOR_TRIGGERED,
    ATTR_EMBEDDING_DIMENSIONS,
    ATTR_RETRIEVER_MEMORY_COUNT,
    ATTR_RETRIEVER_DIFF_COUNT,
    ATTR_RETRIEVER_FILE_SIGNAL_COUNT,
    ATTR_RETRIEVER_STRUCTURAL_COUNT,
    ATTR_RERANKER_INPUT_COUNT,
    ATTR_RERANKER_OUTPUT_COUNT,
)
