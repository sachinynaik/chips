"""RED: MCP /context/memory tool tests."""
import pytest
from chips.memory.repository import MemoryRepository, MemoryRecord, MemoryType
from chips.mcp.tools.memory import search_memory


def test_search_memory_returns_results(conn):
    repo = MemoryRepository(conn)
    repo.insert(MemoryRecord(
        type=MemoryType.INVARIANT,
        scope="valet.checkout",
        content="Checkout must verify active vehicle before starting workflow.",
        source="test",
        embedding=[0.2] * 768,
    ))

    results = search_memory(
        conn=conn,
        query_embedding=[0.2] * 768,
        scope=None,
        limit=5,
    )
    assert len(results) >= 1
    assert results[0]["type"] == "invariant"
    assert "content" in results[0]
    assert "score" in results[0]
    assert "signal_breakdown" in results[0]


def test_search_memory_scope_filter(conn):
    repo = MemoryRepository(conn)
    repo.insert(MemoryRecord(
        type=MemoryType.LESSON,
        scope="auth",
        content="Auth lesson.",
        source="test",
        embedding=[0.3] * 768,
    ))
    repo.insert(MemoryRecord(
        type=MemoryType.LESSON,
        scope="parking",
        content="Parking lesson.",
        source="test",
        embedding=[0.3] * 768,
    ))

    results = search_memory(
        conn=conn,
        query_embedding=[0.3] * 768,
        scope="auth",
        limit=10,
    )
    scopes = {r["scope"] for r in results}
    assert scopes == {"auth"}


def test_search_memory_respects_limit(conn):
    repo = MemoryRepository(conn)
    for i in range(10):
        repo.insert(MemoryRecord(
            type=MemoryType.LESSON,
            scope="test.limit",
            content=f"Lesson {i}",
            source="test",
            embedding=[float(i) / 10] * 768,
        ))

    results = search_memory(
        conn=conn,
        query_embedding=[0.5] * 768,
        scope="test.limit",
        limit=3,
    )
    assert len(results) <= 3
