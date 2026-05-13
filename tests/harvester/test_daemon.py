from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from chips.harvester.daemon import HarvesterDaemon
from chips.harvester.git_reader import CommitRecord


def _fake_commit(sha: str = "abc123", message: str = "fix crash") -> CommitRecord:
    return CommitRecord(
        sha=sha,
        author="Alice",
        committed_at="2026-05-13T10:00:00+00:00",
        message=message,
        files_changed=["src/auth/login.py"],
    )


def _make_embedder(vector: list[float] | None = None) -> MagicMock:
    m = MagicMock()
    m.embed.return_value = vector or [0.1] * 768
    return m


def test_run_once_returns_zero_when_no_new_commits(conn):
    with patch("chips.harvester.daemon.GitReader") as mock_reader_cls:
        mock_reader_cls.return_value.commits_since.return_value = []
        daemon = HarvesterDaemon(conn, _make_embedder(), repo_path=".")
        count = daemon.run_once()
    assert count == 0


def test_run_once_ingests_commits_to_db(conn):
    commits = [_fake_commit("sha1", "fix login crash")]
    with patch("chips.harvester.daemon.GitReader") as mock_reader_cls:
        mock_reader_cls.return_value.commits_since.return_value = commits
        daemon = HarvesterDaemon(conn, _make_embedder(), repo_path=".")
        daemon.run_once()
    row = conn.execute(
        "SELECT sha FROM cortex_git_commits WHERE sha = 'sha1'"
    ).fetchone()
    assert row is not None


def test_run_once_writes_memory_for_each_commit(conn):
    commits = [
        _fake_commit("sha1", "fix auth crash"),
        _fake_commit("sha2", "add retry logic"),
    ]
    with patch("chips.harvester.daemon.GitReader") as mock_reader_cls:
        mock_reader_cls.return_value.commits_since.return_value = commits
        daemon = HarvesterDaemon(conn, _make_embedder(), repo_path=".")
        count = daemon.run_once()
    assert count == 2


def test_run_once_skips_merge_commits(conn):
    commits = [
        _fake_commit("sha1", "Merge branch 'main' into feature"),
        _fake_commit("sha2", "fix real bug"),
    ]
    with patch("chips.harvester.daemon.GitReader") as mock_reader_cls:
        mock_reader_cls.return_value.commits_since.return_value = commits
        daemon = HarvesterDaemon(conn, _make_embedder(), repo_path=".")
        count = daemon.run_once()
    assert count == 1


def test_run_once_embeds_memory_content(conn):
    commits = [_fake_commit("sha1", "fix crash")]
    embedder = _make_embedder()
    with patch("chips.harvester.daemon.GitReader") as mock_reader_cls:
        mock_reader_cls.return_value.commits_since.return_value = commits
        daemon = HarvesterDaemon(conn, embedder, repo_path=".")
        daemon.run_once()
    embedder.embed.assert_called_once_with("fix crash")


def test_run_once_passes_since_sha_to_reader(conn):
    # Pre-insert a commit so the daemon knows the last SHA
    conn.execute(
        """
        INSERT INTO cortex_git_commits (sha, author, committed_at, message, files_changed)
        VALUES ('prev_sha', 'Alice', now(), 'previous commit', '{}')
        """
    )
    conn.commit()

    with patch("chips.harvester.daemon.GitReader") as mock_reader_cls:
        mock_reader_cls.return_value.commits_since.return_value = []
        daemon = HarvesterDaemon(conn, _make_embedder(), repo_path=".")
        daemon.run_once()
        mock_reader_cls.return_value.commits_since.assert_called_once()
        call_kwargs = mock_reader_cls.return_value.commits_since.call_args
        assert call_kwargs[1].get("since_sha") == "prev_sha" or call_kwargs[0][0] == "prev_sha"


def test_run_once_memory_stored_in_db(conn):
    commits = [_fake_commit("sha99", "refactor auth module")]
    with patch("chips.harvester.daemon.GitReader") as mock_reader_cls:
        mock_reader_cls.return_value.commits_since.return_value = commits
        daemon = HarvesterDaemon(conn, _make_embedder(), repo_path=".")
        daemon.run_once()
    row = conn.execute(
        "SELECT content, scope FROM cortex_memories WHERE source = 'sha99'"
    ).fetchone()
    assert row is not None
    assert row[0] == "refactor auth module"
    assert row[1] == "auth"
