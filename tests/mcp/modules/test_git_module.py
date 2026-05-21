"""RED: GitModule tests."""
from unittest.mock import MagicMock, patch


def test_git_module_name():
    from chips.mcp.modules.git import GitModule
    assert GitModule(conn_factory=MagicMock()).name == "git"


def test_get_recent_commits_delegates_to_db():
    from chips.mcp.modules.git import GitModule
    fake = [{"sha": "abc", "message": "fix auth", "files_changed": [], "cochange_pairs": []}]

    with patch("chips.mcp.modules.git._get_recent_commits", return_value=fake) as mock_git:
        module = GitModule(conn_factory=MagicMock())
        result = module.get_recent_commits(limit=5)

    mock_git.assert_called_once()
    assert result == fake


def test_get_recent_commits_passes_limit():
    from chips.mcp.modules.git import GitModule

    with patch("chips.mcp.modules.git._get_recent_commits", return_value=[]) as mock_git:
        module = GitModule(conn_factory=MagicMock())
        module.get_recent_commits(limit=3)

    _, kwargs = mock_git.call_args
    assert kwargs["limit"] == 3


def test_git_module_register_adds_tool_to_app():
    from chips.mcp.modules.git import GitModule
    from mcp.server.fastmcp import FastMCP
    app = FastMCP("test")
    GitModule(conn_factory=MagicMock()).register(app)
    assert "get_recent_commits" in list(app._tool_manager._tools.keys())
