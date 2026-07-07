from __future__ import annotations

from unittest.mock import MagicMock, patch

from chips.harvester.daemon import HarvesterDaemon
from chips.harvester.embedding import OllamaEmbedder
from chips.harvester.extractor import CommitMemoryExtractor
from chips.harvester.git_reader import CommitRecord


def _commit(**kwargs) -> CommitRecord:
    defaults = dict(
        sha="abc123",
        author="Alice",
        committed_at="2026-05-01T00:00:00+00:00",
        message="fix bug",
        files_changed=["src/auth.py"],
    )
    defaults.update(kwargs)
    return CommitRecord(**defaults)


def _conn() -> MagicMock:
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = None
    return conn


def _embedder() -> MagicMock:
    m = MagicMock(spec=OllamaEmbedder)
    m.embed.return_value = [0.1] * 768
    return m


def _daemon(extractor=None, **kwargs) -> HarvesterDaemon:
    return HarvesterDaemon(
        conn=_conn(),
        embedder=_embedder(),
        repo_path=".",
        extractor=extractor,
        **kwargs,
    )


def _run_with_commits(daemon: HarvesterDaemon, commits: list[CommitRecord]) -> int:
    with patch("chips.harvester.daemon.GitReader") as mock_reader:
        with patch("chips.harvester.daemon.GitIngestion"):
            with patch("chips.harvester.daemon.MemoryRepository"):
                mock_reader.return_value.commits_since.return_value = commits
                return daemon.run_once()


# ── Extractor wiring ──────────────────────────────────────────────────────────

def test_daemon_uses_default_extractor_when_none_provided():
    daemon = _daemon()
    assert isinstance(daemon._extractor, CommitMemoryExtractor)


def test_daemon_uses_provided_extractor():
    extractor = MagicMock(spec=CommitMemoryExtractor)
    daemon = _daemon(extractor=extractor)
    assert daemon._extractor is extractor


def test_daemon_calls_provided_extractor_for_each_commit():
    extractor = MagicMock(spec=CommitMemoryExtractor)
    record = MagicMock()
    record.content = "enriched lesson"
    record.embedding = None
    extractor.extract.return_value = record

    commits = [_commit(sha="s1"), _commit(sha="s2")]
    daemon = _daemon(extractor=extractor)
    _run_with_commits(daemon, commits)

    assert extractor.extract.call_count == 2


def test_daemon_embeds_content_from_provided_extractor():
    extractor = MagicMock(spec=CommitMemoryExtractor)
    record = MagicMock()
    record.content = "enriched lesson from pyrefly + semgrep"
    record.embedding = None
    extractor.extract.return_value = record

    daemon = _daemon(extractor=extractor)
    _run_with_commits(daemon, [_commit()])

    daemon._embedder.embed.assert_called_once_with("enriched lesson from pyrefly + semgrep")


def test_daemon_skips_none_records_from_provided_extractor():
    extractor = MagicMock(spec=CommitMemoryExtractor)
    extractor.extract.return_value = None

    daemon = _daemon(extractor=extractor)
    count = _run_with_commits(daemon, [_commit(message="Merge branch 'main'")])

    assert count == 0


def test_daemon_returns_correct_count_with_mixed_extractions():
    extractor = MagicMock(spec=CommitMemoryExtractor)
    record = MagicMock()
    record.content = "lesson"
    record.embedding = None
    extractor.extract.side_effect = [record, None, record]

    daemon = _daemon(extractor=extractor)
    count = _run_with_commits(daemon, [_commit(sha=f"s{i}") for i in range(3)])

    assert count == 2


# ── Backward compatibility ────────────────────────────────────────────────────

def test_daemon_default_extractor_extracts_commit_message():
    daemon = _daemon()
    commits = [_commit(message="fix auth crash", sha="sha_unit")]
    with patch("chips.harvester.daemon.GitReader") as mock_reader:
        with patch("chips.harvester.daemon.GitIngestion"):
            with patch("chips.harvester.daemon.MemoryRepository"):
                mock_reader.return_value.commits_since.return_value = commits
                daemon.run_once()
    daemon._embedder.embed.assert_called_once_with("fix auth crash")


# ── Backfill limit ────────────────────────────────────────────────────────────
# run_once() previously hardcoded GitReader.commits_since()'s default limit=100,
# so a repo with >100 commits could never be fully backfilled: the first cycle
# only ever sees the newest 100 commits, and _last_ingested_sha() then jumps
# straight to HEAD, permanently skipping everything older.

def test_daemon_run_once_defaults_limit_to_100():
    daemon = _daemon()
    with patch("chips.harvester.daemon.GitReader") as mock_reader:
        with patch("chips.harvester.daemon.GitIngestion"):
            with patch("chips.harvester.daemon.MemoryRepository"):
                mock_reader.return_value.commits_since.return_value = []
                daemon.run_once()
    mock_reader.return_value.commits_since.assert_called_once_with(since_sha=None, limit=100)


def test_daemon_run_once_passes_explicit_limit_through_for_backfill():
    daemon = _daemon()
    with patch("chips.harvester.daemon.GitReader") as mock_reader:
        with patch("chips.harvester.daemon.GitIngestion"):
            with patch("chips.harvester.daemon.MemoryRepository"):
                mock_reader.return_value.commits_since.return_value = []
                daemon.run_once(limit=100_000)
    mock_reader.return_value.commits_since.assert_called_once_with(since_sha=None, limit=100_000)
