"""Docker-free unit tests for get_test_context tool function."""
from __future__ import annotations

from unittest.mock import MagicMock

from chips.mcp.tools.tests_ctx import get_test_context


def _conn(file_rows=None, cochange_rows=None):
    conn = MagicMock()
    cursors = []
    for rows in [file_rows or [], cochange_rows or []]:
        cursor = MagicMock()
        cursor.fetchall.return_value = rows
        cursors.append(cursor)
    conn.execute.side_effect = cursors
    return conn


_FILE_ROW = ("src/test_auth.py", 0.8, 2)
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
    result = get_test_context(_conn(file_rows=[_FILE_ROW]))
    f = result["test_files"][0]
    for key in ("file_path", "churn_score", "failure_count"):
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
