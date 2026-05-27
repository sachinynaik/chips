from __future__ import annotations

from chips.compiler.models import SourceStatus


def test_get_source_health_returns_runtime_and_workflow_sources(monkeypatch):
    from chips.mcp.tools import health

    monkeypatch.setattr(
        health,
        "probe_runtime",
        lambda: SourceStatus(status="available"),
    )
    monkeypatch.setattr(
        health,
        "probe_workflow",
        lambda: SourceStatus(status="error", detail="refused"),
    )

    result = health.get_source_health()

    assert "generated_at" in result
    assert result["sources"]["runtime"]["status"] == "available"
    assert result["sources"]["workflow"]["status"] == "error"
    assert "state_counts" in result["sources"]["runtime"]
