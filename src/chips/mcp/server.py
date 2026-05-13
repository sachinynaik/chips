from __future__ import annotations

import os

import psycopg
from mcp.server.fastmcp import FastMCP

from chips.harvester.embedding import OllamaEmbedder
from chips.mcp.tools.git import get_recent_commits as _get_recent_commits
from chips.mcp.tools.memory import search_memory as _search_memory

app = FastMCP("chips-cortex")


def _get_embedder() -> OllamaEmbedder:
    return OllamaEmbedder(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        model=os.getenv("OLLAMA_MODEL", "nomic-embed-text"),
    )


def _get_conn() -> psycopg.Connection:
    return psycopg.connect(os.environ["CHIPS_DB_URL"])


@app.tool()
def search_memory(query: str, scope: str | None = None, limit: int = 10) -> list[dict]:
    """Search engineering memory by semantic similarity."""
    embedder = _get_embedder()
    embedding = embedder.embed(query)
    conn = _get_conn()
    try:
        return _search_memory(conn, embedding, scope=scope, limit=limit)
    finally:
        conn.close()


@app.tool()
def get_recent_commits(limit: int = 10) -> list[dict]:
    """Return recent git commits with co-change pairs."""
    conn = _get_conn()
    try:
        return _get_recent_commits(conn, limit=limit)
    finally:
        conn.close()
