"""RED: MemoryModule tests."""
from unittest.mock import MagicMock, patch


def test_memory_module_name():
    from chips.mcp.modules.memory import MemoryModule
    m = MemoryModule(conn_factory=MagicMock(), embedder=MagicMock())
    assert m.name == "memory"


def test_search_memory_embeds_query():
    from chips.mcp.modules.memory import MemoryModule
    embedder = MagicMock()
    embedder.embed.return_value = [0.1] * 768

    with patch("chips.mcp.modules.memory._search_memory", return_value=[]):
        module = MemoryModule(conn_factory=MagicMock(), embedder=embedder)
        module.search_memory(query="checkout flow", scope=None, limit=5)

    embedder.embed.assert_called_once_with("checkout flow")


def test_search_memory_passes_scope_and_limit():
    from chips.mcp.modules.memory import MemoryModule
    embedder = MagicMock()
    embedder.embed.return_value = [0.2] * 768

    with patch("chips.mcp.modules.memory._search_memory", return_value=[]) as mock_search:
        module = MemoryModule(conn_factory=MagicMock(), embedder=embedder)
        module.search_memory(query="anything", scope="auth", limit=7)

    _, kwargs = mock_search.call_args
    assert kwargs["scope"] == "auth"
    assert kwargs["limit"] == 7


def test_search_memory_returns_results():
    from chips.mcp.modules.memory import MemoryModule
    fake = [{"content": "use repos", "score": 0.9, "type": "lesson", "signal_breakdown": {}}]
    embedder = MagicMock()
    embedder.embed.return_value = [0.1] * 768

    with patch("chips.mcp.modules.memory._search_memory", return_value=fake):
        module = MemoryModule(conn_factory=MagicMock(), embedder=embedder)
        result = module.search_memory(query="q", scope=None, limit=10)

    assert result == fake


def test_memory_module_register_adds_tool_to_app():
    from chips.mcp.modules.memory import MemoryModule
    from mcp.server.fastmcp import FastMCP
    app = FastMCP("test")
    module = MemoryModule(conn_factory=MagicMock(), embedder=MagicMock())
    module.register(app)
    tool_names = list(app._tool_manager._tools.keys())
    assert "search_memory" in tool_names
