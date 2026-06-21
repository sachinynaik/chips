from __future__ import annotations

import psycopg

from chips.compiler.constraint_repository import ConstraintRepository


def get_constraints(
    conn: psycopg.Connection,
    scope: str | None = None,
    tenant_id: str | None = None,
) -> dict:
    constraints = ConstraintRepository(conn).for_scope(scope, tenant_id=tenant_id)
    return {
        "status": "ok",
        "scope": scope,
        "tenant_id": tenant_id,
        "constraints": [
            {
                "id": str(c.id),
                "tenant_id": c.tenant_id,
                "scope_pattern": c.scope_pattern,
                "kind": c.kind,
                "text": c.text,
                "reason": c.reason,
                "source_kind": c.source_kind,
                "source_ref": c.source_ref,
                "target": c.target,
                "status": c.status,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in constraints
        ],
    }


def add_constraint(
    conn: psycopg.Connection,
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
    constraint_id = ConstraintRepository(conn).add(
        scope_pattern=scope_pattern,
        kind=kind,
        text=text,
        reason=reason,
        source_kind=source_kind,
        source_ref=source_ref,
        target=target,
        tenant_id=tenant_id,
    )
    return {
        "status": "ok",
        "constraint_id": str(constraint_id),
        "tenant_id": tenant_id,
        "scope_pattern": scope_pattern,
        "kind": kind,
        "text": text,
        "reason": reason,
        "source_kind": source_kind,
        "source_ref": source_ref,
        "target": target or {},
    }


def retire_constraint(
    conn: psycopg.Connection,
    constraint_id: str,
    tenant_id: str | None = None,
) -> dict:
    retired = ConstraintRepository(conn).retire(constraint_id, tenant_id=tenant_id)  # type: ignore[arg-type]
    return {
        "status": "ok",
        "constraint_id": constraint_id,
        "tenant_id": tenant_id,
        "retired": retired,
    }
