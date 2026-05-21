from __future__ import annotations

from typing import Callable

import psycopg
from mcp.server.fastmcp import FastMCP

from chips.mcp.tools.diffs import get_diffs_for_scope as _get_diffs_for_scope


class DiffsModule:
    name = "diffs"

    def __init__(self, conn_factory: Callable[[], psycopg.Connection]) -> None:
        self._conn_factory = conn_factory

    def get_diffs(self, scope: str | None = None, limit: int = 10) -> dict:
        """Return recent commits and co-change pairs filtered by scope."""
        conn = self._conn_factory()
        try:
            return _get_diffs_for_scope(conn, scope=scope, limit=limit)
        finally:
            conn.close()

    def register(self, app: FastMCP) -> None:
        app.tool()(self.get_diffs)
