from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from chips.mcp.tools.runtime import get_runtime_context as _get_runtime_context


class RuntimeModule:
    name = "runtime"

    def get_runtime_context(self, scope: str | None = None) -> dict:
        return _get_runtime_context(scope=scope)

    def register(self, app: FastMCP) -> None:
        app.tool()(self.get_runtime_context)
