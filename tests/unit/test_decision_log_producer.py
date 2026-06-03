from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from chips.compiler.decision_log_producer import build_decision_fields
from chips.compiler.models import ContextBrief, RankedSignal, RetrievedItems, SourceStatus
from chips.compiler.policy_version import FEATURE_SCHEMA_VERSION, active_policy_version


def _brief() -> ContextBrief:
    return ContextBrief(
        brief_id=uuid4(),
        task="fix the login crash",
        scope="auth",
        generated_at=datetime.now(timezone.utc),
        latency_ms=42,
        task_kind="bugfix",
        retrieved=RetrievedItems(memories=[{"id": "m1"}, {"id": "m2"}], diffs=[]),
        ranked_signals=[
            RankedSignal(item_id="m1", item_type="memory", score=0.9, signal_breakdown={}),
            RankedSignal(item_id="m2", item_type="memory", score=0.5, signal_breakdown={}),
        ],
        hard_constraints=[],
        compressed_context="ctx",
        tenant_id="aaaaaaaa-0000-0000-0000-000000000001",
        data_sources={"file_signals": SourceStatus(status="available")},
        governor_decision={
            "triggered": False,
            "mean_confidence": 0.3,
            "item_count": 2,
            "skipped_sources": [],
            "reason": "",
        },
    )


def test_fields_carry_identity_and_deterministic_policy():
    brief = _brief()
    fields = build_decision_fields(brief, files=None)

    assert fields["brief_id"] == brief.brief_id
    assert fields["scope"] == "auth"
    assert fields["tenant_id"] == brief.tenant_id
    assert fields["latency_ms"] == 42
    assert fields["propensity"] == 1.0
    assert fields["policy_version"] == active_policy_version()
    assert fields["feature_schema_version"] == FEATURE_SCHEMA_VERSION


def test_context_features_describe_the_decision_context():
    fields = build_decision_fields(_brief(), files=["a.py"])
    ctx = fields["context_features"]
    assert ctx["task_kind"] == "bugfix"
    assert ctx["scope"] == "auth"
    assert ctx["has_files"] is True
    assert ctx["memory_count"] == 2


def test_action_describes_what_the_policy_did():
    fields = build_decision_fields(_brief(), files=None)
    action = fields["action"]
    assert action["governor_triggered"] is False
    assert action["ranked_count"] == 2
    assert action["file_signals_status"] == "available"


def test_evidence_used_lists_ranked_signal_ids():
    fields = build_decision_fields(_brief(), files=None)
    assert fields["evidence_used"] == ["m1", "m2"]


def test_build_and_log_builds_then_records_once():
    from unittest.mock import MagicMock, patch

    from chips.compiler.builder import BriefBuilder

    builder = BriefBuilder(MagicMock(), MagicMock(), MagicMock())
    fake = _brief()
    with (
        patch.object(BriefBuilder, "build", return_value=fake) as m_build,
        patch("chips.compiler.builder.record_brief_decision") as m_record,
    ):
        out = builder.build_and_log("t", scope="auth", files=["f.py"], tenant_id="x")

    m_build.assert_called_once_with("t", scope="auth", files=["f.py"], tenant_id="x")
    m_record.assert_called_once_with(builder._conn, fake, files=["f.py"])
    assert out is fake
