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


def _conn_for_truth_backed_rebuild() -> MagicMock:
    conn = MagicMock()
    git_rows: dict[str, tuple[str, str, str, str, list[str]]] = {}

    def execute(sql, params=None):
        cursor = MagicMock()
        if "INSERT INTO cortex_git_commits" in sql:
            sha, author, committed_at, message, files_changed = params
            git_rows[sha] = (sha, author, committed_at, message, files_changed)
            cursor.fetchall.return_value = []
        elif "SELECT sha, author, committed_at, message, files_changed" in sql:
            requested = params[0]
            cursor.fetchall.return_value = [git_rows[sha] for sha in requested]
        else:
            cursor.fetchall.return_value = []
        return cursor

    conn.execute.side_effect = execute
    return conn


def test_ingest_commits_writes_raw_defect_corpus_issue_refs_and_keywords():
    conn = _conn_for_truth_backed_rebuild()
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
    conn = _conn_for_truth_backed_rebuild()
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


def test_ingest_commits_writes_cumulative_cochange_entropy_into_file_signals():
    conn = MagicMock()

    def execute(sql, params):
        cursor = MagicMock()
        if "SELECT file_a, file_b, frequency" in sql:
            # Frequency 2 so each partner clears the co-change support threshold
            # (open decision #2: min support 2); single co-changes are noise.
            cursor.fetchall.return_value = [
                ("src/auth.py", "src/a.py", 2),
                ("src/auth.py", "src/b.py", 2),
                ("src/auth.py", "src/c.py", 2),
            ]
        else:
            cursor.fetchall.return_value = []
        return cursor

    conn.execute.side_effect = execute
    ingestion = GitIngestion(conn)

    ingestion.ingest_commits(
        [
            _commit("change auth with a", sha="abc200"),
            CommitRecord(
                sha="abc201",
                author="Alice",
                committed_at="2026-05-01T00:00:00+00:00",
                message="change auth with b",
                files_changed=["src/auth.py", "src/b.py"],
            ),
            CommitRecord(
                sha="abc202",
                author="Alice",
                committed_at="2026-05-01T00:00:00+00:00",
                message="change auth with c",
                files_changed=["src/auth.py", "src/c.py"],
            ),
        ]
    )

    file_signal_calls = [
        call for call in conn.execute.call_args_list if "INSERT INTO cortex_file_signals" in call.args[0]
    ]
    assert file_signal_calls
    auth_call = next(call for call in file_signal_calls if call.args[1][0] == "src/auth.py")
    assert auth_call.args[1][2] > 0.0
