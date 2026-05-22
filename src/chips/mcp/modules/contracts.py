from __future__ import annotations

from typing import Callable

import psycopg
from mcp.server.fastmcp import FastMCP

from chips.mcp.tools.contracts import get_contracts as _get_contracts


class ContractsModule:
    name = "contracts"

    def __init__(self, conn_factory: Callable[[], psycopg.Connection]) -> None:
        self._conn_factory = conn_factory

    def get_contracts(
        self,
        scope: str | None = None,
        limit: int = 20,
    ) -> dict:
        conn = self._conn_factory()
        try:
            return _get_contracts(conn, scope=scope, limit=limit)
        finally:
            conn.close()

    def register(self, app: FastMCP) -> None:
        app.tool()(self.get_contracts)
