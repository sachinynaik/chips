from __future__ import annotations

import pytest

from chips.observability import tracing

pytest.importorskip("opentelemetry.sdk")

if not tracing._OTEL_AVAILABLE:  # full OTel stack (exporter + instrumentation) absent
    pytest.skip(
        "full OpenTelemetry stack not installed; spans no-op",
        allow_module_level=True,
    )

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)


@pytest.fixture
def captured_spans(monkeypatch):
    """In-memory span capture, isolated from the process-global provider.

    Injects a fresh ``TracerProvider`` via the ``_get_tracer`` seam so each
    test sees only its own spans (no set-once-guard contention), and enables the
    telemetry gate (``start_span`` now also gates on ``_telemetry_requested``).
    """
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(tracing, "_get_tracer", lambda: provider.get_tracer("chips"))
    monkeypatch.setattr(tracing, "_telemetry_requested", lambda: True)
    return exporter


def test_start_span_is_disabled_when_telemetry_not_requested(monkeypatch):
    # Provider injected, but telemetry off → start_span must not create a span.
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(tracing, "_get_tracer", lambda: provider.get_tracer("chips"))
    monkeypatch.setattr(tracing, "_telemetry_requested", lambda: False)

    from chips.observability.openinference import SpanKind

    with tracing.start_span("chips.retrieve", kind=SpanKind.RETRIEVER) as span:
        assert span is None

    assert exporter.get_finished_spans() == ()


def test_span_records_exception_and_sets_error_status(captured_spans):
    from opentelemetry.trace import StatusCode

    from chips.observability.openinference import SpanKind

    with pytest.raises(ValueError):
        with tracing.start_span("chips.boom", kind=SpanKind.TOOL):
            raise ValueError("boom")

    span = captured_spans.get_finished_spans()[0]
    assert span.status.status_code == StatusCode.ERROR
    assert any(event.name == "exception" for event in span.events)


def test_start_span_stamps_openinference_kind(captured_spans):
    from chips.observability.openinference import SPAN_KIND_KEY, SpanKind

    with tracing.start_span("chips.retrieve", **{SPAN_KIND_KEY: SpanKind.RETRIEVER}):
        pass

    spans = captured_spans.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "chips.retrieve"
    assert spans[0].attributes.get(SPAN_KIND_KEY) == SpanKind.RETRIEVER


def test_start_span_sets_chips_attributes(captured_spans):
    from chips.observability.openinference import ATTR_TASK_KIND, SPAN_KIND_KEY, SpanKind

    with tracing.start_span(
        "chips.compile.brief",
        **{SPAN_KIND_KEY: SpanKind.CHAIN, ATTR_TASK_KIND: "bugfix"},
    ):
        pass

    span = captured_spans.get_finished_spans()[0]
    assert span.attributes.get(SPAN_KIND_KEY) == SpanKind.CHAIN
    assert span.attributes.get(ATTR_TASK_KIND) == "bugfix"


def test_start_span_omits_none_valued_attributes(captured_spans):
    from chips.observability.openinference import ATTR_SCOPE, ATTR_TENANT_ID

    with tracing.start_span(
        "chips.compile.brief",
        **{ATTR_SCOPE: "auth", ATTR_TENANT_ID: None},
    ):
        pass

    span = captured_spans.get_finished_spans()[0]
    assert span.attributes.get(ATTR_SCOPE) == "auth"
    assert ATTR_TENANT_ID not in span.attributes
