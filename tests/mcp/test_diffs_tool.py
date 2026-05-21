"""RED: get_diffs_for_scope integration tests."""
from datetime import datetime, timezone

import pytest

from chips.harvester.git_ingestion import GitIngestion
from chips.harvester.git_reader import CommitRecord


def _commit(sha, files, message="test commit", author="dev"):
    return CommitRecord(
        sha=sha,
        message=message,
        author=author,
        committed_at="2026-05-01T00:00:00+00:00",
        files_changed=files,
    )


def test_get_diffs_returns_commits_in_scope(conn):
    from chips.mcp.tools.diffs import get_diffs_for_scope
    GitIngestion(conn).ingest_commits([
        _commit("sha_auth1", ["src/auth/service.py", "src/auth/utils.py"]),
    ])
    result = get_diffs_for_scope(conn, scope="auth", limit=10)
    shas = [c["sha"] for c in result["commits"]]
    assert "sha_auth1" in shas


def test_get_diffs_excludes_commits_outside_scope(conn):
    from chips.mcp.tools.diffs import get_diffs_for_scope
    GitIngestion(conn).ingest_commits([
        _commit("sha_parking1", ["src/parking/lot.py"]),
    ])
    result = get_diffs_for_scope(conn, scope="auth", limit=10)
    shas = [c["sha"] for c in result["commits"]]
    assert "sha_parking1" not in shas


def test_get_diffs_none_scope_returns_all_recent(conn):
    from chips.mcp.tools.diffs import get_diffs_for_scope
    GitIngestion(conn).ingest_commits([
        _commit("sha_any_a", ["src/auth/x.py"]),
        _commit("sha_any_b", ["src/parking/y.py"]),
    ])
    result = get_diffs_for_scope(conn, scope=None, limit=20)
    shas = [c["sha"] for c in result["commits"]]
    assert "sha_any_a" in shas
    assert "sha_any_b" in shas


def test_get_diffs_respects_limit(conn):
    from chips.mcp.tools.diffs import get_diffs_for_scope
    commits = [_commit(f"sha_lim_{i}", [f"src/auth/file_{i}.py"]) for i in range(10)]
    GitIngestion(conn).ingest_commits(commits)
    result = get_diffs_for_scope(conn, scope="auth", limit=3)
    assert len(result["commits"]) <= 3


def test_get_diffs_commit_has_expected_keys(conn):
    from chips.mcp.tools.diffs import get_diffs_for_scope
    GitIngestion(conn).ingest_commits([
        _commit("sha_keys1", ["src/auth/service.py"], message="add auth"),
    ])
    result = get_diffs_for_scope(conn, scope="auth", limit=10)
    commit = next(c for c in result["commits"] if c["sha"] == "sha_keys1")
    for key in ("sha", "message", "author", "committed_at", "files_changed", "cochange_pairs"):
        assert key in commit


def test_get_diffs_includes_cochange_pairs_for_commit_files(conn):
    from chips.mcp.tools.diffs import get_diffs_for_scope
    GitIngestion(conn).ingest_commits([
        _commit("sha_co_a1", ["src/auth/service.py", "src/auth/models.py"]),
        _commit("sha_co_b1", ["src/auth/service.py", "src/auth/models.py"]),
    ])
    result = get_diffs_for_scope(conn, scope="auth", limit=10)
    all_pairs = [p for c in result["commits"] for p in c["cochange_pairs"]]
    assert len(all_pairs) > 0


def test_get_diffs_result_status_is_ok(conn):
    from chips.mcp.tools.diffs import get_diffs_for_scope
    result = get_diffs_for_scope(conn, scope="auth", limit=5)
    assert result["status"] == "ok"


def test_get_diffs_result_has_scope_key(conn):
    from chips.mcp.tools.diffs import get_diffs_for_scope
    result = get_diffs_for_scope(conn, scope="payments", limit=5)
    assert result["scope"] == "payments"
