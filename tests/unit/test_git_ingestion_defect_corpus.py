from __future__ import annotations

from unittest.mock import MagicMock

from chips.harvester.git_reader import CommitRecord
from chips.harvester.ingestion import GitIngestion


def _commit(message: str, sha: str = "abc123") -> CommitRecord:
    return CommitRecord(
        sha=sha,
        author="Alice",
        committed_at="2026-05-01T00:00:00+00:00",
        message=message,
        files_changed=["src/auth.py"],
    )


def _defect_corpus_calls(conn: MagicMock) -> list[tuple[str, tuple]]:
    calls: list[tuple[str, tuple]] = []
    for call in conn.execute.call_args_list:
        sql = call.args[0]
        params = call.args[1]
        if "INSERT INTO cortex_defect_corpus" in sql:
            calls.append((sql, params))
    return calls


def test_ingest_commits_writes_raw_defect_corpus_issue_refs_and_keywords():
    conn = MagicMock()
    ingestion = GitIngestion(conn)

    ingestion.ingest_commits([_commit("hotfix(auth): resolve incident ABC-123 closes #77")])

    calls = _defect_corpus_calls(conn)
    assert len(calls) == 1
    _, params = calls[0]
    assert params[0] == "abc123"
    assert params[1] == ["#77", "ABC-123"]
    assert params[5] is True
    assert params[6] is True


def test_ingest_commits_writes_raw_defect_corpus_revert_linkage():
    conn = MagicMock()
    ingestion = GitIngestion(conn)

    ingestion.ingest_commits(
        [
            _commit(
                'Revert "break auth"\n\nThis reverts commit 0123456789abcdef0123456789abcdef01234567.',
                sha="abc124",
            )
        ]
    )

    calls = _defect_corpus_calls(conn)
    assert len(calls) == 1
    _, params = calls[0]
    assert params[0] == "abc124"
    assert params[2] == "0123456789abcdef0123456789abcdef01234567"
