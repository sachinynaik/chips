"""Docker-free unit tests for get_workflow_state tool function."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from chips.mcp.tools.workflow import get_workflow_state


_DT = datetime(2026, 5, 1, tzinfo=timezone.utc)
_WF_ROW = ("wf-uuid-001", "ERROR", "checkout.process_payment", _DT)


# ---------------------------------------------------------------------------
# Unavailable (no DBOS_DB_URL)
# ---------------------------------------------------------------------------

def test_returns_unavailable_when_env_not_set(monkeypatch):
    monkeypatch.delenv("DBOS_DB_URL", raising=False)
    result = get_workflow_state()
    assert result["status"] == "unavailable"
    assert result["workflows"] == []


def test_unavailable_preserves_scope(monkeypatch):
    monkeypatch.delenv("DBOS_DB_URL", raising=False)
    result = get_workflow_state(scope="checkout")
    assert result["scope"] == "checkout"


def test_unavailable_scope_none_by_default(monkeypatch):
    monkeypatch.delenv("DBOS_DB_URL", raising=False)
    result = get_workflow_state()
    assert result["scope"] is None


# ---------------------------------------------------------------------------
# Success path (DBOS_DB_URL set)
# ---------------------------------------------------------------------------

def _mock_conn(rows):
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = rows
    return conn


def test_returns_ok_status_when_db_responds(monkeypatch):
    monkeypatch.setenv("DBOS_DB_URL", "postgresql://localhost/dbos")
    with patch("chips.mcp.tools.workflow.psycopg.connect", return_value=_mock_conn([])):
        result = get_workflow_state()
    assert result["status"] == "ok"


def test_workflows_list_populated_from_rows(monkeypatch):
    monkeypatch.setenv("DBOS_DB_URL", "postgresql://localhost/dbos")
    with patch("chips.mcp.tools.workflow.psycopg.connect", return_value=_mock_conn([_WF_ROW])):
        result = get_workflow_state()
    assert len(result["workflows"]) == 1


def test_workflow_has_expected_keys(monkeypatch):
    monkeypatch.setenv("DBOS_DB_URL", "postgresql://localhost/dbos")
    with patch("chips.mcp.tools.workflow.psycopg.connect", return_value=_mock_conn([_WF_ROW])):
        result = get_workflow_state()
    wf = result["workflows"][0]
    for key in ("workflow_uuid", "status", "name", "updated_at"):
        assert key in wf, f"missing key: {key}"


def test_workflow_values_correct(monkeypatch):
    monkeypatch.setenv("DBOS_DB_URL", "postgresql://localhost/dbos")
    with patch("chips.mcp.tools.workflow.psycopg.connect", return_value=_mock_conn([_WF_ROW])):
        result = get_workflow_state()
    wf = result["workflows"][0]
    assert wf["workflow_uuid"] == "wf-uuid-001"
    assert wf["status"] == "ERROR"
    assert wf["name"] == "checkout.process_payment"
    assert wf["updated_at"] == _DT.isoformat()


def test_scope_filter_passed_to_query(monkeypatch):
    monkeypatch.setenv("DBOS_DB_URL", "postgresql://localhost/dbos")
    conn = _mock_conn([])
    with patch("chips.mcp.tools.workflow.psycopg.connect", return_value=conn):
        get_workflow_state(scope="checkout")
    _, params = conn.execute.call_args[0]
    assert any("checkout" in str(p) for p in params)


def test_connection_is_closed_after_query(monkeypatch):
    monkeypatch.setenv("DBOS_DB_URL", "postgresql://localhost/dbos")
    conn = _mock_conn([])
    with patch("chips.mcp.tools.workflow.psycopg.connect", return_value=conn):
        get_workflow_state()
    conn.close.assert_called_once()


def test_connection_closed_on_error(monkeypatch):
    monkeypatch.setenv("DBOS_DB_URL", "postgresql://localhost/dbos")
    conn = MagicMock()
    conn.execute.side_effect = Exception("db error")
    with patch("chips.mcp.tools.workflow.psycopg.connect", return_value=conn):
        result = get_workflow_state()
    conn.close.assert_called_once()
    assert result["status"].startswith("error:")


# ---------------------------------------------------------------------------
# Error path
# ---------------------------------------------------------------------------

def test_returns_error_status_on_db_failure(monkeypatch):
    monkeypatch.setenv("DBOS_DB_URL", "postgresql://localhost/dbos")
    with patch("chips.mcp.tools.workflow.psycopg.connect", side_effect=Exception("connection refused")):
        result = get_workflow_state()
    assert result["status"].startswith("error:")
    assert result["workflows"] == []


def test_error_preserves_scope(monkeypatch):
    monkeypatch.setenv("DBOS_DB_URL", "postgresql://localhost/dbos")
    with patch("chips.mcp.tools.workflow.psycopg.connect", side_effect=Exception("timeout")):
        result = get_workflow_state(scope="checkout")
    assert result["scope"] == "checkout"
