from __future__ import annotations

from chips.observability.metrics import (
    observe_brief_build,
    observe_feedback_submission,
    observe_governor_decision,
    observe_learning_recompute,
    observe_rerank,
    observe_structural_retrieval,
    render_latest_metrics,
)
from chips.observability.tracing import configure_telemetry, start_span


def test_metrics_render_contains_registered_chips_metrics():
    observe_brief_build(status="success", latency_ms=125)
    observe_feedback_submission(outcome="accepted", deduplicated=False, latency_ms=12)
    observe_learning_recompute(status="success", duration_s=0.05)
    observe_governor_decision(triggered=True)
    observe_rerank(status="success")
    observe_structural_retrieval(status="success")

    rendered = render_latest_metrics()

    assert "chips_brief_build_total" in rendered
    assert "chips_feedback_submission_total" in rendered
    assert "chips_learning_recompute_total" in rendered
    assert "chips_governor_decision_total" in rendered
    assert "chips_rerank_total" in rendered
    assert "chips_structural_retrieval_total" in rendered


def test_configure_telemetry_is_disabled_without_env(monkeypatch):
    monkeypatch.delenv("CHIPS_ENABLE_OTEL", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", raising=False)

    assert configure_telemetry("chips-test") is False


def test_start_span_is_safe_without_configured_provider():
    with start_span("chips.test.span", answer=42):
        value = "ok"

    assert value == "ok"
