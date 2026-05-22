from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from chips.mcp.tools.workflow import get_workflow_state as _get_workflow_state


class WorkflowModule:
    name = "workflow"

    def get_workflow_state(self, scope: str | None = None) -> dict:
        return _get_workflow_state(scope=scope)

    def register(self, app: FastMCP) -> None:
        app.tool()(self.get_workflow_state)
