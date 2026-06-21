"""Docker-free unit tests for get_test_context tool function."""
from __future__ import annotations

from unittest.mock import MagicMock
from unittest.mock import patch

from chips.mcp.tools.tests_ctx import get_test_context


class _Store:
    def __init__(self) -> None:
        self.test_file_calls: list[tuple[str | None, int, str | None]] = []
        self.test_cochange_calls: list[tuple[str | None, int, str | None]] = []

    def test_file_signals(
        self,
        scope: str | None = None,
        limit: int = 20,
        tenant_id: str | None = None,
    ) -> list[tuple[str, float | None, float | None, str | None, int | None, int | None]]:
        self.test_file_calls.append((scope, limit, tenant_id))
        return [("src/test_auth.py", 0.8, 0.4, None, 2, 2)]

    def test_cochanges(
        self,
        scope: str | None = None,
        limit: int = 10,
        tenant_id: str | None = None,
    ) -> list[tuple[str, str, int]]:
        self.test_cochange_calls.append((scope, limit, tenant_id))
        return [("src/test_auth.py", "src/auth.py", 5)]


def _conn(file_rows=None, cochange_rows=None):
    conn = MagicMock()
    cursors = []
    for rows in [file_rows or [], cochange_rows or []]:
        cursor = MagicMock()
        cursor.fetchall.return_value = rows
        cursors.append(cursor)
    conn.execute.side_effect = cursors
    return conn


_FILE_ROW = ("src/test_auth.py", 0.8, 0.4, None, 2, 2)
_COCHANGE_ROW = ("src/test_auth.py", "src/auth.py", 5)


# ---------------------------------------------------------------------------
# Result structure
# ---------------------------------------------------------------------------

def test_result_has_status_ok():
    result = get_test_context(_conn())
    assert result["status"] == "ok"


def test_result_has_test_files_key():
    result = get_test_context(_conn())
    assert "test_files" in result


def test_result_has_cochange_pairs_key():
    result = get_test_context(_conn())
    assert "cochange_pairs" in result


def test_result_has_scope_key():
    result = get_test_context(_conn(), scope="auth")
    assert result["scope"] == "auth"


def test_result_scope_none_when_not_given():
    result = get_test_context(_conn())
    assert result["scope"] is None


def test_empty_db_returns_empty_lists():
    result = get_test_context(_conn())
    assert result["test_files"] == []
    assert result["cochange_pairs"] == []


# ---------------------------------------------------------------------------
# Test file row mapping
# ---------------------------------------------------------------------------

def test_test_file_has_expected_keys():
    with patch("chips.mcp.tools.tests_ctx.estimate_defect_density", return_value=(2.0, 500)):
        result = get_test_context(_conn(file_rows=[_FILE_ROW]))
    f = result["test_files"][0]
    for key in ("file_path", "churn_score", "cochange_entropy", "generated_kind", "defect_history_count", "defect_density", "defect_density_basis_nloc", "fragility", "fragility_inputs", "failure_count"):
        assert key in f, f"missing key: {key}"


def test_test_file_path_correct():
    result = get_test_context(_conn(file_rows=[_FILE_ROW]))
    assert result["test_files"][0]["file_path"] == "src/test_auth.py"


def test_test_file_churn_score_correct():
    result = get_test_context(_conn(file_rows=[_FILE_ROW]))
    assert result["test_files"][0]["churn_score"] == 0.8


def test_test_file_failure_count_correct():
    result = get_test_context(_conn(file_rows=[_FILE_ROW]))
    assert result["test_files"][0]["failure_count"] == 2


def test_test_file_cochange_entropy_correct():
    result = get_test_context(_conn(file_rows=[_FILE_ROW]))
    assert result["test_files"][0]["cochange_entropy"] == 0.4


def test_test_file_defect_history_count_correct():
    result = get_test_context(_conn(file_rows=[_FILE_ROW]))
    assert result["test_files"][0]["defect_history_count"] == 2


def test_test_file_defect_density_uses_density_helper():
    with patch("chips.mcp.tools.tests_ctx.estimate_defect_density", return_value=(2.0, 500)):
        result = get_test_context(_conn(file_rows=[_FILE_ROW]))

    assert result["test_files"][0]["defect_density"] == 2.0
    assert result["test_files"][0]["defect_density_basis_nloc"] == 500


def test_test_file_yield_score_is_present():
    with patch("chips.mcp.tools.tests_ctx.estimate_defect_density", return_value=(2.0, 500)):
        with patch(
            "chips.mcp.tools.tests_ctx.compute_yield_score",
            return_value={"score": 4.2, "mode": "raw", "calibrated": False, "inputs": {"complete": True, "present": [], "missing": []}},
        ):
            with patch(
                "chips.mcp.tools.tests_ctx.assay_signal",
                return_value={"purity": {"score": 1.0, "deterministic_fraction": 1.0, "dopants": []}, "freshness": {"complete": False, "missing": ["code_version"]}, "source_kind": "git_history"},
            ):
                result = get_test_context(_conn(file_rows=[_FILE_ROW]))

    assert result["test_files"][0]["yield_score"]["mode"] == "raw"
    assert result["test_files"][0]["yield_score"]["calibrated"] is False


def test_test_file_assay_is_present():
    with patch("chips.mcp.tools.tests_ctx.estimate_defect_density", return_value=(2.0, 500)):
        with patch(
            "chips.mcp.tools.tests_ctx.assay_signal",
            return_value={"purity": {"score": 1.0, "deterministic_fraction": 1.0, "dopants": []}, "freshness": {"complete": False, "missing": ["code_version"]}, "source_kind": "git_history"},
        ):
            result = get_test_context(_conn(file_rows=[_FILE_ROW]))

    assert result["test_files"][0]["assay"]["purity"]["score"] == 1.0


def test_test_file_fragility_correct():
    result = get_test_context(_conn(file_rows=[_FILE_ROW]))
    assert result["test_files"][0]["fragility"] == 0.65


def test_test_file_fragility_inputs_complete_when_all_inputs_present():
    result = get_test_context(_conn(file_rows=[_FILE_ROW]))
    assert result["test_files"][0]["fragility_inputs"] == {
        "complete": True,
        "present": ["churn_score", "cochange_entropy", "defect_history_count"],
        "missing": [],
    }


# ---------------------------------------------------------------------------
# Cochange row mapping
# ---------------------------------------------------------------------------

def test_cochange_pair_has_expected_keys():
    result = get_test_context(_conn(cochange_rows=[_COCHANGE_ROW]))
    pair = result["cochange_pairs"][0]
    for key in ("file_a", "file_b", "frequency"):
        assert key in pair, f"missing key: {key}"


def test_cochange_pair_values_correct():
    result = get_test_context(_conn(cochange_rows=[_COCHANGE_ROW]))
    pair = result["cochange_pairs"][0]
    assert pair["file_a"] == "src/test_auth.py"
    assert pair["file_b"] == "src/auth.py"
    assert pair["frequency"] == 5


# ---------------------------------------------------------------------------
# Two DB queries are made
# ---------------------------------------------------------------------------

def test_two_queries_executed():
    conn = _conn()
    get_test_context(conn)
    assert conn.execute.call_count == 2


# ---------------------------------------------------------------------------
# Scope is passed to both queries
# ---------------------------------------------------------------------------

def test_scope_included_in_file_query_params():
    conn = _conn()
    get_test_context(conn, scope="payments")
    first_call_params = conn.execute.call_args_list[0][0][1]
    assert any("payments" in str(p) for p in first_call_params)


def test_scope_included_in_cochange_query_params():
    conn = _conn()
    get_test_context(conn, scope="payments")
    second_call_params = conn.execute.call_args_list[1][0][1]
    assert any("payments" in str(p) for p in second_call_params)


def test_limit_passed_to_file_query():
    conn = _conn()
    get_test_context(conn, limit=5)
    first_call_params = conn.execute.call_args_list[0][0][1]
    assert 5 in first_call_params


# ---------------------------------------------------------------------------
# tenant_id filtering
# ---------------------------------------------------------------------------

_TENANT = "bbbbbbbb-0000-0000-0000-000000000001"


def test_tenant_id_included_in_file_sql_when_given():
    conn = _conn()
    get_test_context(conn, tenant_id=_TENANT)
    sql, params = conn.execute.call_args_list[0][0]
    assert "tenant_id" in sql
    assert _TENANT in params


def test_tenant_id_included_in_cochange_sql_when_given():
    conn = _conn()
    get_test_context(conn, tenant_id=_TENANT)
    sql, params = conn.execute.call_args_list[1][0]
    assert "tenant_id" in sql
    assert _TENANT in params


def test_tenant_id_omitted_from_both_queries_when_none():
    conn = _conn()
    get_test_context(conn, tenant_id=None)
    for call in conn.execute.call_args_list:
        sql, _ = call[0]
        assert "tenant_id" not in sql


def test_get_test_context_uses_store_boundary_when_store_is_provided():
    store = _Store()

    with patch("chips.mcp.tools.tests_ctx.estimate_defect_density", return_value=(2.0, 500)):
        result = get_test_context(store, scope="auth", limit=5, tenant_id="tenant-1")

    assert result["status"] == "ok"
    assert result["test_files"][0]["file_path"] == "src/test_auth.py"
    assert result["cochange_pairs"][0]["frequency"] == 5
    assert store.test_file_calls == [("auth", 5, "tenant-1")]
    assert store.test_cochange_calls == [("auth", 10, "tenant-1")]
