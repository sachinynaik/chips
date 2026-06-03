"""Gate: every brief BriefBuilder.build produces emits exactly one decision row.

This is the bandit-design "log-count = brief-count audit" (step 3) — the test
that makes the cortex_decision_log a *live* foundation rather than a dead schema.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import UUID

import pytest

from chips.compiler.builder import BriefBuilder
from chips.compiler.policy_version import FEATURE_SCHEMA_VERSION, active_policy_version

_TENANT = "aaaaaaaa-0000-0000-0000-000000000001"


def _make_embedder() -> MagicMock:
    embedder = MagicMock()
    embedder.embed.return_value = [0.1] * 768
    return embedder


def _make_compressor() -> MagicMock:
    compressor = MagicMock()
    compressor.compress.return_value = "compressed"
    compressor.compress_with_trace.return_value = ("compressed", [])
    return compressor


def _decision_rows(conn, brief_id) -> list[tuple]:
    return conn.execute(
        "SELECT id, feature_schema_version, propensity, policy_version, "
        "context_features, action, latency_ms, composite_reward, feedback, "
        "verifier_outcome, downstream_success "
        "FROM cortex_decision_log WHERE brief_id = %s",
        (str(brief_id),),
    ).fetchall()


def test_build_logs_exactly_one_decision_per_brief(conn):
    brief = BriefBuilder(conn, _make_embedder(), _make_compressor()).build_and_log(
        "fix the login crash", scope="auth", tenant_id=_TENANT
    )
    rows = _decision_rows(conn, brief.brief_id)
    assert len(rows) == 1


def test_two_builds_log_two_decisions(conn):
    builder = BriefBuilder(conn, _make_embedder(), _make_compressor())
    b1 = builder.build_and_log("task one", tenant_id=_TENANT)
    b2 = builder.build_and_log("task two", tenant_id=_TENANT)
    assert len(_decision_rows(conn, b1.brief_id)) == 1
    assert len(_decision_rows(conn, b2.brief_id)) == 1


def test_logged_decision_uses_content_hash_policy_version(conn):
    brief = BriefBuilder(conn, _make_embedder(), _make_compressor()).build_and_log(
        "fix crash", tenant_id=_TENANT
    )
    row = _decision_rows(conn, brief.brief_id)[0]
    assert row[3] == active_policy_version()
    assert str(row[3]).startswith("pv-")  # content hash, not free text


def test_logged_decision_is_deterministic_foundation_shape(conn):
    brief = BriefBuilder(conn, _make_embedder(), _make_compressor()).build_and_log(
        "fix crash", tenant_id=_TENANT
    )
    row = _decision_rows(conn, brief.brief_id)[0]
    assert row[1] == FEATURE_SCHEMA_VERSION
    assert row[2] == 1.0  # propensity (deterministic policy)
    assert row[4]  # context_features populated
    assert row[6] == brief.latency_ms
    # Reward columns stay NULL in Foundation (gated on Phase-3 verifier).
    assert row[7] is None  # composite_reward
    assert row[8] is None  # feedback
    assert row[9] is None  # verifier_outcome
    assert row[10] is None  # downstream_success


def test_decision_is_tenant_scoped_to_the_brief(conn):
    brief = BriefBuilder(conn, _make_embedder(), _make_compressor()).build_and_log(
        "fix crash", tenant_id=_TENANT
    )
    row = conn.execute(
        "SELECT tenant_id FROM cortex_decision_log WHERE brief_id = %s",
        (str(brief.brief_id),),
    ).fetchone()
    assert str(row[0]) == _TENANT
