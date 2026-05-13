"""RED: memory repository tests."""
import uuid
import pytest
from chips.memory.repository import MemoryRepository, MemoryRecord, MemoryType


def test_insert_memory_returns_id(conn):
    repo = MemoryRepository(conn)
    record = MemoryRecord(
        type=MemoryType.INVARIANT,
        scope="valet.checkout",
        content="DBOS owns all workflow state.",
        source="manual",
    )
    memory_id = repo.insert(record)
    assert isinstance(memory_id, uuid.UUID)


def test_get_memory_by_id(conn):
    repo = MemoryRepository(conn)
    record = MemoryRecord(
        type=MemoryType.PITFALL,
        scope="auth",
        content="Keycloak token cache must be invalidated on role change.",
        source="manual",
    )
    memory_id = repo.insert(record)
    fetched = repo.get(memory_id)
    assert fetched is not None
    assert fetched.scope == "auth"
    assert fetched.type == MemoryType.PITFALL
    assert fetched.content == "Keycloak token cache must be invalidated on role change."


def test_archived_memories_excluded_by_default(conn):
    repo = MemoryRepository(conn)
    record = MemoryRecord(
        type=MemoryType.LESSON,
        scope="parking",
        content="MiniZinc solutions should be cached.",
        source="manual",
    )
    memory_id = repo.insert(record)
    repo.archive(memory_id)

    fetched = repo.get(memory_id)
    assert fetched is None


def test_list_by_scope(conn):
    repo = MemoryRepository(conn)
    for i in range(3):
        repo.insert(MemoryRecord(
            type=MemoryType.LESSON,
            scope="valet.parking",
            content=f"Lesson {i}",
            source="test",
        ))
    repo.insert(MemoryRecord(
        type=MemoryType.DECISION,
        scope="auth",
        content="Other scope",
        source="test",
    ))

    results = repo.list_by_scope("valet.parking")
    assert len(results) == 3
    assert all(r.scope == "valet.parking" for r in results)


def test_semantic_search_requires_embedding(conn):
    repo = MemoryRepository(conn)
    record = MemoryRecord(
        type=MemoryType.INVARIANT,
        scope="checkout",
        content="Checkout must verify active vehicle.",
        source="test",
        embedding=[0.1] * 768,
    )
    repo.insert(record)

    results = repo.semantic_search(query_embedding=[0.1] * 768, limit=20)
    assert len(results) >= 1
    contents = [r.content for r in results]
    assert "Checkout must verify active vehicle." in contents


def test_semantic_search_excludes_records_without_embedding(conn):
    repo = MemoryRepository(conn)
    repo.insert(MemoryRecord(
        type=MemoryType.LESSON,
        scope="misc",
        content="No embedding record",
        source="test",
    ))

    results = repo.semantic_search(query_embedding=[0.0] * 768, limit=10)
    contents = [r.content for r in results]
    assert "No embedding record" not in contents


def test_confidence_defaults_to_0_8(conn):
    repo = MemoryRepository(conn)
    record = MemoryRecord(
        type=MemoryType.DECISION,
        scope="infra",
        content="Use pgvector for engineering memory.",
        source="manual",
    )
    memory_id = repo.insert(record)
    fetched = repo.get(memory_id)
    assert fetched.confidence == pytest.approx(0.8)
