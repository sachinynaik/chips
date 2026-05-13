from __future__ import annotations
import psycopg

from chips.memory.repository import MemoryRepository


def search_memory(
    conn: psycopg.Connection,
    query_embedding: list[float],
    scope: str | None = None,
    limit: int = 10,
) -> list[dict]:
    repo = MemoryRepository(conn)  # register_vector happens inside __init__
    records = repo.semantic_search(
        query_embedding=query_embedding,
        scope=scope,
        limit=limit,
    )
    return [
        {
            "id": str(r.id),
            "type": str(r.type),
            "scope": r.scope,
            "content": r.content,
            "confidence": r.confidence,
            "source": r.source,
            "tags": r.tags,
            "score": None,
            "signal_breakdown": {
                "semantic": None,
                "recency": None,
                "graph": None,
                "failure": None,
                "cochange": None,
            },
        }
        for r in records
    ]
