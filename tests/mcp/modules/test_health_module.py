from __future__ import annotations

from unittest.mock import patch


def test_health_module_name():
    from chips.mcp.modules.health import HealthModule

    assert HealthModule().name == "health"


def test_get_source_health_delegates_to_tool():
    fake = {"generated_at": "2026-01-01T00:00:00+00:00", "sources": {}}

    with patch("chips.mcp.modules.health._get_source_health", return_value=fake) as fn:
        from chips.mcp.modules.health import HealthModule

        result = HealthModule().get_source_health()

    fn.assert_called_once_with()
    assert result == fake


def test_health_module_registers_tool():
    from mcp.server.fastmcp import FastMCP
    from chips.mcp.modules.health import HealthModule

    app = FastMCP("test")
    HealthModule().register(app)
    assert "get_source_health" in app._tool_manager._tools
