"""Contract tests for the four-state health source vocabulary."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from chips.compiler.models import SourceStatus


# ---------------------------------------------------------------------------
# SourceStatus model
# ---------------------------------------------------------------------------

class TestSourceStatus:
    def test_four_valid_statuses_accepted(self):
        for status in ("not_configured", "available", "unavailable", "error"):
            s = SourceStatus(status=status)
            assert s.status == status

    def test_checked_at_defaults_to_none(self):
        s = SourceStatus(status="available")
        assert s.checked_at is None

    def test_checked_at_preserved(self):
        ts = datetime.now(timezone.utc)
        s = SourceStatus(status="available", checked_at=ts)
        assert s.checked_at == ts

    def test_detail_defaults_to_empty_string(self):
        s = SourceStatus(status="error")
        assert s.detail == ""


# ---------------------------------------------------------------------------
# probe_runtime stamps checked_at on active statuses
# ---------------------------------------------------------------------------

class TestProbeRuntime:
    def test_not_configured_has_no_checked_at(self, monkeypatch):
        monkeypatch.delenv("SIGNOZ_API_URL", raising=False)
        from chips.mcp.tools.runtime import probe_runtime
        status = probe_runtime()
        assert status.status == "not_configured"
        assert status.checked_at is None

    def test_available_has_checked_at(self, monkeypatch):
        monkeypatch.setenv("SIGNOZ_API_URL", "http://signoz:3301")
        with patch("chips.mcp.tools.runtime.requests.get") as mock_get:
            mock_get.return_value.raise_for_status = MagicMock()
            from chips.mcp.tools.runtime import probe_runtime
            status = probe_runtime()
        assert status.status == "available"
        assert isinstance(status.checked_at, datetime)

    def test_error_has_checked_at(self, monkeypatch):
        monkeypatch.setenv("SIGNOZ_API_URL", "http://signoz:3301")
        with patch("chips.mcp.tools.runtime.requests.get", side_effect=ConnectionError("x")):
            from chips.mcp.tools.runtime import probe_runtime
            status = probe_runtime()
        assert status.status == "error"
        assert isinstance(status.checked_at, datetime)


# ---------------------------------------------------------------------------
# probe_workflow stamps checked_at on active statuses
# ---------------------------------------------------------------------------

class TestProbeWorkflow:
    def test_not_configured_has_no_checked_at(self, monkeypatch):
        monkeypatch.delenv("DBOS_DB_URL", raising=False)
        from chips.mcp.tools.workflow import probe_workflow
        status = probe_workflow()
        assert status.status == "not_configured"
        assert status.checked_at is None

    def test_available_has_checked_at(self, monkeypatch):
        monkeypatch.setenv("DBOS_DB_URL", "postgresql://u:p@h/db")
        with patch("chips.mcp.tools.workflow.psycopg.connect") as mock_conn:
            mock_conn.return_value = MagicMock()
            from chips.mcp.tools.workflow import probe_workflow
            status = probe_workflow()
        assert status.status == "available"
        assert isinstance(status.checked_at, datetime)

    def test_error_has_checked_at(self, monkeypatch):
        monkeypatch.setenv("DBOS_DB_URL", "postgresql://u:p@h/db")
        with patch("chips.mcp.tools.workflow.psycopg.connect", side_effect=Exception("refused")):
            from chips.mcp.tools.workflow import probe_workflow
            status = probe_workflow()
        assert status.status == "error"
        assert isinstance(status.checked_at, datetime)


# ---------------------------------------------------------------------------
# Wire serialization via BriefModule
# ---------------------------------------------------------------------------

class TestDataSourcesWireContract:
    def _call_module(self, data_sources):
        import uuid
        from datetime import datetime, timezone
        from chips.mcp.modules.brief import BriefModule

        fake_brief = MagicMock()
        fake_brief.brief_id = uuid.uuid4()
        fake_brief.generated_at = datetime.now(timezone.utc)
        fake_brief.ranked_signals = []
        fake_brief.retrieved.memories = []
        fake_brief.data_sources = data_sources

        module = BriefModule(
            conn_factory=MagicMock(),
            embedder=MagicMock(),
            compressor=MagicMock(),
            policy_loader=MagicMock(),
        )
        with patch("chips.mcp.modules.brief.BriefBuilder") as mock_cls:
            mock_cls.return_value.build_and_log.return_value = fake_brief
            return module.get_context_brief(task="t")

    def test_data_sources_wire_has_checked_at_field(self):
        ts = datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc)
        result = self._call_module({
            "runtime": SourceStatus(status="available", checked_at=ts),
        })
        ds = result["data_sources"]["runtime"]
        assert "checked_at" in ds
        assert ds["checked_at"] == ts.isoformat()

    def test_checked_at_is_none_for_not_configured(self):
        result = self._call_module({
            "runtime": SourceStatus(status="not_configured"),
        })
        ds = result["data_sources"]["runtime"]
        assert ds["checked_at"] is None

    def test_all_four_statuses_serialize_consistently(self):
        ts = datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc)
        sources = {
            "a": SourceStatus(status="not_configured"),
            "b": SourceStatus(status="available", checked_at=ts),
            "c": SourceStatus(status="unavailable", checked_at=ts),
            "d": SourceStatus(status="error", detail="conn refused", checked_at=ts),
        }
        result = self._call_module(sources)
        ds = result["data_sources"]
        assert ds["a"] == {"status": "not_configured", "detail": "", "checked_at": None}
        assert ds["b"] == {"status": "available", "detail": "", "checked_at": ts.isoformat()}
        assert ds["c"] == {"status": "unavailable", "detail": "", "checked_at": ts.isoformat()}
        assert ds["d"] == {"status": "error", "detail": "conn refused", "checked_at": ts.isoformat()}

    def test_probe_failure_does_not_corrupt_brief_output_shape(self):
        """Missing/broken probe must not remove data_sources key from brief."""
        result = self._call_module({
            "runtime": SourceStatus(status="error", detail="timeout"),
            "workflow": SourceStatus(status="not_configured"),
        })
        assert "data_sources" in result
        assert "runtime" in result["data_sources"]
        assert "workflow" in result["data_sources"]
