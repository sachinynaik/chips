"""MCP server wiring tests — verifies the bus app and tool registrations."""
from unittest.mock import MagicMock, patch


def test_server_app_exists():
    from chips.mcp.server import app
    assert app is not None
    assert app.name == "chips-cortex"


def test_server_exposes_all_nine_tools():
    from chips.mcp.server import app
    registered = set(app._tool_manager._tools.keys())
    expected = {
        "search_memory",
        "get_recent_commits",
        "get_context_brief",
        "get_diffs",
        "get_runtime_context",
        "get_workflow_state",
        "get_contracts",
        "get_test_context",
        "get_policy",
    }
    assert expected.issubset(registered)


def test_search_memory_tool_embeds_query_before_searching():
    fake_embedding = [0.1] * 768
    fake_results = [
        {
            "id": "abc",
            "type": "lesson",
            "scope": "api",
            "content": "always validate inputs",
            "confidence": 0.9,
            "source": None,
            "tags": [],
            "score": None,
            "signal_breakdown": {},
        }
    ]

    with patch("chips.mcp.modules.memory._search_memory", return_value=fake_results):
        from chips.mcp.modules.memory import MemoryModule
        embedder = MagicMock()
        embedder.embed.return_value = fake_embedding
        module = MemoryModule(conn_factory=MagicMock(), embedder=embedder)
        result = module.search_memory(query="test query", scope="api")

    embedder.embed.assert_called_once_with("test query")
    assert result == fake_results


def test_get_recent_commits_tool_delegates_to_db():
    fake_commits = [
        {
            "sha": "abc123",
            "author": "Alice",
            "committed_at": "2026-05-10T12:00:00+00:00",
            "message": "fix checkout",
            "files_changed": ["src/checkout.py"],
            "cochange_pairs": [],
        }
    ]

    with patch("chips.mcp.modules.git._get_recent_commits", return_value=fake_commits):
        from chips.mcp.modules.git import GitModule
        module = GitModule(conn_factory=MagicMock())
        result = module.get_recent_commits(limit=5)

    assert result == fake_commits
