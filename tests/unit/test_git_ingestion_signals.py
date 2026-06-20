from __future__ import annotations

from unittest.mock import MagicMock, patch

from chips.harvester.git_reader import CommitRecord, FileSignal
from chips.harvester.ingestion import GitIngestion
from chips.harvester.storage import PostgresHarvesterStore


def _commit(sha: str, files: list[str]) -> CommitRecord:
    return CommitRecord(
        sha=sha,
        author="test",
        committed_at="2026-06-20T00:00:00+00:00",
        message=f"commit {sha}",
        files_changed=files,
    )


def test_upsert_file_signals_persists_generated_kind_and_snapshot():
    store = PostgresHarvesterStore.__new__(PostgresHarvesterStore)
    store.partner_frequencies = lambda file_path: {}
    store.upsert_file_signal = MagicMock()
    store.snapshot_file_signal = MagicMock()
    ingestion = GitIngestion(store)
    signal = FileSignal(
        file_path="src/migrations/001_auth.py",
        churn_count=1,
        churn_score=0.8,
        cochange_entropy=0.0,
        generated_kind="scaffolded",
    )

    with patch("chips.harvester.ingestion.GitReader._compute_file_signals", return_value=[signal]):
        with patch.object(GitIngestion, "_compute_stored_cochange_entropy", return_value=0.0):
            ingestion._upsert_file_signals([_commit("abc123", [signal.file_path])])

    store.upsert_file_signal.assert_called_once_with(
        file_path=signal.file_path,
        churn_score=0.8,
        cochange_entropy=0.0,
        generated_kind="scaffolded",
    )
    store.snapshot_file_signal.assert_called_once()
    assert store.snapshot_file_signal.call_args.kwargs["basis_sha"] == "abc123"
    assert store.snapshot_file_signal.call_args.kwargs["generated_kind"] == "scaffolded"


def test_snapshot_marks_missing_defect_history_until_v1_2():
    store = PostgresHarvesterStore.__new__(PostgresHarvesterStore)
    store.upsert_file_signal = MagicMock()
    store.snapshot_file_signal = MagicMock()
    store.partner_frequencies = lambda file_path: {}
    ingestion = GitIngestion(store)
    signal = FileSignal(
        file_path="src/auth/service.py",
        churn_count=2,
        churn_score=0.9,
        cochange_entropy=0.6,
        generated_kind=None,
    )

    with patch("chips.harvester.ingestion.GitReader._compute_file_signals", return_value=[signal]):
        with patch.object(GitIngestion, "_compute_stored_cochange_entropy", return_value=0.6):
            ingestion._upsert_file_signals([_commit("def456", [signal.file_path])])

    snapshot_kwargs = store.snapshot_file_signal.call_args.kwargs
    assert snapshot_kwargs["fragility"] == 0.61
    assert snapshot_kwargs["fragility_complete"] is False
    assert snapshot_kwargs["fragility_inputs_present"] == ["churn_score", "cochange_entropy"]
    assert snapshot_kwargs["fragility_inputs_missing"] == ["defect_history_count"]
