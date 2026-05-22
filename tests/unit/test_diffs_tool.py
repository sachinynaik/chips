"""Docker-free unit tests for get_diffs_for_scope."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from chips.mcp.tools.diffs import get_diffs_for_scope


_DT = datetime(2026, 5, 1, tzinfo=timezone.utc)

_COMMIT_ROW = ("sha1", "Alice", _DT, "fix auth", ["src/auth/service.py"])


def _conn_returning(commit_rows, cochange_rows=None):
    """Build a mock connection whose fetchall returns commit_rows then cochange_rows."""
    conn = MagicMock()
    if cochange_rows is None:
        cochange_rows = []
    # Each call to conn.execute() returns a new cursor mock.
    # The first call is the commits query; subsequent calls are per-commit cochange queries.
    cursors = []
    for row_batch in [commit_rows] + [cochange_rows] * len(commit_rows):
        cursor = MagicMock()
        cursor.fetchall.return_value = row_batch
        cursors.append(cursor)
    conn.execute.side_effect = cursors
    return conn


# ---------------------------------------------------------------------------
# Result structure
# ---------------------------------------------------------------------------

def test_result_has_status_ok():
    conn = _conn_returning([])
    result = get_diffs_for_scope(conn, scope=None, limit=5)
    assert result["status"] == "ok"


def test_result_has_scope_key_when_scope_given():
    conn = _conn_returning([])
    result = get_diffs_for_scope(conn, scope="auth", limit=5)
    assert result["scope"] == "auth"


def test_result_scope_is_none_when_no_scope():
    conn = _conn_returning([])
    result = get_diffs_for_scope(conn, scope=None, limit=5)
    assert result["scope"] is None


def test_result_has_commits_key():
    conn = _conn_returning([])
    result = get_diffs_for_scope(conn, scope=None, limit=5)
    assert "commits" in result


def test_empty_db_returns_empty_commits():
    conn = _conn_returning([])
    result = get_diffs_for_scope(conn, scope="auth", limit=10)
    assert result["commits"] == []


# ---------------------------------------------------------------------------
# Commit structure
# ---------------------------------------------------------------------------

def test_commit_has_all_required_keys():
    conn = _conn_returning([_COMMIT_ROW])
    result = get_diffs_for_scope(conn, scope="auth", limit=10)
    commit = result["commits"][0]
    for key in ("sha", "author", "message", "committed_at", "files_changed", "cochange_pairs"):
        assert key in commit, f"missing key: {key}"


def test_commit_sha_is_correct():
    conn = _conn_returning([_COMMIT_ROW])
    result = get_diffs_for_scope(conn, scope="auth", limit=10)
    assert result["commits"][0]["sha"] == "sha1"


def test_commit_author_is_correct():
    conn = _conn_returning([_COMMIT_ROW])
    result = get_diffs_for_scope(conn, scope="auth", limit=10)
    assert result["commits"][0]["author"] == "Alice"


def test_commit_message_is_correct():
    conn = _conn_returning([_COMMIT_ROW])
    result = get_diffs_for_scope(conn, scope="auth", limit=10)
    assert result["commits"][0]["message"] == "fix auth"


def test_commit_files_changed_is_list():
    conn = _conn_returning([_COMMIT_ROW])
    result = get_diffs_for_scope(conn, scope="auth", limit=10)
    assert result["commits"][0]["files_changed"] == ["src/auth/service.py"]


def test_commit_committed_at_is_iso_string():
    conn = _conn_returning([_COMMIT_ROW])
    result = get_diffs_for_scope(conn, scope="auth", limit=10)
    assert result["commits"][0]["committed_at"] == _DT.isoformat()


def test_commit_null_committed_at_becomes_none():
    row = ("sha_null_dt", "Bob", None, "msg", [])
    conn = _conn_returning([row])
    result = get_diffs_for_scope(conn, scope=None, limit=10)
    assert result["commits"][0]["committed_at"] is None


def test_commit_null_files_changed_becomes_empty_list():
    row = ("sha_no_files", "Bob", _DT, "msg", None)
    conn = _conn_returning([row])
    result = get_diffs_for_scope(conn, scope=None, limit=10)
    assert result["commits"][0]["files_changed"] == []


# ---------------------------------------------------------------------------
# Cochange pairs
# ---------------------------------------------------------------------------

def test_cochange_pairs_empty_when_none_returned():
    conn = _conn_returning([_COMMIT_ROW], cochange_rows=[])
    result = get_diffs_for_scope(conn, scope="auth", limit=10)
    assert result["commits"][0]["cochange_pairs"] == []


def test_cochange_pairs_have_correct_structure():
    cochange = [("src/auth/service.py", "src/auth/models.py", 3)]
    conn = _conn_returning([_COMMIT_ROW], cochange_rows=cochange)
    result = get_diffs_for_scope(conn, scope="auth", limit=10)
    pairs = result["commits"][0]["cochange_pairs"]
    assert len(pairs) == 1
    assert pairs[0] == {"file_a": "src/auth/service.py", "file_b": "src/auth/models.py", "frequency": 3}


def test_cochange_pairs_queried_once_per_commit():
    rows = [
        ("sha_a", "dev", _DT, "msg a", ["x.py"]),
        ("sha_b", "dev", _DT, "msg b", ["y.py"]),
    ]
    conn = _conn_returning(rows, cochange_rows=[])
    get_diffs_for_scope(conn, scope=None, limit=10)
    # 1 commits query + 2 cochange queries
    assert conn.execute.call_count == 3


# ---------------------------------------------------------------------------
# Scope filtering passed to SQL
# ---------------------------------------------------------------------------

def test_scope_filter_uses_ilike_pattern():
    conn = _conn_returning([])
    get_diffs_for_scope(conn, scope="payments", limit=5)
    first_call_args = conn.execute.call_args_list[0]
    params = first_call_args[0][1]  # positional params tuple
    assert "%payments%" in params


def test_no_scope_does_not_include_ilike_param():
    conn = _conn_returning([])
    get_diffs_for_scope(conn, scope=None, limit=5)
    first_call_args = conn.execute.call_args_list[0]
    params = first_call_args[0][1]  # positional params tuple
    assert not any("%" in str(p) for p in params)


def test_limit_is_passed_to_query():
    conn = _conn_returning([])
    get_diffs_for_scope(conn, scope=None, limit=7)
    first_call_args = conn.execute.call_args_list[0]
    params = first_call_args[0][1]
    assert 7 in params


# ---------------------------------------------------------------------------
# Multiple commits
# ---------------------------------------------------------------------------

def test_multiple_commits_all_returned():
    rows = [
        ("sha_1", "dev", _DT, "first", ["a.py"]),
        ("sha_2", "dev", _DT, "second", ["b.py"]),
    ]
    conn = _conn_returning(rows, cochange_rows=[])
    result = get_diffs_for_scope(conn, scope=None, limit=10)
    assert len(result["commits"]) == 2
    shas = [c["sha"] for c in result["commits"]]
    assert "sha_1" in shas
    assert "sha_2" in shas


# ---------------------------------------------------------------------------
# tenant_id filtering
# ---------------------------------------------------------------------------

_TENANT = "bbbbbbbb-0000-0000-0000-000000000001"


def test_tenant_id_included_in_commits_sql_when_given():
    conn = _conn_returning([])
    get_diffs_for_scope(conn, tenant_id=_TENANT)
    sql, params = conn.execute.call_args_list[0][0]
    assert "tenant_id" in sql
    assert _TENANT in params


def test_tenant_id_omitted_from_commits_sql_when_none():
    conn = _conn_returning([])
    get_diffs_for_scope(conn, tenant_id=None)
    sql, _ = conn.execute.call_args_list[0][0]
    assert "tenant_id" not in sql
