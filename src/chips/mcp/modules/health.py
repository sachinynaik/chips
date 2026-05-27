from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from chips.mcp.tools.health import get_source_health as _get_source_health


class HealthModule:
    name = "health"

    def get_source_health(self) -> dict:
        return _get_source_health()

    def register(self, app: FastMCP) -> None:
        app.tool()(self.get_source_health)
