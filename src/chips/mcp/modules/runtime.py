from __future__ import annotations

from mcp.server.fastmcp import FastMCP


class RuntimeModule:
    name = "runtime"

    def get_runtime_context(self, scope: str | None = None) -> dict:
        """Return OTel spans and runtime traces for the given scope. Not yet implemented."""
        return {"spans": [], "scope": scope, "status": "not_implemented"}

    def register(self, app: FastMCP) -> None:
        app.tool()(self.get_runtime_context)
