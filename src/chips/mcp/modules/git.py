from __future__ import annotations

from typing import Callable

import psycopg
from mcp.server.fastmcp import FastMCP

from chips.mcp.tools.git import get_recent_commits as _get_recent_commits


class GitModule:
    name = "git"

    def __init__(self, conn_factory: Callable[[], psycopg.Connection]) -> None:
        self._conn_factory = conn_factory

    def get_recent_commits(self, limit: int = 10) -> list[dict]:
        conn = self._conn_factory()
        try:
            return _get_recent_commits(conn, limit=limit)
        finally:
            conn.close()

    def register(self, app: FastMCP) -> None:
        app.tool()(self.get_recent_commits)
