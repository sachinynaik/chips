"""MCP server wiring tests — verifies tools are registered and callable."""
from unittest.mock import MagicMock, patch


def test_server_app_exists():
    from chips.mcp.server import app
    assert app is not None
    assert app.name == "chips-cortex"


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

    with (
        patch("chips.mcp.server._get_embedder") as mock_embedder_factory,
        patch("chips.mcp.server._get_conn") as mock_conn_factory,
        patch("chips.mcp.server._search_memory", return_value=fake_results) as mock_search,
    ):
        mock_embedder = MagicMock()
        mock_embedder.embed.return_value = fake_embedding
        mock_embedder_factory.return_value = mock_embedder
        mock_conn_factory.return_value = MagicMock()

        from chips.mcp.server import search_memory
        result = search_memory(query="test query", scope="api")

    mock_embedder.embed.assert_called_once_with("test query")
    mock_search.assert_called_once()
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

    with (
        patch("chips.mcp.server._get_conn") as mock_conn_factory,
        patch("chips.mcp.server._get_recent_commits", return_value=fake_commits) as mock_git,
    ):
        mock_conn_factory.return_value = MagicMock()

        from chips.mcp.server import get_recent_commits
        result = get_recent_commits(limit=5)

    mock_git.assert_called_once()
    assert result == fake_commits
