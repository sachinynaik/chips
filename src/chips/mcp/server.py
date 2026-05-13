from __future__ import annotations

import os

import psycopg
from mcp.server.fastmcp import FastMCP

from chips.compiler.builder import BriefBuilder
from chips.compiler.compressor import OllamaCompressor
from chips.harvester.embedding import OllamaEmbedder
from chips.mcp.tools.git import get_recent_commits as _get_recent_commits
from chips.mcp.tools.memory import search_memory as _search_memory

app = FastMCP("chips-cortex")


def _get_embedder() -> OllamaEmbedder:
    return OllamaEmbedder(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        model=os.getenv("OLLAMA_MODEL", "nomic-embed-text"),
    )


def _get_compressor() -> OllamaCompressor:
    return OllamaCompressor(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        model=os.getenv("OLLAMA_COMPRESS_MODEL", "qwen2.5-coder:1.5b"),
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


@app.tool()
def get_context_brief(task: str, scope: str | None = None) -> dict:
    """Compile a ranked, compressed context brief for a coding task."""
    embedder = _get_embedder()
    compressor = _get_compressor()
    conn = _get_conn()
    try:
        builder = BriefBuilder(conn, embedder, compressor)
        brief = builder.build(task, scope=scope)
    finally:
        conn.close()

    return {
        "brief_id": str(brief.brief_id),
        "task": brief.task,
        "task_kind": brief.task_kind,
        "scope": brief.scope,
        "generated_at": brief.generated_at.isoformat(),
        "latency_ms": brief.latency_ms,
        "hard_constraints": brief.hard_constraints,
        "compressed_context": brief.compressed_context,
        "ranked_signals": [
            {
                "item_id": s.item_id,
                "item_type": s.item_type,
                "score": s.score,
                "signal_breakdown": s.signal_breakdown,
            }
            for s in brief.ranked_signals
        ],
        "retrieved_memories": brief.retrieved.memories,
    }
