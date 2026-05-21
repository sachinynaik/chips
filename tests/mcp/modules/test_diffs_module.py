"""RED: DiffsModule unit tests."""
import pytest
from unittest.mock import MagicMock, patch


def _fake_result(scope="auth"):
    return {"commits": [], "scope": scope, "status": "ok"}


def test_diffs_module_name():
    from chips.mcp.modules.diffs import DiffsModule
    assert DiffsModule(conn_factory=MagicMock()).name == "diffs"


def test_get_diffs_delegates_to_tool_function():
    from chips.mcp.modules.diffs import DiffsModule
    fake = _fake_result()

    with patch("chips.mcp.modules.diffs._get_diffs_for_scope", return_value=fake) as mock_fn:
        result = DiffsModule(conn_factory=MagicMock()).get_diffs(scope="auth", limit=5)

    mock_fn.assert_called_once()
    assert result == fake


def test_get_diffs_passes_scope_and_limit():
    from chips.mcp.modules.diffs import DiffsModule

    with patch("chips.mcp.modules.diffs._get_diffs_for_scope", return_value=_fake_result()) as mock_fn:
        DiffsModule(conn_factory=MagicMock()).get_diffs(scope="auth", limit=7)

    _, kwargs = mock_fn.call_args
    assert kwargs["scope"] == "auth"
    assert kwargs["limit"] == 7


def test_get_diffs_closes_connection_on_success():
    from chips.mcp.modules.diffs import DiffsModule
    conn = MagicMock()

    with patch("chips.mcp.modules.diffs._get_diffs_for_scope", return_value=_fake_result()):
        DiffsModule(conn_factory=MagicMock(return_value=conn)).get_diffs()

    conn.close.assert_called_once()


def test_get_diffs_closes_connection_on_error():
    from chips.mcp.modules.diffs import DiffsModule
    conn = MagicMock()

    with patch("chips.mcp.modules.diffs._get_diffs_for_scope", side_effect=RuntimeError("db error")):
        with pytest.raises(RuntimeError):
            DiffsModule(conn_factory=MagicMock(return_value=conn)).get_diffs()

    conn.close.assert_called_once()


def test_diffs_module_register_adds_tool_to_app():
    from chips.mcp.modules.diffs import DiffsModule
    from mcp.server.fastmcp import FastMCP
    app = FastMCP("test")
    DiffsModule(conn_factory=MagicMock()).register(app)
    assert "get_diffs" in list(app._tool_manager._tools.keys())
