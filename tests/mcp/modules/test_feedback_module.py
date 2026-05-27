from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4


def _make_module():
    from chips.mcp.modules.feedback import FeedbackModule

    return FeedbackModule(conn_factory=MagicMock())


def test_feedback_module_name():
    assert _make_module().name == "feedback"


def test_submit_brief_feedback_returns_ack_payload():
    from chips.memory.outcome_repository import RecordedOutcome

    recorded_at = datetime.now(timezone.utc)
    outcome = RecordedOutcome(
        outcome_id=uuid4(),
        brief_id=uuid4(),
        tenant_id="tenant-x",
        outcome="accepted",
        note="helpful",
        created_at=recorded_at,
        deduplicated=False,
    )

    with (
        patch("chips.mcp.modules.feedback.BriefOutcomeRepository") as repo_cls,
        patch("chips.mcp.modules.feedback.BriefLearningService") as learning_cls,
    ):
        repo_cls.return_value.record_with_ack.return_value = outcome
        result = _make_module().submit_brief_feedback(
            brief_id=str(outcome.brief_id),
            outcome="accepted",
            tenant_id="tenant-x",
        )

    assert result["outcome_id"] == str(outcome.outcome_id)
    assert result["brief_id"] == str(outcome.brief_id)
    assert result["tenant_id"] == "tenant-x"
    assert result["outcome"] == "accepted"
    learning_cls.return_value.maybe_recompute.assert_called_once_with(tenant_id="tenant-x")


def test_feedback_module_registers_tool():
    from mcp.server.fastmcp import FastMCP

    app = FastMCP("test")
    _make_module().register(app)
    assert "submit_brief_feedback" in app._tool_manager._tools
