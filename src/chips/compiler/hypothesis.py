"""Phase 1: deterministic hypothesis ranking + structural contradiction.

Contract: docs/27_05_phase1_evidence_hypotheses_contract.md §D/§E.

Pure functions only — no DB, no LLM, no I/O. CHIPS scores hypotheses; the agent's
``rank_hint`` is advisory and never enters the score.

    score(h) = w_cov·coverage − w_con·contradiction + w_div·corroboration + w_prox·proximity

  - coverage dedups on the SET of unique valid cited evidence IDs
  - corroboration uses the SET of unique cited kinds
  - contradiction is STRUCTURAL and counts only forbidden/invariant constraints
    (known_issue is guidance, not a hard contradiction)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from chips.compiler.models import EvidenceBundle, EvidenceItem, Hypothesis

_HARD_KINDS = frozenset({"forbidden", "invariant"})

# Closed set so the MCP surface can switch on it reliably.
ViolationKind = Literal["unknown_evidence_id", "declared_violation_not_constraint"]


@dataclass(frozen=True)
class RankingWeights:
    w_cov: float = 1.0
    w_con: float = 2.0   # > w_cov: violating an invariant is worse than being well-cited
    w_div: float = 0.25
    w_prox: float = 0.0  # failing-path proximity arrives in Phase 2


@dataclass(frozen=True)
class ContractViolation:
    hypothesis_id: str
    kind: ViolationKind
    detail: str          # the offending evidence/constraint ID


@dataclass(frozen=True)
class ScoredHypothesis:
    hypothesis_id: str
    score: float
    coverage: float
    contradiction: int
    corroboration: int
    proximity: float
    unique_kinds: int
    violations: list[ContractViolation] = field(default_factory=list)


def _unique_valid_items(hypothesis: Hypothesis, bundle: EvidenceBundle) -> list[EvidenceItem]:
    """Bundle items for the hypothesis's cited IDs, deduplicated by ID, order-stable."""
    seen: dict[str, EvidenceItem] = {}
    for eid in hypothesis.cited_evidence:
        if eid in seen:
            continue
        item = bundle.by_id(eid)
        if item is not None:
            seen[eid] = item
    return list(seen.values())


def coverage(hypothesis: Hypothesis, bundle: EvidenceBundle) -> float:
    """Sum of weights over unique, valid cited evidence."""
    return sum(item.weight for item in _unique_valid_items(hypothesis, bundle))


def corroboration(hypothesis: Hypothesis, bundle: EvidenceBundle) -> int:
    """Distinct evidence kinds cited, minus one, floored at zero."""
    kinds = {item.kind for item in _unique_valid_items(hypothesis, bundle)}
    return max(0, len(kinds) - 1)


def contradiction(hypothesis: Hypothesis, bundle: EvidenceBundle) -> int:
    """Count distinct forbidden/invariant constraints structurally contradicted.

    A constraint is contradicted iff the hypothesis declares it as a violation, or
    its target path/symbol overlaps the hypothesis's touched paths/symbols.
    """
    touched_paths = set(hypothesis.touched_paths)
    touched_symbols = set(hypothesis.touched_symbols)
    declared = set(hypothesis.declared_violations)

    count = 0
    for c in bundle.constraints:
        if c.constraint_kind not in _HARD_KINDS:
            continue
        path = c.target.get("path")
        symbol = c.target.get("symbol")
        if (
            c.evidence_id in declared
            or (symbol and symbol in touched_symbols)
            or (path and path in touched_paths)
        ):
            count += 1
    return count


def validate_hypothesis(
    hypothesis: Hypothesis, bundle: EvidenceBundle
) -> list[ContractViolation]:
    """Surface (never silently drop) contract violations.

    - cited evidence IDs absent from the bundle
    - declared_violations that are not constraint IDs in the bundle
    """
    violations: list[ContractViolation] = []
    for eid in dict.fromkeys(hypothesis.cited_evidence):  # unique, order-stable
        if bundle.by_id(eid) is None:
            violations.append(
                ContractViolation(hypothesis.hypothesis_id, "unknown_evidence_id", eid)
            )
    for eid in dict.fromkeys(hypothesis.declared_violations):
        if bundle.constraint_by_id(eid) is None:
            violations.append(
                ContractViolation(
                    hypothesis.hypothesis_id, "declared_violation_not_constraint", eid
                )
            )
    return violations


def score_hypothesis(
    hypothesis: Hypothesis,
    bundle: EvidenceBundle,
    weights: RankingWeights | None = None,
) -> ScoredHypothesis:
    w = weights or RankingWeights()
    items = _unique_valid_items(hypothesis, bundle)
    cov = sum(item.weight for item in items)
    n_kinds = len({item.kind for item in items})
    corro = max(0, n_kinds - 1)
    con = contradiction(hypothesis, bundle)
    prox = 0.0  # Phase 2
    score = w.w_cov * cov - w.w_con * con + w.w_div * corro + w.w_prox * prox
    return ScoredHypothesis(
        hypothesis_id=hypothesis.hypothesis_id,
        score=score,
        coverage=cov,
        contradiction=con,
        corroboration=corro,
        proximity=prox,
        unique_kinds=n_kinds,
        violations=validate_hypothesis(hypothesis, bundle),
    )


def rank_hypotheses(
    hypotheses: list[Hypothesis],
    bundle: EvidenceBundle,
    weights: RankingWeights | None = None,
) -> list[ScoredHypothesis]:
    """Rank by score desc, then deterministic tie-breaks: coverage desc,
    contradiction asc, unique-kinds desc, hypothesis_id lexicographic.
    """
    scored = [score_hypothesis(h, bundle, weights) for h in hypotheses]
    scored.sort(
        key=lambda s: (-s.score, -s.coverage, s.contradiction, -s.unique_kinds, s.hypothesis_id)
    )
    return scored
