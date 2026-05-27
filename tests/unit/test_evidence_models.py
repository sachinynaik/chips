"""Phase 1: EvidenceBundle / EvidenceItem / Hypothesis / ConstraintCandidate models.

Locks docs/27_05_phase1_evidence_hypotheses_contract.md §B/§C/§F: two-list bundle
(constraints vs evidence), constraint_kind + target as first-class fields, and the
review-queue candidate payload shape.
"""
from __future__ import annotations

from uuid import uuid4

from chips.compiler.models import (
    ConstraintCandidate,
    EvidenceBundle,
    EvidenceItem,
    Hypothesis,
)


def _con(eid: str, kind: str, **target) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=eid,
        kind="constraint",
        label=eid,
        text=f"constraint {eid}",
        weight=1.0,
        constraint_kind=kind,  # type: ignore[arg-type]
        target=target,
    )


def _ev(eid: str, kind: str, weight: float) -> EvidenceItem:
    return EvidenceItem(evidence_id=eid, kind=kind, label=eid, text=f"ev {eid}", weight=weight)  # type: ignore[arg-type]


def _bundle() -> EvidenceBundle:
    return EvidenceBundle(
        bundle_id=uuid4(),
        constraints=[_con("con:1", "forbidden", path="pay.py")],
        evidence=[_ev("mem:1", "memory", 2.0)],
    )


def test_by_id_finds_item_in_either_list():
    b = _bundle()
    assert b.by_id("con:1").constraint_kind == "forbidden"
    assert b.by_id("mem:1").kind == "memory"


def test_by_id_returns_none_for_absent_id():
    assert _bundle().by_id("ghost:1") is None


def test_constraint_by_id_only_matches_constraints():
    b = _bundle()
    assert b.constraint_by_id("con:1") is not None
    # an evidence-list id is NOT a constraint
    assert b.constraint_by_id("mem:1") is None
    assert b.constraint_by_id("ghost:1") is None


def test_constraint_kind_and_target_are_first_class_fields():
    item = _con("con:9", "invariant", symbol="Cart.add")
    assert item.constraint_kind == "invariant"
    assert item.target == {"symbol": "Cart.add"}


def test_evidence_item_defaults_are_independent_instances():
    a = _ev("mem:1", "memory", 1.0)
    b = _ev("mem:2", "memory", 1.0)
    assert a.target == {} and a.refs == {}
    assert a.target is not b.target  # default_factory, not shared mutable


def test_hypothesis_optional_fields_default_empty():
    h = Hypothesis(hypothesis_id="h1", claim="c", mechanism="m", cited_evidence=["mem:1"])
    assert h.touched_paths == []
    assert h.touched_symbols == []
    assert h.declared_violations == []
    assert h.rank_hint is None


def test_constraint_candidate_carries_review_payload():
    bid = uuid4()
    c = ConstraintCandidate(
        claim="don't bypass lock",
        mechanism="race on inventory decrement",
        cited_evidence=["wf:abc", "find:deadbeef0000"],
        source_brief_id=bid,
        source_hypothesis_id="h2",
        tenant_id="t1",
        scope="checkout",
        proposed_target={"path": "pay.py"},
    )
    assert c.proposed_kind == "known_issue"  # default
    assert c.source_brief_id == bid
    assert c.proposed_target == {"path": "pay.py"}
