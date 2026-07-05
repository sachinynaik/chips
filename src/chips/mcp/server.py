from __future__ import annotations

import time

# Re-export these into the server namespace so tests can patch them directly.
from chips.compiler.builder import BriefBuilder  # noqa: F401
from chips.compiler.learning import BriefLearningService
from chips.mcp.tools.hypotheses import get_constraint_candidates as _get_constraint_candidates
from chips.mcp.tools.hypotheses import review_constraint_candidate as _review_constraint_candidate
from chips.mcp.tools.hypotheses import submit_hypotheses as _submit_hypotheses
from chips.mcp.tools.constraints import add_constraint as _add_constraint
from chips.mcp.tools.constraints import get_constraints as _get_constraints
from chips.mcp.tools.constraints import retire_constraint as _retire_constraint
from chips.memory.outcome_repository import BriefOutcomeRepository
from chips.mcp.bus import (
    _get_compressor,
    _get_conn,
    _get_embedder,
    _get_policy_loader,
    create_bus,
    main,  # noqa: F401
)
from chips.mcp.modules.brief import evidence_bundle_to_wire
from chips.mcp.tools.health import get_source_health as _get_source_health
from chips.observability.metrics import observe_feedback_submission
from chips.observability.tracing import start_span

app, _registry = create_bus()


def get_context_brief(
    task: str,
    scope: str | None = None,
    files: list[str] | None = None,
    tenant_id: str | None = None,
) -> dict:
    from chips.tenant import require_tenant

    require_tenant(tenant_id)
    with start_span(
        "chips.mcp.get_context_brief",
        scope=scope,
        tenant_id=tenant_id,
        files_count=len(files or []),
    ):
        conn = _get_conn()
        try:
            embedder = _get_embedder()
            builder = BriefBuilder(
                conn, embedder, _get_compressor(), policy_loader=_get_policy_loader()
            )
            brief = builder.build_and_log(
                task, scope=scope, files=files, tenant_id=tenant_id
            )
        finally:
            conn.close()
    return {
        "brief_id": str(brief.brief_id),
        "task": brief.task,
        "task_kind": brief.task_kind,
        "scope": brief.scope,
        "tenant_id": brief.tenant_id,
        "generated_at": brief.generated_at.isoformat(),
        "latency_ms": brief.latency_ms,
        "hard_constraints": brief.hard_constraints,
        "compressed_context": brief.compressed_context,
        "schema_version": brief.schema_version,
        "data_sources": {
            k: {
                "status": v.status,
                "detail": v.detail,
                "checked_at": v.checked_at.isoformat() if v.checked_at else None,
            }
            for k, v in brief.data_sources.items()
        },
        "evidence_bundle": evidence_bundle_to_wire(brief.evidence_bundle),
    }


def get_source_health() -> dict:
    return _get_source_health()


def submit_brief_feedback(
    brief_id: str,
    outcome: str,
    note: str | None = None,
    tenant_id: str | None = None,
    idempotency_key: str | None = None,
) -> dict:
    from uuid import UUID

    from chips.tenant import require_tenant

    require_tenant(tenant_id)
    start = time.monotonic()
    with start_span(
        "chips.mcp.submit_brief_feedback",
        outcome=outcome,
        tenant_id=tenant_id,
        idempotency_key_present=idempotency_key is not None,
    ):
        conn = _get_conn()
        try:
            result = BriefOutcomeRepository(conn).record_with_ack(
                UUID(brief_id),
                outcome=outcome,  # type: ignore[arg-type]
                note=note,
                tenant_id=tenant_id,
                idempotency_key=idempotency_key,
            )
            BriefLearningService(conn).maybe_recompute(tenant_id=tenant_id)
        finally:
            conn.close()
    observe_feedback_submission(
        outcome=result.outcome,
        deduplicated=result.deduplicated,
        latency_ms=int((time.monotonic() - start) * 1000),
    )

    return {
        "outcome_id": str(result.outcome_id),
        "brief_id": str(result.brief_id),
        "tenant_id": result.tenant_id,
        "outcome": result.outcome,
        "note": result.note,
        "recorded_at": result.created_at.isoformat() if result.created_at else None,
        "deduplicated": result.deduplicated,
    }


def get_constraints(
    scope: str | None = None,
    tenant_id: str | None = None,
) -> dict:
    from chips.tenant import require_tenant

    require_tenant(tenant_id)
    conn = _get_conn()
    try:
        return _get_constraints(conn, scope=scope, tenant_id=tenant_id)
    finally:
        conn.close()


def add_constraint(
    *,
    scope_pattern: str = "*",
    kind: str,
    text: str,
    reason: str | None = None,
    source_kind: str | None = None,
    source_ref: str | None = None,
    target: dict | None = None,
    tenant_id: str | None = None,
) -> dict:
    from chips.tenant import require_tenant

    require_tenant(tenant_id)
    conn = _get_conn()
    try:
        return _add_constraint(
            conn,
            scope_pattern=scope_pattern,
            kind=kind,
            text=text,
            reason=reason,
            source_kind=source_kind,
            source_ref=source_ref,
            target=target,
            tenant_id=tenant_id,
        )
    finally:
        conn.close()


def retire_constraint(
    constraint_id: str,
    tenant_id: str | None = None,
) -> dict:
    from chips.tenant import require_tenant

    require_tenant(tenant_id)
    conn = _get_conn()
    try:
        return _retire_constraint(conn, constraint_id=constraint_id, tenant_id=tenant_id)
    finally:
        conn.close()


def submit_hypotheses(
    *,
    evidence_bundle: dict,
    hypotheses: list[dict],
    rejected_hypothesis_ids: list[str] | None = None,
    scope: str | None = None,
    tenant_id: str | None = None,
) -> dict:
    from chips.tenant import require_tenant

    require_tenant(tenant_id)
    conn = _get_conn()
    try:
        return _submit_hypotheses(
            evidence_bundle=evidence_bundle,
            hypotheses=hypotheses,
            rejected_hypothesis_ids=rejected_hypothesis_ids,
            scope=scope,
            tenant_id=tenant_id,
            conn=conn,
        )
    finally:
        conn.close()


def get_constraint_candidates(
    *,
    scope: str | None = None,
    status: str = "pending",
    tenant_id: str | None = None,
) -> dict:
    from chips.tenant import require_tenant

    require_tenant(tenant_id)
    conn = _get_conn()
    try:
        return _get_constraint_candidates(conn, scope=scope, status=status, tenant_id=tenant_id)
    finally:
        conn.close()


def review_constraint_candidate(
    *,
    candidate_id: str,
    resolution: str,
    promoted_constraint_id: str | None = None,
    tenant_id: str | None = None,
) -> dict:
    from chips.tenant import require_tenant

    require_tenant(tenant_id)
    conn = _get_conn()
    try:
        return _review_constraint_candidate(
            conn,
            candidate_id=candidate_id,
            resolution=resolution,
            promoted_constraint_id=promoted_constraint_id,
            tenant_id=tenant_id,
        )
    finally:
        conn.close()


__all__ = [
    "app",
    "main",
    "get_context_brief",
    "get_source_health",
    "submit_brief_feedback",
    "get_constraints",
    "add_constraint",
    "retire_constraint",
    "submit_hypotheses",
    "get_constraint_candidates",
    "review_constraint_candidate",
]
