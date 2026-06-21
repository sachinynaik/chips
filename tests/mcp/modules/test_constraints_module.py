from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from mcp.server.fastmcp import FastMCP


def _make_module():
    from chips.mcp.modules.constraints import ConstraintsModule

    return ConstraintsModule(conn_factory=MagicMock())


def test_constraints_module_name():
    assert _make_module().name == "constraints"


def test_get_constraints_delegates_to_tool():
    with patch("chips.mcp.modules.constraints._get_constraints", return_value={"status": "ok", "constraints": []}) as fn:
        _make_module().get_constraints(scope="checkout", tenant_id="tenant-x")
    fn.assert_called_once()


def test_add_constraint_delegates_to_tool():
    with patch("chips.mcp.modules.constraints._add_constraint", return_value={"status": "ok", "constraint_id": str(uuid.uuid4())}) as fn:
        _make_module().add_constraint(
            scope_pattern="checkout",
            kind="known_issue",
            text="avoid double decrement",
            tenant_id="tenant-x",
        )
    fn.assert_called_once()


def test_retire_constraint_delegates_to_tool():
    cid = str(uuid.uuid4())
    with patch("chips.mcp.modules.constraints._retire_constraint", return_value={"status": "ok", "constraint_id": cid, "retired": True}) as fn:
        _make_module().retire_constraint(constraint_id=cid, tenant_id="tenant-x")
    fn.assert_called_once()


def test_constraints_module_closes_connection_on_success():
    conn = MagicMock()
    from chips.mcp.modules.constraints import ConstraintsModule

    with patch("chips.mcp.modules.constraints._get_constraints", return_value={"status": "ok", "constraints": []}):
        ConstraintsModule(conn_factory=MagicMock(return_value=conn)).get_constraints(scope="checkout")

    conn.close.assert_called_once()


def test_constraints_module_closes_connection_on_error():
    conn = MagicMock()
    from chips.mcp.modules.constraints import ConstraintsModule

    with patch("chips.mcp.modules.constraints._add_constraint", side_effect=RuntimeError("db")):
        with pytest.raises(RuntimeError):
            ConstraintsModule(conn_factory=MagicMock(return_value=conn)).add_constraint(
                scope_pattern="checkout",
                kind="known_issue",
                text="avoid double decrement",
            )

    conn.close.assert_called_once()


def test_constraints_module_registers_tools():
    app = FastMCP("test")
    _make_module().register(app)
    tools = app._tool_manager._tools
    assert "get_constraints" in tools
    assert "add_constraint" in tools
    assert "retire_constraint" in tools
