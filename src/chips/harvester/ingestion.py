from __future__ import annotations
import psycopg

from chips.compiler.fragility import fragility_inputs, fragility_score
from chips.harvester.git_reader import CommitRecord, GitReader
from chips.harvester.signals import classify_generated_kind, cochange_entropy_for_file
from chips.harvester.storage import HarvesterStore, PostgresHarvesterStore


class GitIngestion:
    def __init__(self, conn: psycopg.Connection | HarvesterStore) -> None:
        if hasattr(conn, "execute"):
            self._store: HarvesterStore = PostgresHarvesterStore(conn)  # type: ignore[arg-type]
        else:
            self._store = conn

    def ingest_commits(self, commits: list[CommitRecord]) -> None:
        if not commits:
            return
        self._upsert_commits(commits)
        self._upsert_defect_corpus(commits)
        self._upsert_cochange_pairs(commits)
        self._upsert_file_signals(commits)

    def rebuild_derived_from_truth(self) -> None:
        commits = self._store.truth_commits()
        self._store.clear_derived_tables()
        for commit in commits:
            self._upsert_defect_corpus([commit])
            self._upsert_cochange_pairs([commit])
            self._upsert_file_signals([commit])

    def _upsert_commits(self, commits: list[CommitRecord]) -> None:
        self._store.append_git_commits(commits)

    def _upsert_cochange_pairs(self, commits: list[CommitRecord]) -> None:
        reader = GitReader.__new__(GitReader)
        pairs = reader._compute_cochange_pairs(commits)
        self._store.merge_cochange_pairs(pairs)

    def _upsert_defect_corpus(self, commits: list[CommitRecord]) -> None:
        self._store.rebuild_defect_corpus_for_shas([commit.sha for commit in commits])

    def _upsert_file_signals(self, commits: list[CommitRecord]) -> None:
        reader = GitReader.__new__(GitReader)
        # Apply file-signal deltas commit-by-commit so replay from cortex_git_commits
        # reconstructs the exact same aggregates and snapshots. Batch-boundary
        # semantics are not stored in truth; per-commit replay is.
        #
        # _upsert_cochange_pairs(commits) has already merged every pair for this batch,
        # so the cochange table is static for the whole loop below: a file's entropy is
        # identical across all its commits. Memoize the read per file_path to kill the
        # N+1 (one partner_frequencies query per (commit, file) → one per distinct file).
        # On spacemate_chat_system this collapsed ~48k reads to a few thousand. The cache
        # is per-call, so per-commit replay (rebuild_derived_from_truth) is unaffected.
        entropy_cache: dict[str, float] = {}
        for commit in commits:
            signals = reader._compute_file_signals([commit])
            for signal in signals:
                generated_kind = signal.generated_kind or classify_generated_kind(signal.file_path)
                cochange_entropy = entropy_cache.get(signal.file_path)
                if cochange_entropy is None:
                    cochange_entropy = self._compute_stored_cochange_entropy(signal.file_path, generated_kind)
                    entropy_cache[signal.file_path] = cochange_entropy
                self._store.upsert_file_signal(
                    file_path=signal.file_path,
                    churn_score=signal.churn_score,
                    cochange_entropy=cochange_entropy,
                    generated_kind=generated_kind,
                )
                self._snapshot_file_signal(
                    basis_sha=commit.sha,
                    file_path=signal.file_path,
                    churn_score=signal.churn_score,
                    cochange_entropy=cochange_entropy,
                    generated_kind=generated_kind,
                )

    def _snapshot_file_signal(
        self,
        *,
        basis_sha: str,
        file_path: str,
        churn_score: float,
        cochange_entropy: float,
        generated_kind: str | None,
    ) -> None:
        fragility = fragility_score(churn_score, cochange_entropy, None)
        inputs = fragility_inputs(churn_score, cochange_entropy, None)
        self._store.snapshot_file_signal(
            basis_sha=basis_sha,
            file_path=file_path,
            churn_score=churn_score,
            cochange_entropy=cochange_entropy,
            generated_kind=generated_kind,
            fragility=fragility,
            fragility_complete=inputs["complete"],
            fragility_inputs_present=inputs["present"],
            fragility_inputs_missing=inputs["missing"],
        )

    def _compute_stored_cochange_entropy(
        self,
        file_path: str,
        generated_kind: str | None = None,
    ) -> float:
        if generated_kind is not None:
            return 0.0
        return cochange_entropy_for_file(file_path, self._store.partner_frequencies(file_path))
