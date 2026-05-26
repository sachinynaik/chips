from __future__ import annotations

# Re-export these into the server namespace so tests can patch them directly.
from chips.compiler.builder import BriefBuilder  # noqa: F401
from chips.mcp.bus import (
    _get_compressor,
    _get_conn,
    _get_embedder,
    _get_policy_loader,
    create_bus,
    main,  # noqa: F401
)

app, _registry = create_bus()


def get_context_brief(
    task: str,
    scope: str | None = None,
    tenant_id: str | None = None,
) -> dict:
    conn = _get_conn()
    embedder = _get_embedder()
    builder = BriefBuilder(
        conn, embedder, _get_compressor(), policy_loader=_get_policy_loader()
    )
    brief = builder.build(task, scope=scope, tenant_id=tenant_id)
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
            k: {"status": v.status, "detail": v.detail}
            for k, v in brief.data_sources.items()
        },
    }


__all__ = ["app", "main", "get_context_brief"]
