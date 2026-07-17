"""RED: Phase-3 verifier skeleton — deterministic 'unknown' labeler (shadow, no rule yet)."""
from uuid import uuid4

from chips.compiler.decision_log_repository import DecisionLogRepository
from chips.verifier.verifier import Verifier

_UNKNOWN_OUTCOME = {"status": "unknown", "reason": "verifier_skeleton_no_rule"}


def _make_decision(repo: DecisionLogRepository, tenant_id: str | None = None) -> "UUID":
    return repo.record(
        brief_id=uuid4(),
        feature_schema_version="v1",
        policy_version="p1",
        tenant_id=tenant_id,
    )


def test_set_verifier_outcome_writes_jsonb_and_returns_true(conn):
    repo = DecisionLogRepository(conn)
    decision_id = _make_decision(repo)

    updated = repo.set_verifier_outcome(decision_id, _UNKNOWN_OUTCOME)

    assert updated is True
    entry = repo.get(decision_id)
    assert entry is not None
    assert entry.verifier_outcome == _UNKNOWN_OUTCOME


def test_set_verifier_outcome_returns_false_for_unknown_id(conn):
    repo = DecisionLogRepository(conn)

    updated = repo.set_verifier_outcome(uuid4(), _UNKNOWN_OUTCOME)

    assert updated is False


def test_run_once_labels_all_null_rows_unknown(conn):
    # Tenant-scope this test's rows so run_once counts only them — run_once(None)
    # labels EVERY unlabeled row in the shared DB (other tests' committed decision
    # rows accumulate), which is correct behavior but makes a global count assertion
    # non-deterministic across the full suite.
    repo = DecisionLogRepository(conn)
    tid = f"verifier-skel-{uuid4()}"
    d1 = _make_decision(repo, tenant_id=tid)
    d2 = _make_decision(repo, tenant_id=tid)

    verifier = Verifier(conn)
    count = verifier.run_once(tenant_id=tid)

    assert count == 2
    e1 = repo.get(d1, tenant_id=tid)
    e2 = repo.get(d2, tenant_id=tid)
    assert e1.verifier_outcome == _UNKNOWN_OUTCOME
    assert e2.verifier_outcome == _UNKNOWN_OUTCOME


def test_run_once_is_idempotent_on_replay(conn):
    # Tenant-scoped so the counts reflect only this test's rows (see note above).
    repo = DecisionLogRepository(conn)
    tid = f"verifier-replay-{uuid4()}"
    d1 = _make_decision(repo, tenant_id=tid)

    verifier = Verifier(conn)
    first_count = verifier.run_once(tenant_id=tid)
    entry_after_first = repo.get(d1, tenant_id=tid)

    second_count = verifier.run_once(tenant_id=tid)
    entry_after_second = repo.get(d1, tenant_id=tid)

    assert first_count == 1
    assert second_count == 0
    assert entry_after_first.verifier_outcome == entry_after_second.verifier_outcome
    assert entry_after_second.verifier_outcome == _UNKNOWN_OUTCOME


def test_run_once_is_tenant_scoped(conn):
    repo = DecisionLogRepository(conn)
    tenant_a_id = f"tenant-a-{uuid4()}"
    tenant_b_id = f"tenant-b-{uuid4()}"
    d_a = _make_decision(repo, tenant_id=tenant_a_id)
    d_b = _make_decision(repo, tenant_id=tenant_b_id)

    verifier = Verifier(conn)
    count = verifier.run_once(tenant_id=tenant_a_id)

    assert count == 1
    entry_a = repo.get(d_a, tenant_id=tenant_a_id)
    entry_b = repo.get(d_b, tenant_id=tenant_b_id)
    assert entry_a.verifier_outcome == _UNKNOWN_OUTCOME
    assert entry_b.verifier_outcome is None
