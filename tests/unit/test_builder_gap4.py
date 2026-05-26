"""Gap 4: source-availability probes for runtime and workflow."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from chips.compiler.builder import BriefBuilder


def _build_with_mocks(**kwargs):
    builder = BriefBuilder(
        conn=MagicMock(),
        embedder=MagicMock(embed=MagicMock(return_value=[0.1] * 768)),
        compressor=MagicMock(compress=MagicMock(return_value="compressed")),
    )
    with (
        patch("chips.compiler.builder.retrieve_memories", return_value=[]),
        patch("chips.compiler.builder.retrieve_diffs", return_value=[]),
        patch("chips.compiler.builder.retrieve_file_signals", return_value=[]),
        patch.object(BriefBuilder, "_persist"),
    ):
        return builder.build("fix crash", **kwargs)


# ── probe_runtime ─────────────────────────────────────────────────────────────

class TestProbeRuntime:
    def test_not_configured_when_no_env_var(self, monkeypatch):
        monkeypatch.delenv("SIGNOZ_API_URL", raising=False)
        from chips.mcp.tools.runtime import probe_runtime
        status = probe_runtime()
        assert status.status == "not_configured"

    def test_available_when_env_set_and_request_ok(self, monkeypatch):
        monkeypatch.setenv("SIGNOZ_API_URL", "http://signoz:3301")
        from chips.mcp.tools.runtime import probe_runtime
        with patch("chips.mcp.tools.runtime.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.raise_for_status = MagicMock()
            status = probe_runtime()
        assert status.status == "available"

    def test_error_when_env_set_but_connection_fails(self, monkeypatch):
        monkeypatch.setenv("SIGNOZ_API_URL", "http://signoz:3301")
        from chips.mcp.tools.runtime import probe_runtime
        with patch("chips.mcp.tools.runtime.requests.get", side_effect=ConnectionError("refused")):
            status = probe_runtime()
        assert status.status == "error"
        assert "ConnectionError" in status.detail or "refused" in status.detail

    def test_error_when_service_returns_http_error(self, monkeypatch):
        monkeypatch.setenv("SIGNOZ_API_URL", "http://signoz:3301")
        from chips.mcp.tools.runtime import probe_runtime
        import requests as req
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req.HTTPError("500 Server Error")
        with patch("chips.mcp.tools.runtime.requests.get", return_value=mock_resp):
            status = probe_runtime()
        assert status.status == "error"


# ── probe_workflow ────────────────────────────────────────────────────────────

class TestProbeWorkflow:
    def test_not_configured_when_no_env_var(self, monkeypatch):
        monkeypatch.delenv("DBOS_DB_URL", raising=False)
        from chips.mcp.tools.workflow import probe_workflow
        status = probe_workflow()
        assert status.status == "not_configured"

    def test_available_when_env_set_and_db_ok(self, monkeypatch):
        monkeypatch.setenv("DBOS_DB_URL", "postgresql://user:pw@host/db")
        from chips.mcp.tools.workflow import probe_workflow
        with patch("chips.mcp.tools.workflow.psycopg.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_connect.return_value = mock_conn
            status = probe_workflow()
        assert status.status == "available"

    def test_error_when_env_set_but_connection_fails(self, monkeypatch):
        monkeypatch.setenv("DBOS_DB_URL", "postgresql://user:pw@host/db")
        from chips.mcp.tools.workflow import probe_workflow
        with patch("chips.mcp.tools.workflow.psycopg.connect", side_effect=Exception("refused")):
            status = probe_workflow()
        assert status.status == "error"
        assert status.detail != ""

    def test_probe_passes_connect_timeout(self, monkeypatch):
        monkeypatch.setenv("DBOS_DB_URL", "postgresql://user:pw@host/db")
        from chips.mcp.tools.workflow import probe_workflow
        with patch("chips.mcp.tools.workflow.psycopg.connect") as mock_connect:
            mock_connect.return_value = MagicMock()
            probe_workflow()
        _, kwargs = mock_connect.call_args
        assert "connect_timeout" in kwargs
        assert kwargs["connect_timeout"] > 0


# ── BriefBuilder integration ──────────────────────────────────────────────────

class TestBriefBuilderGap4:
    def test_data_sources_includes_runtime_key(self, monkeypatch):
        monkeypatch.delenv("SIGNOZ_API_URL", raising=False)
        brief = _build_with_mocks()
        assert "runtime" in brief.data_sources

    def test_data_sources_includes_workflow_key(self, monkeypatch):
        monkeypatch.delenv("DBOS_DB_URL", raising=False)
        brief = _build_with_mocks()
        assert "workflow" in brief.data_sources

    def test_runtime_not_configured_when_no_env_var(self, monkeypatch):
        monkeypatch.delenv("SIGNOZ_API_URL", raising=False)
        brief = _build_with_mocks()
        assert brief.data_sources["runtime"].status == "not_configured"

    def test_workflow_not_configured_when_no_env_var(self, monkeypatch):
        monkeypatch.delenv("DBOS_DB_URL", raising=False)
        brief = _build_with_mocks()
        assert brief.data_sources["workflow"].status == "not_configured"

    def test_build_logs_warning_when_runtime_errors(self, monkeypatch):
        monkeypatch.setenv("SIGNOZ_API_URL", "http://signoz:3301")
        with patch("chips.mcp.tools.runtime.requests.get", side_effect=ConnectionError("refused")):
            with patch("chips.compiler.builder.logger") as mock_logger:
                _build_with_mocks()
        mock_logger.warning.assert_called()

    def test_build_logs_warning_when_workflow_errors(self, monkeypatch):
        monkeypatch.setenv("DBOS_DB_URL", "postgresql://user:pw@host/db")
        with patch("chips.mcp.tools.workflow.psycopg.connect", side_effect=Exception("refused")):
            with patch("chips.compiler.builder.logger") as mock_logger:
                _build_with_mocks()
        mock_logger.warning.assert_called()
