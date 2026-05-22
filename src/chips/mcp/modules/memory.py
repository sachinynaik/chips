from __future__ import annotations

from typing import Callable

import psycopg
from mcp.server.fastmcp import FastMCP

from chips.harvester.embedding import OllamaEmbedder
from chips.mcp.tools.memory import search_memory as _search_memory


class MemoryModule:
    name = "memory"

    def __init__(
        self,
        conn_factory: Callable[[], psycopg.Connection],
        embedder: OllamaEmbedder,
    ) -> None:
        self._conn_factory = conn_factory
        self._embedder = embedder

    def search_memory(
        self,
        query: str,
        scope: str | None = None,
        limit: int = 10,
        tenant_id: str | None = None,
    ) -> list[dict]:
        embedding = self._embedder.embed(query)
        conn = self._conn_factory()
        try:
            return _search_memory(conn, embedding, scope=scope, limit=limit, tenant_id=tenant_id)
        finally:
            conn.close()

    def register(self, app: FastMCP) -> None:
        app.tool()(self.search_memory)
