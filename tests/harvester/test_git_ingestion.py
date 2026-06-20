"""RED: git ingestion into DB tests."""
import pytest
from chips.harvester.git_reader import CommitRecord
from chips.harvester.ingestion import GitIngestion
from chips.compiler.retrieval import retrieve_file_signals


def _make_commit(sha: str, files: list[str]) -> CommitRecord:
    return CommitRecord(
        sha=sha,
        author="test",
        committed_at="2026-05-10T12:00:00+00:00",
        message=f"commit {sha}",
        files_changed=files,
    )


def test_ingest_commit_stored_in_db(conn):
    ingestion = GitIngestion(conn)
    commit = _make_commit("abc001", ["src/a.py", "src/b.py"])

    ingestion.ingest_commits([commit])

    row = conn.execute(
        "SELECT sha, author FROM cortex_git_commits WHERE sha = 'abc001'"
    ).fetchone()
    assert row is not None
    assert row[0] == "abc001"


def test_ingest_is_idempotent(conn):
    ingestion = GitIngestion(conn)
    commit = _make_commit("abc002", ["src/a.py"])

    ingestion.ingest_commits([commit])
    ingestion.ingest_commits([commit])

    rows = conn.execute(
        "SELECT sha FROM cortex_git_commits WHERE sha = 'abc002'"
    ).fetchall()
    assert len(rows) == 1


def test_ingest_writes_cochange_pairs(conn):
    ingestion = GitIngestion(conn)
    commit = _make_commit("abc003", ["src/checkout.py", "src/test_checkout.py"])

    ingestion.ingest_commits([commit])

    rows = conn.execute(
        "SELECT file_a, file_b, frequency FROM cortex_cochange_pairs "
        "WHERE (file_a = 'src/checkout.py' AND file_b = 'src/test_checkout.py') "
        "OR (file_a = 'src/test_checkout.py' AND file_b = 'src/checkout.py')"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0][2] == 1


def test_ingest_increments_cochange_frequency(conn):
    ingestion = GitIngestion(conn)
    c1 = _make_commit("abc004", ["src/x.py", "src/y.py"])
    c2 = _make_commit("abc005", ["src/x.py", "src/y.py"])

    ingestion.ingest_commits([c1, c2])

    rows = conn.execute(
        "SELECT frequency FROM cortex_cochange_pairs "
        "WHERE (file_a = 'src/x.py' AND file_b = 'src/y.py') "
        "OR (file_a = 'src/y.py' AND file_b = 'src/x.py')"
    ).fetchall()
    assert rows[0][0] == 2


def test_ingest_updates_file_signals(conn):
    ingestion = GitIngestion(conn)
    c1 = _make_commit("abc006", ["src/hot.py", "src/cold.py"])
    c2 = _make_commit("abc007", ["src/hot.py"])

    ingestion.ingest_commits([c1, c2])

    row = conn.execute(
        "SELECT churn_score FROM cortex_file_signals WHERE file_path = 'src/hot.py'"
    ).fetchone()
    assert row is not None
    assert row[0] > 0


def test_ingest_persists_cochange_entropy_for_scattered_files(conn):
    ingestion = GitIngestion(conn)
    commits = [
        _make_commit("abc010", ["src/hot.py", "src/a.py"]),
        _make_commit("abc011", ["src/hot.py", "src/b.py"]),
        _make_commit("abc012", ["src/hot.py", "src/c.py"]),
    ]

    ingestion.ingest_commits(commits)

    row = conn.execute(
        "SELECT cochange_entropy FROM cortex_file_signals WHERE file_path = 'src/hot.py'"
    ).fetchone()
    assert row is not None
    assert row[0] > 0


def test_ingest_marks_generated_kind_and_snapshots_it(conn):
    ingestion = GitIngestion(conn)
    commit = _make_commit("abc013", ["src/migrations/001_auth.py", "src/auth.py"])

    ingestion.ingest_commits([commit])

    signal_row = conn.execute(
        "SELECT generated_kind, cochange_entropy "
        "FROM cortex_file_signals WHERE file_path = 'src/migrations/001_auth.py'"
    ).fetchone()
    snapshot_row = conn.execute(
        "SELECT basis_sha, generated_kind, fragility_complete, fragility_inputs_missing "
        "FROM cortex_file_signal_snapshots WHERE file_path = 'src/migrations/001_auth.py'"
    ).fetchone()
    assert signal_row == ("scaffolded", 0.0)
    assert snapshot_row[0] == "abc013"
    assert snapshot_row[1] == "scaffolded"
    assert snapshot_row[2] is False
    assert "defect_history_count" in snapshot_row[3]


def test_ingest_captures_raw_defect_corpus_evidence(conn):
    ingestion = GitIngestion(conn)
    commit = CommitRecord(
        sha="abc008",
        author="test",
        committed_at="2026-05-10T12:00:00+00:00",
        message="hotfix(auth): resolve incident ABC-123 closes #77",
        files_changed=["src/auth.py"],
    )

    ingestion.ingest_commits([commit])

    row = conn.execute(
        "SELECT issue_refs, has_hotfix_keyword, has_incident_keyword, revert_of_sha "
        "FROM cortex_defect_corpus WHERE sha = 'abc008'"
    ).fetchone()
    assert row is not None
    assert row[0] == ["#77", "ABC-123"]
    assert row[1] is True
    assert row[2] is True
    assert row[3] is None


def test_ingest_captures_revert_linkage_for_defect_corpus(conn):
    ingestion = GitIngestion(conn)
    commit = CommitRecord(
        sha="abc009",
        author="test",
        committed_at="2026-05-10T12:00:00+00:00",
        message='Revert "break auth"\n\nThis reverts commit 0123456789abcdef0123456789abcdef01234567.',
        files_changed=["src/auth.py"],
    )

    ingestion.ingest_commits([commit])

    row = conn.execute(
        "SELECT revert_of_sha FROM cortex_defect_corpus WHERE sha = 'abc009'"
    ).fetchone()
    assert row is not None
    assert row[0] == "0123456789abcdef0123456789abcdef01234567"


def test_retrieve_file_signals_uses_high_precision_defect_rule(conn):
    ingestion = GitIngestion(conn)
    non_defect = CommitRecord(
        sha="abc014",
        author="test",
        committed_at="2026-05-10T12:00:00+00:00",
        message="refs #88 only",
        files_changed=["src/auth.py"],
    )
    true_defect = CommitRecord(
        sha="abc015",
        author="test",
        committed_at="2026-05-11T12:00:00+00:00",
        message="bugfix(auth): closes #77",
        files_changed=["src/auth.py"],
    )

    ingestion.ingest_commits([non_defect, true_defect])

    result = retrieve_file_signals(conn, ["src/auth.py"])
    assert result[0]["defect_history_count"] == 1
    assert result[0]["yield_score"]["mode"] == "raw"
    assert result[0]["assay"]["purity"]["score"] == 1.0


def test_defect_corpus_is_rebuildable_from_git_commits(conn):
    ingestion = GitIngestion(conn)
    commits = [
        CommitRecord(
            sha="abc016",
            author="test",
            committed_at="2026-05-12T12:00:00+00:00",
            message="hotfix(auth): resolve incident ABC-123 closes #77",
            files_changed=["src/auth.py"],
        ),
        CommitRecord(
            sha="abc017",
            author="test",
            committed_at="2026-05-13T12:00:00+00:00",
            message='Revert "break auth"\n\nThis reverts commit 0123456789abcdef0123456789abcdef01234567.',
            files_changed=["src/auth.py"],
        ),
    ]

    ingestion.ingest_commits(commits)

    original_rows = conn.execute(
        """
        SELECT
            sha,
            issue_refs,
            revert_of_sha,
            has_bug_keyword,
            has_defect_keyword,
            has_hotfix_keyword,
            has_incident_keyword
        FROM cortex_defect_corpus
        WHERE sha IN ('abc016', 'abc017')
        ORDER BY sha
        """
    ).fetchall()

    conn.execute("DELETE FROM cortex_defect_corpus WHERE sha IN ('abc016', 'abc017')")

    raw_commits = [
        CommitRecord(
            sha=row[0],
            author=row[1],
            committed_at=row[2].isoformat(),
            message=row[3],
            files_changed=row[4],
        )
        for row in conn.execute(
            """
            SELECT sha, author, committed_at, message, files_changed
            FROM cortex_git_commits
            WHERE sha IN ('abc016', 'abc017')
            ORDER BY sha
            """
        ).fetchall()
    ]

    ingestion._upsert_defect_corpus(raw_commits)

    rebuilt_rows = conn.execute(
        """
        SELECT
            sha,
            issue_refs,
            revert_of_sha,
            has_bug_keyword,
            has_defect_keyword,
            has_hotfix_keyword,
            has_incident_keyword
        FROM cortex_defect_corpus
        WHERE sha IN ('abc016', 'abc017')
        ORDER BY sha
        """
    ).fetchall()

    assert rebuilt_rows == original_rows
