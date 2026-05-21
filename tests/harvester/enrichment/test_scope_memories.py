from __future__ import annotations
from unittest.mock import MagicMock
from chips.harvester.enrichment.scope_memories import ScopeMemoryFetcher

def _mock_conn(rows):
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = rows
    return conn

def test_fetch_returns_memories_for_scope():
    conn = _mock_conn([("never call raw SQL", "invariant", ["security"])])
    result = ScopeMemoryFetcher().fetch(conn, "auth")
    assert len(result) == 1
    assert result[0]["content"] == "never call raw SQL"

def test_fetch_returns_empty_for_empty_scope():
    result = ScopeMemoryFetcher().fetch(MagicMock(), "")
    assert result == []

def test_fetch_returns_empty_on_db_error():
    conn = MagicMock()
    conn.execute.side_effect = Exception("db error")
    result = ScopeMemoryFetcher().fetch(conn, "auth")
    assert result == []

def test_fetch_handles_null_tags():
    conn = _mock_conn([("lesson content", "lesson", None)])
    result = ScopeMemoryFetcher().fetch(conn, "auth")
    assert result[0]["tags"] == []
