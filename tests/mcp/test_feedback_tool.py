from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

from chips.memory.outcome_repository import RecordedOutcome


def test_submit_brief_feedback_exists():
    from chips.mcp import server

    assert hasattr(server, "submit_brief_feedback")


def test_submit_brief_feedback_returns_ack():
    recorded_at = datetime.now(timezone.utc)
    outcome = RecordedOutcome(
        outcome_id=uuid4(),
        brief_id=uuid4(),
        tenant_id="tenant-x",
        outcome="accepted",
        note=None,
        created_at=recorded_at,
        deduplicated=True,
    )

    with (
        patch("chips.mcp.server._get_conn", return_value=MagicMock()),
        patch("chips.mcp.server.BriefOutcomeRepository") as repo_cls,
        patch("chips.mcp.server.BriefLearningService") as learning_cls,
    ):
        repo_cls.return_value.record_with_ack.return_value = outcome
        from chips.mcp.server import submit_brief_feedback

        result = submit_brief_feedback(
            brief_id=str(outcome.brief_id),
            outcome="accepted",
            tenant_id="tenant-x",
            idempotency_key="retry-1",
        )

    assert result["outcome_id"] == str(outcome.outcome_id)
    assert result["deduplicated"] is True
    learning_cls.return_value.maybe_recompute.assert_called_once_with(tenant_id="tenant-x")
