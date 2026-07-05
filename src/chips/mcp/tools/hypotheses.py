from __future__ import annotations

from uuid import UUID

import psycopg

from chips.compiler.constraint_candidate_repository import ConstraintCandidateRepository
from chips.compiler.hypothesis import rank_hypotheses
from chips.compiler.models import ConstraintCandidate, EvidenceBundle, EvidenceItem, Hypothesis


def _evidence_item_from_wire(payload: dict) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=payload["evidence_id"],
        kind=payload["kind"],
        label=payload["label"],
        text=payload["text"],
        weight=payload.get("weight", 0.0),
        constraint_kind=payload.get("constraint_kind"),
        target=payload.get("target") or {},
        refs=payload.get("refs") or {},
    )


def _evidence_bundle_from_wire(payload: dict) -> EvidenceBundle:
    from uuid import UUID

    return EvidenceBundle(
        bundle_id=UUID(payload["bundle_id"]),
        constraints=[_evidence_item_from_wire(item) for item in payload.get("constraints", [])],
        evidence=[_evidence_item_from_wire(item) for item in payload.get("evidence", [])],
    )


def _hypothesis_from_wire(payload: dict) -> Hypothesis:
    return Hypothesis(
        hypothesis_id=payload["hypothesis_id"],
        claim=payload["claim"],
        mechanism=payload["mechanism"],
        cited_evidence=list(payload.get("cited_evidence", [])),
        touched_paths=list(payload.get("touched_paths", [])),
        touched_symbols=list(payload.get("touched_symbols", [])),
        declared_violations=list(payload.get("declared_violations", [])),
        predicted_checks=list(payload.get("predicted_checks", [])),
        rank_hint=payload.get("rank_hint"),
    )


def _proposed_target(hypothesis: Hypothesis) -> dict:
    target: dict[str, str] = {}
    paths = sorted(set(hypothesis.touched_paths))
    symbols = sorted(set(hypothesis.touched_symbols))
    if len(paths) == 1:
        target["path"] = paths[0]
    if len(symbols) == 1:
        target["symbol"] = symbols[0]
    return target


def _constraint_candidate_to_wire(candidate: ConstraintCandidate) -> dict:
    return {
        "claim": candidate.claim,
        "mechanism": candidate.mechanism,
        "cited_evidence": candidate.cited_evidence,
        "source_brief_id": str(candidate.source_brief_id),
        "source_hypothesis_id": candidate.source_hypothesis_id,
        "tenant_id": candidate.tenant_id,
        "scope": candidate.scope,
        "proposed_kind": candidate.proposed_kind,
        "proposed_target": candidate.proposed_target,
    }


def _queued_candidate_to_wire(candidate) -> dict:
    return {
        "candidate_id": str(candidate.id),
        "tenant_id": candidate.tenant_id,
        "scope": candidate.scope,
        "claim": candidate.claim,
        "mechanism": candidate.mechanism,
        "cited_evidence": candidate.cited_evidence,
        "source_brief_id": str(candidate.source_brief_id),
        "source_hypothesis_id": candidate.source_hypothesis_id,
        "proposed_kind": candidate.proposed_kind,
        "proposed_target": candidate.proposed_target,
        "status": candidate.status,
        "promoted_constraint_id": str(candidate.promoted_constraint_id) if candidate.promoted_constraint_id else None,
        "created_at": candidate.created_at.isoformat() if candidate.created_at else None,
        "reviewed_at": candidate.reviewed_at.isoformat() if candidate.reviewed_at else None,
    }


def submit_hypotheses(
    *,
    evidence_bundle: dict,
    hypotheses: list[dict],
    rejected_hypothesis_ids: list[str] | None = None,
    scope: str | None = None,
    tenant_id: str | None = None,
    conn: psycopg.Connection | None = None,
) -> dict:
    bundle = _evidence_bundle_from_wire(evidence_bundle)
    hypothesis_models = [_hypothesis_from_wire(item) for item in hypotheses]
    ranked = rank_hypotheses(hypothesis_models, bundle)

    by_id = {h.hypothesis_id: h for h in hypothesis_models}
    rejected = rejected_hypothesis_ids or []
    unknown_rejected = [hid for hid in rejected if hid not in by_id]
    candidates = [
        ConstraintCandidate(
            claim=by_id[hid].claim,
            mechanism=by_id[hid].mechanism,
            cited_evidence=by_id[hid].cited_evidence,
            source_brief_id=bundle.bundle_id,
            source_hypothesis_id=hid,
            tenant_id=tenant_id,
            scope=scope,
            proposed_target=_proposed_target(by_id[hid]),
        )
        for hid in rejected
        if hid in by_id
    ]

    ranked_wire = []
    for score in ranked:
        source = by_id[score.hypothesis_id]
        ranked_wire.append(
            {
                "hypothesis_id": score.hypothesis_id,
                "claim": source.claim,
                "mechanism": source.mechanism,
                "cited_evidence": source.cited_evidence,
                "touched_paths": source.touched_paths,
                "touched_symbols": source.touched_symbols,
                "declared_violations": source.declared_violations,
                "predicted_checks": source.predicted_checks,
                "rank_hint": source.rank_hint,
                "score": score.score,
                "coverage": score.coverage,
                "contradiction": score.contradiction,
                "corroboration": score.corroboration,
                "proximity": score.proximity,
                "unique_kinds": score.unique_kinds,
                "violations": [
                    {"kind": violation.kind, "detail": violation.detail}
                    for violation in score.violations
                ],
            }
        )

    queue_repo = ConstraintCandidateRepository(conn) if conn is not None else None
    candidate_rows = []
    for candidate in candidates:
        payload = _constraint_candidate_to_wire(candidate)
        if queue_repo is not None:
            payload["candidate_id"] = str(queue_repo.enqueue(candidate))
        candidate_rows.append(payload)

    return {
        "bundle_id": str(bundle.bundle_id),
        "ranked_hypotheses": ranked_wire,
        "constraint_candidates": candidate_rows,
        "unknown_rejected_hypothesis_ids": unknown_rejected,
    }


def get_constraint_candidates(
    conn: psycopg.Connection,
    *,
    scope: str | None = None,
    status: str = "pending",
    tenant_id: str | None = None,
) -> dict:
    candidates = ConstraintCandidateRepository(conn).list(
        scope=scope,
        status=status,
        tenant_id=tenant_id,
    )
    return {
        "status": "ok",
        "candidates": [_queued_candidate_to_wire(candidate) for candidate in candidates],
    }


def review_constraint_candidate(
    conn: psycopg.Connection,
    *,
    candidate_id: str,
    resolution: str,
    promoted_constraint_id: str | None = None,
    tenant_id: str | None = None,
) -> dict:
    reviewed = ConstraintCandidateRepository(conn).review(
        UUID(candidate_id),
        resolution=resolution,
        promoted_constraint_id=UUID(promoted_constraint_id) if promoted_constraint_id else None,
        tenant_id=tenant_id,
    )
    return {
        "status": "ok" if reviewed else "not_found",
        "candidate_id": candidate_id,
        "reviewed": reviewed,
        "resolution": resolution,
        "promoted_constraint_id": promoted_constraint_id,
    }
