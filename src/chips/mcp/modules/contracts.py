from __future__ import annotations

from mcp.server.fastmcp import FastMCP


class ContractsModule:
    name = "contracts"

    def get_contracts(self, scope: str | None = None) -> dict:
        """Return API contracts and interface definitions. Not yet implemented."""
        return {"contracts": [], "scope": scope, "status": "not_implemented"}

    def register(self, app: FastMCP) -> None:
        app.tool()(self.get_contracts)
