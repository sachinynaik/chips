from __future__ import annotations

from unittest.mock import MagicMock, patch

from chips.compiler.models import ContextBrief, RetrievedItems


def _fake_brief(task: str) -> ContextBrief:
    import uuid
    from datetime import datetime, timezone
    return ContextBrief(
        brief_id=uuid.uuid4(),
        task=task,
        scope=None,
        generated_at=datetime.now(timezone.utc),
        latency_ms=42,
        task_kind="bugfix",
        retrieved=RetrievedItems(),
        ranked_signals=[],
        hard_constraints=[],
        compressed_context="context summary",
    )


def test_get_context_brief_tool_exists():
    from chips.mcp import server
    assert hasattr(server, "get_context_brief")


def test_get_context_brief_returns_dict_with_expected_keys():
    brief = _fake_brief("fix crash")

    with (
        patch("chips.mcp.server._get_embedder", return_value=MagicMock()),
        patch("chips.mcp.server._get_conn", return_value=MagicMock()),
        patch("chips.mcp.server.BriefBuilder") as mock_cls,
    ):
        mock_cls.return_value.build.return_value = brief
        from chips.mcp.server import get_context_brief
        result = get_context_brief(task="fix crash")

    assert result["task"] == "fix crash"
    assert result["task_kind"] == "bugfix"
    assert result["compressed_context"] == "context summary"
    assert "brief_id" in result
    assert "latency_ms" in result


def test_get_context_brief_passes_scope_to_builder():
    brief = _fake_brief("add feature")

    with (
        patch("chips.mcp.server._get_embedder", return_value=MagicMock()),
        patch("chips.mcp.server._get_conn", return_value=MagicMock()),
        patch("chips.mcp.server.BriefBuilder") as mock_cls,
    ):
        mock_cls.return_value.build.return_value = brief
        from chips.mcp.server import get_context_brief
        get_context_brief(task="add feature", scope="payments")

    mock_cls.return_value.build.assert_called_once_with("add feature", scope="payments")
