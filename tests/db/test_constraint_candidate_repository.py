from __future__ import annotations

from uuid import UUID, uuid4

from chips.compiler.constraint_candidate_repository import ConstraintCandidateRepository
from chips.compiler.models import ConstraintCandidate


def _candidate(
    *,
    brief_id: str | None = None,
    hypothesis_id: str = "h1",
    tenant_id: str = "t1",
) -> ConstraintCandidate:
    return ConstraintCandidate(
        claim="avoid bypassing lock",
        mechanism="race on checkout path",
        cited_evidence=["mem:1", "find:abc"],
        source_brief_id=UUID(brief_id) if brief_id else uuid4(),
        source_hypothesis_id=hypothesis_id,
        tenant_id=tenant_id,
        scope="checkout",
        proposed_kind="known_issue",
        proposed_target={"path": "src/pay.py", "symbol": "checkout.pay"},
    )


def test_enqueue_and_list_pending_roundtrip(conn):
    repo = ConstraintCandidateRepository(conn)
    candidate = _candidate()

    candidate_id = repo.enqueue(candidate)
    rows = repo.list(tenant_id="t1")

    assert len(rows) == 1
    row = rows[0]
    assert row.id == candidate_id
    assert row.status == "pending"
    assert row.claim == candidate.claim
    assert row.proposed_target == candidate.proposed_target
    assert row.reviewed_at is None


def test_enqueue_is_idempotent_per_brief_and_hypothesis(conn):
    repo = ConstraintCandidateRepository(conn)
    brief_id = str(uuid4())
    tenant_id = f"tenant-{uuid4()}"
    first = repo.enqueue(_candidate(brief_id=brief_id, hypothesis_id="h1", tenant_id=tenant_id))
    second = repo.enqueue(_candidate(brief_id=brief_id, hypothesis_id="h1", tenant_id=tenant_id))

    assert first == second
    rows = repo.list(tenant_id=tenant_id)
    assert len(rows) == 1
    assert rows[0].source_brief_id == UUID(brief_id)


def test_review_marks_candidate_promoted(conn):
    repo = ConstraintCandidateRepository(conn)
    candidate_id = repo.enqueue(_candidate())
    promoted_constraint_id = uuid4()

    updated = repo.review(
        candidate_id,
        resolution="promoted",
        promoted_constraint_id=promoted_constraint_id,
        tenant_id="t1",
    )

    assert updated is True
    row = repo.list(status="promoted", tenant_id="t1")[0]
    assert row.id == candidate_id
    assert row.status == "promoted"
    assert row.promoted_constraint_id == promoted_constraint_id
    assert row.reviewed_at is not None


def test_tenant_isolation_applies_to_list_and_review(conn):
    repo = ConstraintCandidateRepository(conn)
    candidate_id = repo.enqueue(_candidate())

    assert repo.list(tenant_id="other") == []
    assert repo.review(candidate_id, resolution="dismissed", tenant_id="other") is False
    assert repo.review(candidate_id, resolution="dismissed", tenant_id="t1") is True
