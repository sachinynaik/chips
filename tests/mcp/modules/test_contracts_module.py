"""Unit tests for ContractsModule — delegation, lifecycle, registration."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from mcp.server.fastmcp import FastMCP


def _fake_result(scope=None):
    return {"contracts": [], "scope": scope, "status": "ok"}


def _make_module():
    from chips.mcp.modules.contracts import ContractsModule
    return ContractsModule(conn_factory=MagicMock())


# ---------------------------------------------------------------------------
# Module identity
# ---------------------------------------------------------------------------

def test_contracts_module_name():
    assert _make_module().name == "contracts"


# ---------------------------------------------------------------------------
# Delegation
# ---------------------------------------------------------------------------

def test_get_contracts_delegates_to_tool():
    with patch("chips.mcp.modules.contracts._get_contracts", return_value=_fake_result()) as fn:
        _make_module().get_contracts(scope="payments", limit=10)
    fn.assert_called_once()


def test_get_contracts_passes_scope():
    with patch("chips.mcp.modules.contracts._get_contracts", return_value=_fake_result()) as fn:
        _make_module().get_contracts(scope="payments", limit=10)
    _, kwargs = fn.call_args
    assert kwargs["scope"] == "payments"


def test_get_contracts_passes_limit():
    with patch("chips.mcp.modules.contracts._get_contracts", return_value=_fake_result()) as fn:
        _make_module().get_contracts(scope=None, limit=5)
    _, kwargs = fn.call_args
    assert kwargs["limit"] == 5


def test_get_contracts_returns_tool_result():
    fake = {"contracts": [{"id": "x"}], "scope": "auth", "status": "ok"}
    with patch("chips.mcp.modules.contracts._get_contracts", return_value=fake):
        result = _make_module().get_contracts()
    assert result == fake


# ---------------------------------------------------------------------------
# Connection lifecycle
# ---------------------------------------------------------------------------

def test_get_contracts_closes_connection_on_success():
    conn = MagicMock()
    with patch("chips.mcp.modules.contracts._get_contracts", return_value=_fake_result()):
        ContractsModule = _make_module().__class__
        ContractsModule(conn_factory=MagicMock(return_value=conn)).get_contracts()
    conn.close.assert_called_once()


def test_get_contracts_closes_connection_on_error():
    conn = MagicMock()
    from chips.mcp.modules.contracts import ContractsModule
    with patch("chips.mcp.modules.contracts._get_contracts", side_effect=RuntimeError("db")):
        with pytest.raises(RuntimeError):
            ContractsModule(conn_factory=MagicMock(return_value=conn)).get_contracts()
    conn.close.assert_called_once()


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def test_contracts_module_registers_tool():
    app = FastMCP("test")
    _make_module().register(app)
    assert "get_contracts" in app._tool_manager._tools


def test_get_contracts_passes_tenant_id():
    _TENANT = "bbbbbbbb-0000-0000-0000-000000000001"
    with patch("chips.mcp.modules.contracts._get_contracts", return_value=_fake_result()) as fn:
        _make_module().get_contracts(tenant_id=_TENANT)
    _, kwargs = fn.call_args
    assert kwargs["tenant_id"] == _TENANT
