"""Unit tests for RuntimeModule — delegation and registration."""
from __future__ import annotations

from unittest.mock import patch
from mcp.server.fastmcp import FastMCP


def _fake_result(scope=None):
    return {"spans": [], "scope": scope, "status": "unavailable"}


# ---------------------------------------------------------------------------
# Module identity
# ---------------------------------------------------------------------------

def test_runtime_module_name():
    from chips.mcp.modules.runtime import RuntimeModule
    assert RuntimeModule().name == "runtime"


# ---------------------------------------------------------------------------
# Delegation
# ---------------------------------------------------------------------------

def test_get_runtime_context_delegates_to_tool():
    from chips.mcp.modules.runtime import RuntimeModule
    with patch("chips.mcp.modules.runtime._get_runtime_context", return_value=_fake_result()) as fn:
        RuntimeModule().get_runtime_context(scope="auth")
    fn.assert_called_once()


def test_get_runtime_context_passes_scope():
    from chips.mcp.modules.runtime import RuntimeModule
    with patch("chips.mcp.modules.runtime._get_runtime_context", return_value=_fake_result()) as fn:
        RuntimeModule().get_runtime_context(scope="auth")
    _, kwargs = fn.call_args
    assert kwargs["scope"] == "auth"


def test_get_runtime_context_returns_tool_result():
    from chips.mcp.modules.runtime import RuntimeModule
    fake = {"spans": [{"service": "auth"}], "scope": "auth", "status": "ok"}
    with patch("chips.mcp.modules.runtime._get_runtime_context", return_value=fake):
        result = RuntimeModule().get_runtime_context()
    assert result == fake


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def test_runtime_module_registers_tool():
    from chips.mcp.modules.runtime import RuntimeModule
    app = FastMCP("test")
    RuntimeModule().register(app)
    assert "get_runtime_context" in app._tool_manager._tools
