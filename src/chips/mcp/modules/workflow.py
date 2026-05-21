from __future__ import annotations

from mcp.server.fastmcp import FastMCP


class WorkflowModule:
    name = "workflow"

    def get_workflow_state(self, scope: str | None = None) -> dict:
        """Return DBOS workflow state and step history. Not yet implemented."""
        return {"workflows": [], "scope": scope, "status": "not_implemented"}

    def register(self, app: FastMCP) -> None:
        app.tool()(self.get_workflow_state)
