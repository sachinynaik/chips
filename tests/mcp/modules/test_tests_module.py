"""Unit tests for TestsModule — delegation, lifecycle, registration."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from mcp.server.fastmcp import FastMCP


def _fake_result(scope=None):
    return {"test_files": [], "cochange_pairs": [], "scope": scope, "status": "ok"}


def _make_module():
    from chips.mcp.modules.tests_ctx import TestsModule
    return TestsModule(conn_factory=MagicMock())


# ---------------------------------------------------------------------------
# Module identity
# ---------------------------------------------------------------------------

def test_tests_module_name():
    assert _make_module().name == "tests_ctx"


# ---------------------------------------------------------------------------
# Delegation
# ---------------------------------------------------------------------------

def test_get_test_context_delegates_to_tool():
    with patch("chips.mcp.modules.tests_ctx._get_test_context", return_value=_fake_result()) as fn:
        _make_module().get_test_context(scope="auth", limit=10)
    fn.assert_called_once()


def test_get_test_context_passes_scope():
    with patch("chips.mcp.modules.tests_ctx._get_test_context", return_value=_fake_result()) as fn:
        _make_module().get_test_context(scope="auth", limit=10)
    _, kwargs = fn.call_args
    assert kwargs["scope"] == "auth"


def test_get_test_context_passes_limit():
    with patch("chips.mcp.modules.tests_ctx._get_test_context", return_value=_fake_result()) as fn:
        _make_module().get_test_context(scope=None, limit=7)
    _, kwargs = fn.call_args
    assert kwargs["limit"] == 7


def test_get_test_context_returns_tool_result():
    fake = {"test_files": [{"file_path": "test_x.py"}], "cochange_pairs": [], "scope": "x", "status": "ok"}
    with patch("chips.mcp.modules.tests_ctx._get_test_context", return_value=fake):
        result = _make_module().get_test_context()
    assert result == fake


# ---------------------------------------------------------------------------
# Connection lifecycle
# ---------------------------------------------------------------------------

def test_get_test_context_closes_connection_on_success():
    conn = MagicMock()
    from chips.mcp.modules.tests_ctx import TestsModule
    with patch("chips.mcp.modules.tests_ctx._get_test_context", return_value=_fake_result()):
        TestsModule(conn_factory=MagicMock(return_value=conn)).get_test_context()
    conn.close.assert_called_once()


def test_get_test_context_closes_connection_on_error():
    conn = MagicMock()
    from chips.mcp.modules.tests_ctx import TestsModule
    with patch("chips.mcp.modules.tests_ctx._get_test_context", side_effect=RuntimeError("db")):
        with pytest.raises(RuntimeError):
            TestsModule(conn_factory=MagicMock(return_value=conn)).get_test_context()
    conn.close.assert_called_once()


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def test_tests_module_registers_tool():
    app = FastMCP("test")
    _make_module().register(app)
    assert "get_test_context" in app._tool_manager._tools
