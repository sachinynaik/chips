from __future__ import annotations

from mcp.server.fastmcp import FastMCP


class DiffsModule:
    name = "diffs"

    def get_diffs(self, scope: str | None = None) -> dict:
        """Return code diffs for the current working context. Not yet implemented."""
        return {"diffs": [], "scope": scope, "status": "not_implemented"}

    def register(self, app: FastMCP) -> None:
        app.tool()(self.get_diffs)
