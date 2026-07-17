"""RED: adverse-events DB adapter over harvested history (step 2b, shadow-only)."""
from datetime import datetime, timezone

from chips.verifier.adverse_events import adverse_events_for_files


def _insert_commit(conn, sha: str, committed_at: datetime, files: list[str]) -> None:
    conn.execute(
        """
        INSERT INTO cortex_git_commits (sha, author, committed_at, message, files_changed)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (sha, "test", committed_at, f"commit {sha}", files),
    )


def _insert_defect(
    conn,
    sha: str,
    *,
    revert_of_sha: str | None = None,
    has_hotfix_keyword: bool = False,
    has_bug_keyword: bool = False,
    has_defect_keyword: bool = False,
    tenant_id: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO cortex_defect_corpus
            (sha, tenant_id, revert_of_sha, has_hotfix_keyword, has_bug_keyword, has_defect_keyword)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (sha, tenant_id, revert_of_sha, has_hotfix_keyword, has_bug_keyword, has_defect_keyword),
    )


AFTER = datetime(2026, 6, 1, tzinfo=timezone.utc)
BEFORE = datetime(2026, 6, 30, tzinfo=timezone.utc)
IN_WINDOW = datetime(2026, 6, 10, tzinfo=timezone.utc)
OUT_OF_WINDOW = datetime(2026, 7, 5, tzinfo=timezone.utc)


def test_empty_files_returns_empty_without_query(conn):
    result = adverse_events_for_files(conn, [], AFTER, BEFORE)
    assert result == []


def test_revert_commit_touching_file_in_window(conn):
    _insert_commit(conn, "ae-rev-001", IN_WINDOW, ["src/ae_revert_target.py"])
    _insert_defect(conn, "ae-rev-001", revert_of_sha="ae-orig-001")

    result = adverse_events_for_files(
        conn, ["src/ae_revert_target.py"], AFTER, BEFORE
    )

    assert len(result) == 1
    event = result[0]
    assert event.kind == "revert"
    assert event.file_path == "src/ae_revert_target.py"
    assert event.ref == "ae-rev-001"
    assert event.occurred_at == IN_WINDOW


def test_hotfix_commit_touching_file_in_window(conn):
    _insert_commit(conn, "ae-hot-002", IN_WINDOW, ["src/ae_hotfix_target.py"])
    _insert_defect(conn, "ae-hot-002", has_hotfix_keyword=True)

    result = adverse_events_for_files(
        conn, ["src/ae_hotfix_target.py"], AFTER, BEFORE
    )

    assert len(result) == 1
    assert result[0].kind == "hotfix"
    assert result[0].ref == "ae-hot-002"


def test_commit_outside_window_excluded(conn):
    _insert_commit(conn, "ae-out-003", OUT_OF_WINDOW, ["src/ae_outside_target.py"])
    _insert_defect(conn, "ae-out-003", has_bug_keyword=True)

    result = adverse_events_for_files(
        conn, ["src/ae_outside_target.py"], AFTER, BEFORE
    )

    assert result == []


def test_commit_touching_only_unrequested_files_excluded(conn):
    _insert_commit(conn, "ae-unreq-004", IN_WINDOW, ["src/ae_not_requested.py"])
    _insert_defect(conn, "ae-unreq-004", has_defect_keyword=True)

    result = adverse_events_for_files(
        conn, ["src/ae_something_else.py"], AFTER, BEFORE
    )

    assert result == []


def test_clean_commit_with_no_defect_flags_excluded(conn):
    _insert_commit(conn, "ae-clean-005", IN_WINDOW, ["src/ae_clean_target.py"])
    _insert_defect(conn, "ae-clean-005")

    result = adverse_events_for_files(
        conn, ["src/ae_clean_target.py"], AFTER, BEFORE
    )

    assert result == []


def test_commit_touching_two_requested_files_emits_two_events_ordered(conn):
    _insert_commit(
        conn,
        "ae-two-006",
        IN_WINDOW,
        ["src/ae_two_b.py", "src/ae_two_a.py"],
    )
    _insert_defect(conn, "ae-two-006", has_bug_keyword=True)

    result = adverse_events_for_files(
        conn, ["src/ae_two_a.py", "src/ae_two_b.py"], AFTER, BEFORE
    )

    assert len(result) == 2
    assert [event.file_path for event in result] == [
        "src/ae_two_a.py",
        "src/ae_two_b.py",
    ]
    assert all(event.kind == "hotfix" or event.kind == "revert" for event in result)
    assert all(event.ref == "ae-two-006" for event in result)
