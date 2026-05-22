"""Docker-free unit tests for get_contracts tool function."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from chips.mcp.tools.contracts import get_contracts


def _conn(rows):
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = rows
    return conn


_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
_ROW = (_ID, "payments", "Never double-charge.", ["billing"], 0.95)


# ---------------------------------------------------------------------------
# Result structure
# ---------------------------------------------------------------------------

def test_result_has_status_ok():
    result = get_contracts(_conn([]))
    assert result["status"] == "ok"


def test_result_has_contracts_key():
    result = get_contracts(_conn([]))
    assert "contracts" in result


def test_result_has_scope_key():
    result = get_contracts(_conn([]), scope="payments")
    assert result["scope"] == "payments"


def test_result_scope_is_none_when_not_given():
    result = get_contracts(_conn([]))
    assert result["scope"] is None


def test_empty_db_returns_empty_list():
    result = get_contracts(_conn([]))
    assert result["contracts"] == []


# ---------------------------------------------------------------------------
# Contract row mapping
# ---------------------------------------------------------------------------

def test_contract_has_expected_keys():
    result = get_contracts(_conn([_ROW]))
    contract = result["contracts"][0]
    for key in ("id", "scope", "content", "tags", "confidence"):
        assert key in contract, f"missing key: {key}"


def test_contract_id_is_string():
    result = get_contracts(_conn([_ROW]))
    assert result["contracts"][0]["id"] == str(_ID)


def test_contract_content_correct():
    result = get_contracts(_conn([_ROW]))
    assert result["contracts"][0]["content"] == "Never double-charge."


def test_contract_tags_correct():
    result = get_contracts(_conn([_ROW]))
    assert result["contracts"][0]["tags"] == ["billing"]


def test_contract_confidence_correct():
    result = get_contracts(_conn([_ROW]))
    assert result["contracts"][0]["confidence"] == 0.95


def test_multiple_rows_all_returned():
    id2 = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000002")
    rows = [_ROW, (id2, "auth", "Tokens expire in 24h.", [], 0.9)]
    result = get_contracts(_conn(rows))
    assert len(result["contracts"]) == 2


# ---------------------------------------------------------------------------
# SQL filtering — scope is passed to DB query
# ---------------------------------------------------------------------------

def test_scope_filter_passed_to_execute_when_given():
    conn = _conn([])
    get_contracts(conn, scope="payments")
    sql, params = conn.execute.call_args[0]
    assert "%s" in sql or "?" in sql      # parameterised query
    assert "payments" in params


def test_no_scope_does_not_pass_scope_param_as_filter():
    conn = _conn([])
    get_contracts(conn, scope=None)
    _, params = conn.execute.call_args[0]
    # Only limit should be in params, not a scope string
    assert "payments" not in str(params)


def test_limit_is_passed_to_query():
    conn = _conn([])
    get_contracts(conn, limit=7)
    _, params = conn.execute.call_args[0]
    assert 7 in params


def test_default_limit_is_20():
    conn = _conn([])
    get_contracts(conn)
    _, params = conn.execute.call_args[0]
    assert 20 in params
