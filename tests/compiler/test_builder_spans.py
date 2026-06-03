"""End-to-end span contract test for the brief-build path (Foundation gate).

Asserts the exact OpenInference span tree BriefBuilder.build emits: a CHAIN root
with EMBEDDING / RETRIEVER / RERANKER / TOOL children, each stamped with the
standard span-kind key and the pinned chips.* attributes. This is the executable
contract that replaces a review-gate checklist (observability design §decision).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from chips.observability import tracing

pytest.importorskip("opentelemetry.sdk")

if not tracing._OTEL_AVAILABLE:  # full OTel stack absent (e.g. Windows dev)
    pytest.skip(
        "full OpenTelemetry stack not installed; spans no-op",
        allow_module_level=True,
    )

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from chips.compiler.builder import BriefBuilder
from chips.compiler.models import ContextBrief
from chips.observability.openinference import (
    ATTR_BRIEF_ID,
    ATTR_EMBEDDING_DIMENSIONS,
    ATTR_GOVERNOR_TRIGGERED,
    ATTR_LATENCY_MS,
    ATTR_RETRIEVER_DIFF_COUNT,
    ATTR_RETRIEVER_FILE_SIGNAL_COUNT,
    ATTR_SCOPE,
    ATTR_TASK_KIND,
    ATTR_TENANT_ID,
    SPAN_KIND_KEY,
    SpanKind,
)

_REQUIRED_SPANS = {
    "chips.compile.brief",
    "chips.embed.task",
    "chips.retrieve",
    "chips.rerank",
    "chips.compress",
}

_TENANT = "aaaaaaaa-0000-0000-0000-000000000001"


def _make_embedder(vector: list[float] | None = None) -> MagicMock:
    embedder = MagicMock()
    embedder.embed.return_value = vector or [0.1] * 768
    return embedder


def _make_compressor(output: str = "compressed context") -> MagicMock:
    compressor = MagicMock()
    compressor.compress.return_value = output
    compressor.compress_with_trace.return_value = (output, [])
    return compressor


@pytest.fixture
def captured_spans(monkeypatch):
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(tracing, "_get_tracer", lambda: provider.get_tracer("chips"))
    monkeypatch.setattr(tracing, "_telemetry_requested", lambda: True)
    return exporter


def _by_name(spans) -> dict[str, object]:
    return {s.name: s for s in spans}


def test_build_emits_expected_span_tree(conn, captured_spans):
    brief = BriefBuilder(conn, _make_embedder(), _make_compressor()).build(
        "fix the login crash", scope="auth", tenant_id=_TENANT
    )
    assert isinstance(brief, ContextBrief)

    spans = captured_spans.get_finished_spans()
    names = _by_name(spans)

    # Required spans present (parenting asserted separately). Not an exact-set
    # lock: a future legitimate callee span must not break this contract.
    assert _REQUIRED_SPANS <= set(names)

    # Span kinds.
    assert names["chips.compile.brief"].attributes[SPAN_KIND_KEY] == SpanKind.CHAIN
    assert names["chips.embed.task"].attributes[SPAN_KIND_KEY] == SpanKind.EMBEDDING
    assert names["chips.retrieve"].attributes[SPAN_KIND_KEY] == SpanKind.RETRIEVER
    assert names["chips.rerank"].attributes[SPAN_KIND_KEY] == SpanKind.RERANKER
    assert names["chips.compress"].attributes[SPAN_KIND_KEY] == SpanKind.TOOL


def test_chain_is_root_and_others_are_its_children(conn, captured_spans):
    BriefBuilder(conn, _make_embedder(), _make_compressor()).build("fix crash")

    names = _by_name(captured_spans.get_finished_spans())
    root = names["chips.compile.brief"]
    assert root.parent is None

    root_span_id = root.context.span_id
    for child in ("chips.embed.task", "chips.retrieve", "chips.rerank", "chips.compress"):
        assert names[child].parent is not None
        assert names[child].parent.span_id == root_span_id


def test_chain_span_carries_chips_attributes(conn, captured_spans):
    brief = BriefBuilder(conn, _make_embedder(), _make_compressor()).build(
        "fix the broken pipeline", scope="payments", tenant_id=_TENANT
    )

    root = _by_name(captured_spans.get_finished_spans())["chips.compile.brief"]
    attrs = root.attributes
    assert attrs[ATTR_TASK_KIND] == brief.task_kind
    assert attrs[ATTR_SCOPE] == "payments"
    assert attrs[ATTR_TENANT_ID] == _TENANT
    assert attrs[ATTR_BRIEF_ID] == str(brief.brief_id)
    assert attrs[ATTR_LATENCY_MS] >= 0
    assert ATTR_GOVERNOR_TRIGGERED in attrs


def test_embedding_span_records_dimensions(conn, captured_spans):
    BriefBuilder(conn, _make_embedder([0.0] * 384), _make_compressor()).build("fix crash")

    embed = _by_name(captured_spans.get_finished_spans())["chips.embed.task"]
    assert embed.attributes[ATTR_EMBEDDING_DIMENSIONS] == 384


def test_optional_attributes_omitted_when_absent(conn, captured_spans):
    # No scope, no tenant → those keys must be absent (not stamped empty).
    BriefBuilder(conn, _make_embedder(), _make_compressor()).build("fix crash")

    root = _by_name(captured_spans.get_finished_spans())["chips.compile.brief"]
    assert ATTR_SCOPE not in root.attributes
    assert ATTR_TENANT_ID not in root.attributes


def test_span_tree_is_stable_under_governor_short_circuit(conn, captured_spans):
    # When the governor short-circuits, secondary sources are skipped — but the
    # span tree shape must be identical (deterministic contract), with the skip
    # reflected on the root and zeroed retriever counts.
    gov = MagicMock()
    gov.triggered = True
    gov.mean_confidence = 0.95
    gov.item_count = 3
    gov.skipped_sources = ["file_signals", "diffs"]
    gov.reason = "high confidence"

    with patch("chips.compiler.builder.governor_evaluate", return_value=gov):
        BriefBuilder(conn, _make_embedder(), _make_compressor()).build(
            "fix crash", scope="auth", tenant_id=_TENANT
        )

    names = _by_name(captured_spans.get_finished_spans())
    assert _REQUIRED_SPANS <= set(names)
    assert names["chips.compile.brief"].attributes[ATTR_GOVERNOR_TRIGGERED] is True
    retrieve = names["chips.retrieve"]
    assert retrieve.attributes[ATTR_RETRIEVER_DIFF_COUNT] == 0
    assert retrieve.attributes[ATTR_RETRIEVER_FILE_SIGNAL_COUNT] == 0
