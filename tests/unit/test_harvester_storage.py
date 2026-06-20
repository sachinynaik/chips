from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import MagicMock

from chips.harvester.daemon import HarvesterDaemon
from chips.harvester.git_reader import CommitRecord, FileSignal
from chips.harvester.ingestion import GitIngestion
from chips.harvester.storage import (
    DERIVED_TABLES,
    TRUTH_TABLES,
    PostgresHarvesterStore,
    is_derived_table,
    is_truth_table,
)


def _commit(sha: str, files: list[str]) -> CommitRecord:
    return CommitRecord(
        sha=sha,
        author="test",
        committed_at="2026-06-20T00:00:00+00:00",
        message=f"commit {sha}",
        files_changed=files,
    )


def test_harvester_table_classification_is_explicit_and_non_overlapping():
    assert TRUTH_TABLES == ("cortex_git_commits",)
    assert DERIVED_TABLES == (
        "cortex_defect_corpus",
        "cortex_cochange_pairs",
        "cortex_file_signals",
        "cortex_file_signal_snapshots",
    )
    assert set(TRUTH_TABLES).isdisjoint(DERIVED_TABLES)
    assert is_truth_table("cortex_git_commits") is True
    assert is_derived_table("cortex_defect_corpus") is True
    assert is_truth_table("cortex_defect_corpus") is False
    assert is_derived_table("cortex_git_commits") is False


@dataclass
class _FakeStore:
    appended_commits: list[list[CommitRecord]] = field(default_factory=list)
    rebuilt_defect_batches: list[list[CommitRecord]] = field(default_factory=list)
    merged_pairs: list[list[tuple[str, str, int]]] = field(default_factory=list)
    upserted_signals: list[dict] = field(default_factory=list)
    snapshots: list[dict] = field(default_factory=list)
    partner_freqs: dict[str, dict[str, float]] = field(default_factory=dict)

    def append_git_commits(self, commits: list[CommitRecord]) -> None:
        self.appended_commits.append(commits)

    def rebuild_defect_corpus(self, commits: list[CommitRecord]) -> None:
        self.rebuilt_defect_batches.append(commits)

    def merge_cochange_pairs(self, pairs: list[tuple[str, str, int]]) -> None:
        self.merged_pairs.append(pairs)

    def partner_frequencies(self, file_path: str) -> dict[str, float]:
        return self.partner_freqs.get(file_path, {})

    def upsert_file_signal(
        self,
        *,
        file_path: str,
        churn_score: float,
        cochange_entropy: float,
        generated_kind: str | None,
    ) -> None:
        self.upserted_signals.append(
            {
                "file_path": file_path,
                "churn_score": churn_score,
                "cochange_entropy": cochange_entropy,
                "generated_kind": generated_kind,
            }
        )

    def snapshot_file_signal(self, **kwargs) -> None:
        self.snapshots.append(kwargs)

    def latest_ingested_sha(self) -> str | None:
        return None


def test_git_ingestion_uses_store_boundary_for_truth_and_derived_writes():
    store = _FakeStore()
    ingestion = GitIngestion(store)
    signal = FileSignal(
        file_path="src/migrations/001_auth.py",
        churn_count=1,
        churn_score=0.8,
        cochange_entropy=0.0,
        generated_kind="scaffolded",
    )

    original = GitIngestion._compute_stored_cochange_entropy
    try:
        GitIngestion._compute_stored_cochange_entropy = lambda self, file_path, generated_kind=None: 0.0
        from chips.harvester.ingestion import GitReader

        original_compute = GitReader._compute_file_signals
        GitReader._compute_file_signals = lambda *args, **kwargs: [signal]
        try:
            commits = [_commit("abc123", [signal.file_path])]
            ingestion.ingest_commits(commits)
        finally:
            GitReader._compute_file_signals = original_compute
    finally:
        GitIngestion._compute_stored_cochange_entropy = original

    assert store.appended_commits == [[commits[0]]]
    assert store.rebuilt_defect_batches == [[commits[0]]]
    assert store.upserted_signals == [
        {
            "file_path": signal.file_path,
            "churn_score": 0.8,
            "cochange_entropy": 0.0,
            "generated_kind": "scaffolded",
        }
    ]
    assert store.snapshots[0]["basis_sha"] == "abc123"
    assert store.snapshots[0]["generated_kind"] == "scaffolded"
    assert store.snapshots[0]["fragility_complete"] is False
    assert store.snapshots[0]["fragility_inputs_missing"] == ["defect_history_count"]


def test_postgres_store_latest_ingested_sha_reads_truth_table():
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = ("sha-last",)

    store = PostgresHarvesterStore(conn)

    assert store.latest_ingested_sha() == "sha-last"
    assert "FROM cortex_git_commits" in conn.execute.call_args.args[0]


def test_daemon_reads_latest_sha_through_store_boundary():
    conn = MagicMock()
    embedder = MagicMock()
    store = MagicMock()
    store.latest_ingested_sha.return_value = "prev-sha"

    from unittest.mock import patch

    with patch("chips.harvester.daemon.GitReader") as mock_reader_cls:
        mock_reader_cls.return_value.commits_since.return_value = []
        daemon = HarvesterDaemon(conn, embedder, repo_path=".", harvester_store=store)
        assert daemon.run_once() == 0

    store.latest_ingested_sha.assert_called_once_with()
    mock_reader_cls.return_value.commits_since.assert_called_once()
