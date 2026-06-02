from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID


@dataclass
class RankedSignal:
    item_id: str
    item_type: str
    score: float
    signal_breakdown: dict


@dataclass
class RetrievedItems:
    memories: list[dict] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    traces: list[dict] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    diffs: list[dict] = field(default_factory=list)


@dataclass
class SourceStatus:
    status: Literal["not_configured", "available", "unavailable", "error"]
    detail: str = ""
    checked_at: datetime | None = None


@dataclass(frozen=True)
class SoftContextItem:
    item_id: str
    category: Literal["memory", "diff", "finding", "file", "structural", "generic"]
    text: str
    score: float = 0.0


@dataclass
class ContextBrief:
    brief_id: UUID
    task: str
    scope: str | None
    generated_at: datetime
    latency_ms: int
    task_kind: str
    retrieved: RetrievedItems
    ranked_signals: list[RankedSignal]
    hard_constraints: list[str]
    compressed_context: str
    # tenant_id=None: single-tenant/dev mode only. Production callers must pass a value.
    tenant_id: str | None = None
    data_sources: dict[str, SourceStatus] = field(default_factory=dict)
    schema_version: int = 1
    compression_trace: dict[str, list[str]] = field(default_factory=dict)
    forbidden_edits: list[str] = field(default_factory=list)
    allowed_edits: list[str] = field(default_factory=list)
    governor_decision: dict = field(default_factory=dict)
    # Phase 1 (§B/§I.5): typed, stable-ID projection of this brief's signals. A
    # re-derivable projection — not persisted to cortex_briefs (no §H column).
    evidence_bundle: "EvidenceBundle | None" = None


# ── Phase 1: evidence-ranked hypotheses ──────────────────────────────────────
# Contract: docs/27_05_phase1_evidence_hypotheses_contract.md

EvidenceKind = Literal[
    "constraint", "memory", "diff", "finding", "structural", "workflow", "rule", "span"
]
ConstraintKind = Literal["forbidden", "invariant", "known_issue"]


@dataclass(frozen=True)
class EvidenceItem:
    """A single citable evidence item with a stable, content-derived ID.

    For constraints, ``constraint_kind`` and ``target`` are first-class (never
    render-only): contradiction scoring reads them directly. ``target`` keys:
    {path?, symbol?, workflow_step?, rule_id?}.
    """
    evidence_id: str            # "<kind>:<natural-key>" — stable across compiles
    kind: EvidenceKind
    label: str                  # compact, stable — for logs / UI / write-back review
    text: str                   # full agent-readable content
    weight: float = 0.0         # ranker score; constraints carry authority weight 1.0
    constraint_kind: ConstraintKind | None = None  # set iff kind == "constraint"
    target: dict = field(default_factory=dict)
    refs: dict = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceBundle:
    """Typed, stable-ID projection of a brief's signals.

    Two lists, deliberately: ``constraints`` is the non-negotiable layer that
    contradiction is scored against; ``evidence`` is the citable soft pool.
    """
    bundle_id: UUID                                   # == brief_id
    constraints: list[EvidenceItem] = field(default_factory=list)
    evidence: list[EvidenceItem] = field(default_factory=list)

    def by_id(self, evidence_id: str) -> EvidenceItem | None:
        for item in (*self.constraints, *self.evidence):
            if item.evidence_id == evidence_id:
                return item
        return None

    def constraint_by_id(self, evidence_id: str) -> EvidenceItem | None:
        for item in self.constraints:
            if item.evidence_id == evidence_id:
                return item
        return None


@dataclass(frozen=True)
class Hypothesis:
    """A bug hypothesis emitted by the agent. ``rank_hint`` is advisory only and
    never enters the deterministic score. ``touched_paths``/``touched_symbols``/
    ``declared_violations`` make contradiction scoring deterministic.
    """
    hypothesis_id: str
    claim: str
    mechanism: str
    cited_evidence: list[str] = field(default_factory=list)
    touched_paths: list[str] = field(default_factory=list)
    touched_symbols: list[str] = field(default_factory=list)
    declared_violations: list[str] = field(default_factory=list)  # constraint IDs only
    predicted_checks: list[str] = field(default_factory=list)
    rank_hint: float | None = None


@dataclass(frozen=True)
class ConstraintCandidate:
    """Review-queue payload for a pruned-wrong / rejected hypothesis. NOT an active
    cortex_constraints row until promoted (manually) via cortex_add_constraint.
    """
    claim: str
    mechanism: str
    cited_evidence: list[str]
    source_brief_id: UUID
    source_hypothesis_id: str
    tenant_id: str | None
    scope: str | None
    proposed_kind: ConstraintKind = "known_issue"
    proposed_target: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Constraint:
    """A cortex_constraints row: a durable, scoped policy artifact (Phase 0).

    The dynamic policy layer beside the static PolicyLoader. ``scope_pattern`` is
    '*' (global within tenant) or an exact scope, mirroring PolicyLoader.for_scope.
    """
    id: UUID
    tenant_id: str | None
    scope_pattern: str
    kind: ConstraintKind
    text: str
    reason: str | None = None
    source_kind: str | None = None
    source_ref: str | None = None
    target: dict = field(default_factory=dict)
    status: str = "active"
    created_at: datetime | None = None


@dataclass(frozen=True)
class DecisionLogEntry:
    """A cortex_decision_log row: one policy decision per brief (Foundation).

    Foundation captures context/action/propensity/policy_version/evidence/latency
    with a versioned feature schema. The reward-consuming fields (feedback,
    verifier_outcome, downstream_success, composite_reward) stay None until the
    Activation phase (Phase-3 verifier). Governed by docs/02_06_execution_ledger.md.
    """
    id: UUID
    brief_id: UUID
    feature_schema_version: str
    policy_version: str
    tenant_id: str | None = None
    scope: str | None = None
    context_features: dict = field(default_factory=dict)
    action: dict = field(default_factory=dict)
    propensity: float | None = None
    evidence_used: list = field(default_factory=list)
    latency_ms: int | None = None
    feedback: dict | None = None
    verifier_outcome: dict | None = None
    downstream_success: dict | None = None
    composite_reward: float | None = None
    created_at: datetime | None = None
