"""Foundation slice 1: cortex_decision_log round-trip + schema-version + tenant scope.

DB-backed (uses the root `conn` fixture + real `apply_migrations`; lives under
tests/db/ rather than tests/unit|compiler which no-op migrations for mock tests).
Foundation scope only: the log captures context/action/propensity/policy_version/
evidence/latency with a versioned feature schema; reward-consuming columns stay
NULL (populated only in the Activation phase, per docs/02_06_execution_ledger.md).
"""
from __future__ import annotations

from uuid import uuid4

from chips.compiler.decision_log_repository import DecisionLogRepository


def test_record_and_get_roundtrip(conn):
    repo = DecisionLogRepository(conn)
    brief_id = uuid4()
    decision_id = repo.record(
        brief_id=brief_id,
        feature_schema_version="v1",
        policy_version="pv:abc123",
        context_features={"task_kind": "bugfix", "evidence_counts": {"con": 2}},
        action={"reranker": False, "source_budget": 4000},
        propensity=1.0,
        evidence_used=["con:1", "find:abc"],
        latency_ms=42,
        scope="repoA",
        tenant_id="t1",
    )

    entry = repo.get(decision_id, tenant_id="t1")
    assert entry is not None
    assert entry.id == decision_id
    assert entry.brief_id == brief_id
    assert entry.scope == "repoA"
    assert entry.feature_schema_version == "v1"
    assert entry.policy_version == "pv:abc123"
    assert entry.context_features["task_kind"] == "bugfix"
    assert entry.context_features["evidence_counts"] == {"con": 2}
    assert entry.action["source_budget"] == 4000
    assert entry.action["reranker"] is False
    assert entry.propensity == 1.0
    assert entry.evidence_used == ["con:1", "find:abc"]
    assert entry.latency_ms == 42
    assert entry.created_at is not None


def test_reward_columns_are_null_in_foundation(conn):
    """Foundation records decisions but never computes reward (ledger gate)."""
    repo = DecisionLogRepository(conn)
    decision_id = repo.record(
        brief_id=uuid4(),
        feature_schema_version="v1",
        policy_version="pv:x",
    )
    entry = repo.get(decision_id)
    assert entry is not None
    assert entry.feedback is None
    assert entry.verifier_outcome is None
    assert entry.downstream_success is None
    assert entry.composite_reward is None


def test_feature_schema_version_is_persisted(conn):
    repo = DecisionLogRepository(conn)
    decision_id = repo.record(
        brief_id=uuid4(),
        feature_schema_version="v2",
        policy_version="pv:x",
    )
    entry = repo.get(decision_id)
    assert entry is not None
    assert entry.feature_schema_version == "v2"


def test_tenant_isolation(conn):
    repo = DecisionLogRepository(conn)
    decision_id = repo.record(
        brief_id=uuid4(),
        feature_schema_version="v1",
        policy_version="pv:x",
        tenant_id="owner",
    )
    # Wrong tenant cannot read the row.
    assert repo.get(decision_id, tenant_id="intruder") is None
    # Owner can.
    assert repo.get(decision_id, tenant_id="owner") is not None
    # Unscoped read (tenant_id=None) is not tenant-filtered.
    assert repo.get(decision_id) is not None


def test_for_brief_returns_recorded_decisions(conn):
    repo = DecisionLogRepository(conn)
    brief_id = uuid4()
    repo.record(brief_id=brief_id, feature_schema_version="v1", policy_version="pv:1", tenant_id="t1")
    repo.record(brief_id=brief_id, feature_schema_version="v1", policy_version="pv:2", tenant_id="t1")
    entries = repo.for_brief(brief_id, tenant_id="t1")
    assert len(entries) == 2
    assert {e.policy_version for e in entries} == {"pv:1", "pv:2"}
