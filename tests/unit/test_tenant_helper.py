"""Contract tests for the shared tenant-scoping helper."""
from __future__ import annotations

import pytest

from chips.tenant import (
    MISSING_TENANT_MSG,
    REQUIRE_TENANT_ENV,
    apply_tenant_clause,
    build_tenant_scope,
    require_tenant,
)


# ---------------------------------------------------------------------------
# require_tenant
# ---------------------------------------------------------------------------

class TestRequireTenant:
    def test_no_error_when_tenant_id_provided(self, monkeypatch):
        monkeypatch.setenv(REQUIRE_TENANT_ENV, "1")
        require_tenant("aaaaaaaa-0000-0000-0000-000000000001")  # must not raise

    def test_no_error_when_enforcement_off_and_no_tenant(self, monkeypatch):
        monkeypatch.delenv(REQUIRE_TENANT_ENV, raising=False)
        require_tenant(None)  # must not raise

    def test_raises_when_enforcement_on_and_tenant_missing(self, monkeypatch):
        monkeypatch.setenv(REQUIRE_TENANT_ENV, "1")
        with pytest.raises(ValueError, match=MISSING_TENANT_MSG):
            require_tenant(None)

    def test_stable_error_message(self, monkeypatch):
        monkeypatch.setenv(REQUIRE_TENANT_ENV, "true")
        with pytest.raises(ValueError) as exc_info:
            require_tenant(None)
        assert str(exc_info.value) == MISSING_TENANT_MSG

    def test_empty_string_tenant_does_not_raise(self, monkeypatch):
        # Empty string is a caller mistake; enforcement only blocks None.
        monkeypatch.setenv(REQUIRE_TENANT_ENV, "1")
        require_tenant("")  # not None, should not raise


# ---------------------------------------------------------------------------
# apply_tenant_clause
# ---------------------------------------------------------------------------

class TestApplyTenantClause:
    def test_appends_condition_and_param_when_tenant_provided(self):
        conditions: list[str] = ["archived_at IS NULL"]
        params: list = []
        apply_tenant_clause(conditions, params, "tenant-x")
        assert "tenant_id = %s" in conditions
        assert "tenant-x" in params

    def test_does_not_modify_when_tenant_is_none(self):
        conditions: list[str] = ["archived_at IS NULL"]
        params: list = []
        apply_tenant_clause(conditions, params, None)
        assert len(conditions) == 1
        assert len(params) == 0

    def test_appended_at_end_of_conditions(self):
        conditions = ["a = %s", "b = %s"]
        params: list = [1, 2]
        apply_tenant_clause(conditions, params, "t")
        assert conditions[-1] == "tenant_id = %s"
        assert params[-1] == "t"

    def test_multiple_calls_append_multiple_conditions(self):
        # Unusual usage but must behave predictably.
        conditions: list[str] = []
        params: list = []
        apply_tenant_clause(conditions, params, "t1")
        apply_tenant_clause(conditions, params, "t2")
        assert conditions.count("tenant_id = %s") == 2
        assert params == ["t1", "t2"]


class TestBuildTenantScope:
    def test_returns_copy_when_tenant_missing(self):
        scope = build_tenant_scope(["a = %s"], [1], None)
        assert scope.conditions == ["a = %s"]
        assert scope.params == [1]

    def test_appends_custom_column(self):
        scope = build_tenant_scope(["1 = 1"], [], "tenant-x", column="b.tenant_id")
        assert scope.conditions[-1] == "b.tenant_id = %s"
        assert scope.params[-1] == "tenant-x"
