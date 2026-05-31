from __future__ import annotations

# Re-export these into the server namespace so tests can patch them directly.
from chips.compiler.builder import BriefBuilder  # noqa: F401
from chips.compiler.learning import BriefLearningService
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

app, _registry = create_bus()


def get_context_brief(
    task: str,
    scope: str | None = None,
    files: list[str] | None = None,
    tenant_id: str | None = None,
) -> dict:
    from chips.tenant import require_tenant

    require_tenant(tenant_id)
    conn = _get_conn()
    try:
        embedder = _get_embedder()
        builder = BriefBuilder(
            conn, embedder, _get_compressor(), policy_loader=_get_policy_loader()
        )
        brief = builder.build(task, scope=scope, files=files, tenant_id=tenant_id)
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

    return {
        "outcome_id": str(result.outcome_id),
        "brief_id": str(result.brief_id),
        "tenant_id": result.tenant_id,
        "outcome": result.outcome,
        "note": result.note,
        "recorded_at": result.created_at.isoformat() if result.created_at else None,
        "deduplicated": result.deduplicated,
    }


__all__ = [
    "app",
    "main",
    "get_context_brief",
    "get_source_health",
    "submit_brief_feedback",
]
