from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from chips.compiler.policy import PolicyLoader


class PolicyModule:
    name = "policy"

    def __init__(self, policy_loader: PolicyLoader) -> None:
        self._loader = policy_loader

    def get_policy(self, scope: str | None = None) -> dict:
        """Return governance rules (forbidden / required) for the given scope."""
        policies = self._loader.for_scope(scope)
        forbidden = [item for p in policies for item in p.forbidden]
        required = [item for p in policies for item in p.required]
        return {
            "scope": scope,
            "forbidden": forbidden,
            "required": required,
        }

    def register(self, app: FastMCP) -> None:
        app.tool()(self.get_policy)
