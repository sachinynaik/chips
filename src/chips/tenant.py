from __future__ import annotations

import os
from dataclasses import dataclass

REQUIRE_TENANT_ENV = "CHIPS_REQUIRE_TENANT_ID"
MISSING_TENANT_MSG = "tenant_id is required: CHIPS_REQUIRE_TENANT_ID is set"


@dataclass(frozen=True)
class TenantScope:
    conditions: list[str]
    params: list


def require_tenant(tenant_id: str | None) -> None:
    """Raise ValueError if enforcement is on and tenant_id is absent."""
    if tenant_id is None and os.getenv(REQUIRE_TENANT_ENV):
        raise ValueError(MISSING_TENANT_MSG)


def build_tenant_scope(
    conditions: list[str],
    params: list,
    tenant_id: str | None,
    *,
    column: str = "tenant_id",
) -> TenantScope:
    """Return scoped query parts with a tenant predicate when a tenant is provided."""
    scoped_conditions = list(conditions)
    scoped_params = list(params)
    if tenant_id is not None:
        scoped_conditions.append(f"{column} = %s")
        scoped_params.append(tenant_id)
    return TenantScope(conditions=scoped_conditions, params=scoped_params)


def apply_tenant_clause(
    conditions: list[str], params: list, tenant_id: str | None
) -> None:
    """Append tenant_id = %s predicate in-place when tenant_id is not None."""
    scoped = build_tenant_scope(conditions, params, tenant_id)
    conditions[:] = scoped.conditions
    params[:] = scoped.params
