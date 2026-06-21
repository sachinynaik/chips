from __future__ import annotations

from typing import Callable

import psycopg
from mcp.server.fastmcp import FastMCP

from chips.mcp.tools.constraints import add_constraint as _add_constraint
from chips.mcp.tools.constraints import get_constraints as _get_constraints
from chips.mcp.tools.constraints import retire_constraint as _retire_constraint


class ConstraintsModule:
    name = "constraints"

    def __init__(self, conn_factory: Callable[[], psycopg.Connection]) -> None:
        self._conn_factory = conn_factory

    def get_constraints(
        self,
        scope: str | None = None,
        tenant_id: str | None = None,
    ) -> dict:
        from chips.tenant import require_tenant

        require_tenant(tenant_id)
        conn = self._conn_factory()
        try:
            return _get_constraints(conn, scope=scope, tenant_id=tenant_id)
        finally:
            conn.close()

    def add_constraint(
        self,
        *,
        scope_pattern: str = "*",
        kind: str,
        text: str,
        reason: str | None = None,
        source_kind: str | None = None,
        source_ref: str | None = None,
        target: dict | None = None,
        tenant_id: str | None = None,
    ) -> dict:
        from chips.tenant import require_tenant

        require_tenant(tenant_id)
        conn = self._conn_factory()
        try:
            return _add_constraint(
                conn,
                scope_pattern=scope_pattern,
                kind=kind,
                text=text,
                reason=reason,
                source_kind=source_kind,
                source_ref=source_ref,
                target=target,
                tenant_id=tenant_id,
            )
        finally:
            conn.close()

    def retire_constraint(
        self,
        constraint_id: str,
        tenant_id: str | None = None,
    ) -> dict:
        from chips.tenant import require_tenant

        require_tenant(tenant_id)
        conn = self._conn_factory()
        try:
            return _retire_constraint(conn, constraint_id=constraint_id, tenant_id=tenant_id)
        finally:
            conn.close()

    def register(self, app: FastMCP) -> None:
        app.tool()(self.get_constraints)
        app.tool()(self.add_constraint)
        app.tool()(self.retire_constraint)
