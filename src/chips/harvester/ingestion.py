from __future__ import annotations
import psycopg

from chips.harvester.git_reader import CommitRecord, GitReader


class GitIngestion:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def ingest_commits(self, commits: list[CommitRecord]) -> None:
        if not commits:
            return
        self._upsert_commits(commits)
        self._upsert_cochange_pairs(commits)
        self._upsert_file_signals(commits)

    def _upsert_commits(self, commits: list[CommitRecord]) -> None:
        for commit in commits:
            self._conn.execute(
                """
                INSERT INTO cortex_git_commits
                    (sha, author, committed_at, message, files_changed)
                VALUES (%s, %s, %s::timestamptz, %s, %s)
                ON CONFLICT (sha) DO NOTHING
                """,
                (
                    commit.sha,
                    commit.author,
                    commit.committed_at,
                    commit.message,
                    commit.files_changed,
                ),
            )

    def _upsert_cochange_pairs(self, commits: list[CommitRecord]) -> None:
        reader = GitReader.__new__(GitReader)
        pairs = reader._compute_cochange_pairs(commits)
        for file_a, file_b, freq in pairs:
            self._conn.execute(
                """
                INSERT INTO cortex_cochange_pairs (file_a, file_b, frequency, last_seen_at)
                VALUES (%s, %s, %s, now())
                ON CONFLICT (file_a, file_b)
                DO UPDATE SET
                    frequency = cortex_cochange_pairs.frequency + EXCLUDED.frequency,
                    last_seen_at = now()
                """,
                (file_a, file_b, freq),
            )

    def _upsert_file_signals(self, commits: list[CommitRecord]) -> None:
        reader = GitReader.__new__(GitReader)
        signals = reader._compute_file_signals(commits)
        for signal in signals:
            self._conn.execute(
                """
                INSERT INTO cortex_file_signals
                    (file_path, churn_score, last_changed_at, updated_at)
                VALUES (%s, %s, now(), now())
                ON CONFLICT (file_path)
                DO UPDATE SET
                    churn_score = cortex_file_signals.churn_score + EXCLUDED.churn_score,
                    last_changed_at = now(),
                    updated_at = now()
                """,
                (signal.file_path, signal.churn_score),
            )
