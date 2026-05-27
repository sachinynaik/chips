"""Phase 1: deterministic hypothesis ranking + structural contradiction.

Locks docs/27_05_phase1_evidence_hypotheses_contract.md §D/§E:
  score(h) = w_cov·coverage − w_con·contradiction + w_div·corroboration + w_prox·proximity
  - coverage dedups on UNIQUE valid cited evidence IDs
  - corroboration uses UNIQUE cited kinds
  - contradiction is STRUCTURAL (touched paths/symbols/declared vs constraint targets),
    counts only forbidden/invariant (known_issue is NOT a hard contradiction)
  - rank_hint is advisory and never enters the score
  - tie-breaks: coverage desc, contradiction asc, unique-kinds desc, id lexicographic
"""
from __future__ import annotations

from uuid import uuid4

import pytest

from chips.compiler.hypothesis import (
    ContractViolation,
    RankingWeights,
    contradiction,
    corroboration,
    coverage,
    rank_hypotheses,
    score_hypothesis,
    validate_hypothesis,
)
from chips.compiler.models import EvidenceBundle, EvidenceItem, Hypothesis


def _con(eid: str, kind: str, **target) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=eid, kind="constraint", label=eid, text=eid, weight=1.0,
        constraint_kind=kind, target=target,  # type: ignore[arg-type]
    )


def _ev(eid: str, kind: str, weight: float) -> EvidenceItem:
    return EvidenceItem(evidence_id=eid, kind=kind, label=eid, text=eid, weight=weight)  # type: ignore[arg-type]


@pytest.fixture
def bundle() -> EvidenceBundle:
    return EvidenceBundle(
        bundle_id=uuid4(),
        constraints=[
            _con("con:1", "forbidden", path="pay.py"),
            _con("con:2", "invariant", symbol="Cart.add"),
            _con("con:3", "known_issue", path="pay.py"),
        ],
        evidence=[
            _ev("mem:1", "memory", 2.0),
            _ev("mem:2", "memory", 1.0),
            _ev("diff:abc", "diff", 3.0),
            _ev("find:xyz", "finding", 4.0),
        ],
    )


def _h(hid="h1", cited=(), **kw) -> Hypothesis:
    return Hypothesis(hypothesis_id=hid, claim="c", mechanism="m", cited_evidence=list(cited), **kw)


# ── coverage ───────────────────────────────────────────────────────────────

def test_coverage_sums_unique_valid_cited_weights(bundle):
    assert coverage(_h(cited=["mem:1", "diff:abc"]), bundle) == 5.0


def test_coverage_counts_duplicate_citation_once(bundle):
    # mem:1 cited twice must not double-count (anti-gaming)
    assert coverage(_h(cited=["mem:1", "mem:1", "diff:abc"]), bundle) == 5.0


def test_coverage_excludes_unknown_cited_ids(bundle):
    assert coverage(_h(cited=["mem:1", "ghost:1"]), bundle) == 2.0


# ── corroboration ────────────────────────────────────────────────────────────

def test_corroboration_is_unique_kinds_minus_one(bundle):
    # memory + diff + finding = 3 distinct kinds → 2
    assert corroboration(_h(cited=["mem:1", "diff:abc", "find:xyz"]), bundle) == 2


def test_corroboration_dedups_kinds(bundle):
    # two memory items → 1 distinct kind → 0
    assert corroboration(_h(cited=["mem:1", "mem:2"]), bundle) == 0


def test_corroboration_floored_at_zero_for_no_valid_evidence(bundle):
    assert corroboration(_h(cited=["ghost:1"]), bundle) == 0


# ── contradiction (structural) ───────────────────────────────────────────────

def test_contradiction_matches_forbidden_target_path(bundle):
    assert contradiction(_h(touched_paths=["pay.py"]), bundle) == 1  # con:1 only (con:3 is known_issue)


def test_contradiction_matches_invariant_target_symbol(bundle):
    assert contradiction(_h(touched_symbols=["Cart.add"]), bundle) == 1  # con:2


def test_contradiction_matches_declared_violation(bundle):
    assert contradiction(_h(declared_violations=["con:1"]), bundle) == 1


def test_contradiction_ignores_known_issue(bundle):
    # con:3 is known_issue on pay.py — touching pay.py must NOT count it
    assert contradiction(_h(touched_paths=["pay.py"]), bundle) == 1


def test_contradiction_counts_distinct_constraints_once(bundle):
    # both touched_paths AND declared_violations point at con:1 → counted once;
    # plus con:2 via symbol → total 2 distinct
    h = _h(touched_paths=["pay.py"], declared_violations=["con:1"], touched_symbols=["Cart.add"])
    assert contradiction(h, bundle) == 2


def test_contradiction_zero_when_nothing_matches(bundle):
    assert contradiction(_h(touched_paths=["other.py"]), bundle) == 0


# ── contract validation ──────────────────────────────────────────────────────

def test_validate_flags_unknown_cited_id(bundle):
    violations = validate_hypothesis(_h(cited=["mem:1", "ghost:1"]), bundle)
    assert any(v.kind == "unknown_evidence_id" and "ghost:1" in v.detail for v in violations)


def test_validate_flags_declared_violation_that_is_not_a_constraint(bundle):
    # mem:1 exists but is evidence, not a constraint
    violations = validate_hypothesis(_h(declared_violations=["mem:1"]), bundle)
    assert any(v.kind == "declared_violation_not_constraint" for v in violations)


def test_validate_flags_declared_violation_absent_from_bundle(bundle):
    violations = validate_hypothesis(_h(declared_violations=["con:999"]), bundle)
    assert any(v.kind == "declared_violation_not_constraint" for v in violations)


def test_validate_clean_hypothesis_has_no_violations(bundle):
    assert validate_hypothesis(_h(cited=["mem:1"], declared_violations=["con:1"]), bundle) == []


# ── score ────────────────────────────────────────────────────────────────────

def test_score_uses_default_weights(bundle):
    # cited mem:1(2)+diff:abc(3)+find:xyz(4)=9 cov; kinds 3 → corro 2; touch pay.py → con 1
    h = _h(cited=["mem:1", "diff:abc", "find:xyz"], touched_paths=["pay.py"])
    s = score_hypothesis(h, bundle)
    assert s.coverage == 9.0
    assert s.contradiction == 1
    assert s.corroboration == 2
    assert s.proximity == 0.0
    # 1.0*9 - 2.0*1 + 0.25*2 + 0 = 7.5
    assert s.score == pytest.approx(7.5)


def test_score_honors_custom_weights(bundle):
    h = _h(cited=["mem:1"], touched_paths=["pay.py"])
    s = score_hypothesis(h, bundle, RankingWeights(w_cov=1.0, w_con=10.0, w_div=0.0, w_prox=0.0))
    # 1*2 - 10*1 = -8
    assert s.score == pytest.approx(-8.0)


def test_score_attaches_contract_violations(bundle):
    s = score_hypothesis(_h(cited=["ghost:1"]), bundle)
    assert any(isinstance(v, ContractViolation) for v in s.violations)


# ── ranking + tie-breaks ─────────────────────────────────────────────────────

def test_rank_orders_by_score_descending(bundle):
    hi = _h("hi", cited=["mem:1", "mem:2", "diff:abc", "find:xyz"])  # cov 10, corro 2 → 10.5
    lo = _h("lo", cited=["mem:1"])  # cov 2 → 2.0
    ranked = rank_hypotheses([lo, hi], bundle)
    assert [r.hypothesis_id for r in ranked] == ["hi", "lo"]


def test_rank_tiebreak_prefers_higher_coverage_on_equal_score(bundle):
    # ha: cov 2, con 0 → 2.0 ; hc: cov 4, con 1 → 4 - 2 = 2.0 (equal score, higher coverage)
    ha = _h("ha", cited=["mem:1"])
    hc = _h("hc", cited=["find:xyz"], touched_paths=["pay.py"])
    ranked = rank_hypotheses([ha, hc], bundle)
    assert [r.hypothesis_id for r in ranked] == ["hc", "ha"]


def test_rank_tiebreak_is_lexicographic_id_when_fully_tied(bundle):
    h2 = _h("h2", cited=["mem:1"])
    h1 = _h("h1", cited=["mem:1"])
    ranked = rank_hypotheses([h2, h1], bundle)
    assert [r.hypothesis_id for r in ranked] == ["h1", "h2"]


def test_rank_hint_is_advisory_and_never_scored(bundle):
    persuasive = _h("persuasive", cited=["mem:1"], rank_hint=0.99)  # cov 2 → 2.0
    grounded = _h("grounded", cited=["find:xyz"], rank_hint=0.01)  # cov 4 → 4.0
    ranked = rank_hypotheses([persuasive, grounded], bundle)
    assert [r.hypothesis_id for r in ranked] == ["grounded", "persuasive"]
