from __future__ import annotations

from mcp.server.fastmcp import FastMCP


class TestsModule:
    name = "tests_ctx"

    def get_test_context(self, scope: str | None = None) -> dict:
        """Return test results and coverage signals for the given scope. Not yet implemented."""
        return {"tests": [], "scope": scope, "status": "not_implemented"}

    def register(self, app: FastMCP) -> None:
        app.tool()(self.get_test_context)
