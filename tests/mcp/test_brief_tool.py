from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from chips.compiler.models import ContextBrief, RetrievedItems, SourceStatus


_TENANT = "aaaaaaaa-0000-0000-0000-000000000001"


def _fake_brief(task: str, tenant_id: str | None = None) -> ContextBrief:
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
        tenant_id=tenant_id,
        data_sources={
            "runtime": SourceStatus(status="not_configured"),
            "workflow": SourceStatus(status="not_configured"),
            "file_signals": SourceStatus(
                status="not_configured", detail="no files provided to build()"
            ),
        },
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
        mock_cls.return_value.build_and_log.return_value = brief
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
        mock_cls.return_value.build_and_log.return_value = brief
        from chips.mcp.server import get_context_brief
        get_context_brief(task="add feature", scope="payments")

    mock_cls.return_value.build_and_log.assert_called_once_with(
        "add feature", scope="payments", files=None, tenant_id=None
    )


# ── Tenant isolation at the server entrypoint ─────────────────────────────────

def test_get_context_brief_threads_tenant_id_to_builder():
    brief = _fake_brief("fix crash", tenant_id=_TENANT)

    with (
        patch("chips.mcp.server._get_embedder", return_value=MagicMock()),
        patch("chips.mcp.server._get_conn", return_value=MagicMock()),
        patch("chips.mcp.server.BriefBuilder") as mock_cls,
    ):
        mock_cls.return_value.build_and_log.return_value = brief
        from chips.mcp.server import get_context_brief
        result = get_context_brief(task="fix crash", tenant_id=_TENANT)

    mock_cls.return_value.build_and_log.assert_called_once_with(
        "fix crash", scope=None, files=None, tenant_id=_TENANT
    )
    assert result["tenant_id"] == _TENANT


def test_get_context_brief_raises_when_require_tenant_set_and_none_passed(monkeypatch):
    """ValueError must propagate through the server function — not be swallowed."""
    monkeypatch.setenv("CHIPS_REQUIRE_TENANT_ID", "1")

    with (
        patch("chips.mcp.server._get_embedder", return_value=MagicMock()),
        patch("chips.mcp.server._get_conn", return_value=MagicMock()),
        patch("chips.mcp.server._get_compressor", return_value=MagicMock()),
        patch("chips.mcp.server._get_policy_loader", return_value=MagicMock()),
    ):
        from chips.mcp.server import get_context_brief
        with pytest.raises(ValueError, match="CHIPS_REQUIRE_TENANT_ID"):
            get_context_brief(task="fix crash")


def test_get_context_brief_error_message_is_explicit(monkeypatch):
    """The ValueError message must name the missing param and the env var."""
    monkeypatch.setenv("CHIPS_REQUIRE_TENANT_ID", "1")

    with (
        patch("chips.mcp.server._get_embedder", return_value=MagicMock()),
        patch("chips.mcp.server._get_conn", return_value=MagicMock()),
        patch("chips.mcp.server._get_compressor", return_value=MagicMock()),
        patch("chips.mcp.server._get_policy_loader", return_value=MagicMock()),
    ):
        from chips.mcp.server import get_context_brief
        with pytest.raises(ValueError) as exc_info:
            get_context_brief(task="fix crash")

    msg = str(exc_info.value)
    assert "tenant_id" in msg
    assert "CHIPS_REQUIRE_TENANT_ID" in msg


# ── data_sources wire contract snapshot ──────────────────────────────────────

def test_get_context_brief_data_sources_shape_matches_contract():
    """Each source must serialize as exactly {status: str, detail: str} — no extra keys."""
    brief = _fake_brief("fix crash")

    with (
        patch("chips.mcp.server._get_embedder", return_value=MagicMock()),
        patch("chips.mcp.server._get_conn", return_value=MagicMock()),
        patch("chips.mcp.server.BriefBuilder") as mock_cls,
    ):
        mock_cls.return_value.build_and_log.return_value = brief
        from chips.mcp.server import get_context_brief
        result = get_context_brief(task="fix crash")

    assert "data_sources" in result
    for key, source in result["data_sources"].items():
        assert set(source.keys()) == {"status", "detail", "checked_at"}, (
            f"data_sources[{key!r}] has unexpected keys: {set(source.keys())}"
        )
        assert isinstance(source["status"], str)
        assert isinstance(source["detail"], str)


def test_get_context_brief_data_sources_known_keys_present():
    """The three standard source keys must always be present in the response."""
    brief = _fake_brief("fix crash")

    with (
        patch("chips.mcp.server._get_embedder", return_value=MagicMock()),
        patch("chips.mcp.server._get_conn", return_value=MagicMock()),
        patch("chips.mcp.server.BriefBuilder") as mock_cls,
    ):
        mock_cls.return_value.build_and_log.return_value = brief
        from chips.mcp.server import get_context_brief
        result = get_context_brief(task="fix crash")

    assert "runtime" in result["data_sources"]
    assert "workflow" in result["data_sources"]
    assert "file_signals" in result["data_sources"]


def test_get_context_brief_data_sources_status_vocabulary():
    """status values must come from the defined vocabulary."""
    valid_statuses = {"not_configured", "available", "unavailable", "error"}
    brief = _fake_brief("fix crash")

    with (
        patch("chips.mcp.server._get_embedder", return_value=MagicMock()),
        patch("chips.mcp.server._get_conn", return_value=MagicMock()),
        patch("chips.mcp.server.BriefBuilder") as mock_cls,
    ):
        mock_cls.return_value.build_and_log.return_value = brief
        from chips.mcp.server import get_context_brief
        result = get_context_brief(task="fix crash")

    for key, source in result["data_sources"].items():
        assert source["status"] in valid_statuses, (
            f"data_sources[{key!r}].status={source['status']!r} not in vocabulary"
        )
