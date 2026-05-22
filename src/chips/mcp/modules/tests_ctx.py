from __future__ import annotations

from typing import Callable

import psycopg
from mcp.server.fastmcp import FastMCP

from chips.mcp.tools.tests_ctx import get_test_context as _get_test_context


class TestsModule:
    name = "tests_ctx"

    def __init__(self, conn_factory: Callable[[], psycopg.Connection]) -> None:
        self._conn_factory = conn_factory

    def get_test_context(
        self,
        scope: str | None = None,
        limit: int = 20,
    ) -> dict:
        conn = self._conn_factory()
        try:
            return _get_test_context(conn, scope=scope, limit=limit)
        finally:
            conn.close()

    def register(self, app: FastMCP) -> None:
        app.tool()(self.get_test_context)
