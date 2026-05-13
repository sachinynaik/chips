from __future__ import annotations

from chips.harvester.extractor import CommitMemoryExtractor
from chips.harvester.git_reader import CommitRecord
from chips.memory.models import MemoryType


def _commit(
    sha: str = "abc123",
    message: str = "fix login crash",
    author: str = "Alice",
    files: list[str] | None = None,
) -> CommitRecord:
    return CommitRecord(
        sha=sha,
        author=author,
        committed_at="2026-05-13T10:00:00+00:00",
        message=message,
        files_changed=files or ["src/auth/login.py"],
    )


def test_extract_returns_memory_record():
    record = CommitMemoryExtractor().extract(_commit())
    assert record is not None


def test_extract_type_is_lesson():
    record = CommitMemoryExtractor().extract(_commit())
    assert record.type == MemoryType.LESSON


def test_extract_content_is_commit_message():
    record = CommitMemoryExtractor().extract(_commit(message="add dark mode"))
    assert record.content == "add dark mode"


def test_extract_author_preserved():
    record = CommitMemoryExtractor().extract(_commit(author="Bob"))
    assert record.author == "Bob"


def test_extract_source_is_sha():
    record = CommitMemoryExtractor().extract(_commit(sha="deadbeef"))
    assert record.source == "deadbeef"


def test_extract_scope_from_top_level_directory():
    record = CommitMemoryExtractor().extract(_commit(files=["src/auth/login.py", "src/auth/token.py"]))
    assert record.scope == "auth"


def test_extract_scope_most_common_directory():
    record = CommitMemoryExtractor().extract(
        _commit(files=["src/payments/charge.py", "src/payments/refund.py", "src/auth/token.py"])
    )
    assert record.scope == "payments"


def test_extract_scope_falls_back_to_general_when_no_dirs():
    record = CommitMemoryExtractor().extract(_commit(files=["README.md", "setup.py"]))
    assert record.scope == "general"


def test_extract_tags_include_task_kind():
    record = CommitMemoryExtractor().extract(_commit(message="fix the broken pipeline"))
    assert "bugfix" in record.tags


def test_extract_skips_merge_commits():
    record = CommitMemoryExtractor().extract(_commit(message="Merge branch 'main' into feature"))
    assert record is None


def test_extract_skips_empty_message():
    record = CommitMemoryExtractor().extract(_commit(message=""))
    assert record is None


def test_extract_embedding_is_none_before_embed():
    record = CommitMemoryExtractor().extract(_commit())
    assert record.embedding is None
