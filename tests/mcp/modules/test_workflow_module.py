"""Unit tests for WorkflowModule — delegation and registration."""
from __future__ import annotations

from unittest.mock import patch
from mcp.server.fastmcp import FastMCP


def _fake_result(scope=None):
    return {"workflows": [], "scope": scope, "status": "unavailable"}


# ---------------------------------------------------------------------------
# Module identity
# ---------------------------------------------------------------------------

def test_workflow_module_name():
    from chips.mcp.modules.workflow import WorkflowModule
    assert WorkflowModule().name == "workflow"


# ---------------------------------------------------------------------------
# Delegation
# ---------------------------------------------------------------------------

def test_get_workflow_state_delegates_to_tool():
    from chips.mcp.modules.workflow import WorkflowModule
    with patch("chips.mcp.modules.workflow._get_workflow_state", return_value=_fake_result()) as fn:
        WorkflowModule().get_workflow_state(scope="checkout")
    fn.assert_called_once()


def test_get_workflow_state_passes_scope():
    from chips.mcp.modules.workflow import WorkflowModule
    with patch("chips.mcp.modules.workflow._get_workflow_state", return_value=_fake_result()) as fn:
        WorkflowModule().get_workflow_state(scope="checkout")
    _, kwargs = fn.call_args
    assert kwargs["scope"] == "checkout"


def test_get_workflow_state_returns_tool_result():
    from chips.mcp.modules.workflow import WorkflowModule
    fake = {"workflows": [{"workflow_uuid": "x"}], "scope": "checkout", "status": "ok"}
    with patch("chips.mcp.modules.workflow._get_workflow_state", return_value=fake):
        result = WorkflowModule().get_workflow_state()
    assert result == fake


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def test_workflow_module_registers_tool():
    from chips.mcp.modules.workflow import WorkflowModule
    app = FastMCP("test")
    WorkflowModule().register(app)
    assert "get_workflow_state" in app._tool_manager._tools
