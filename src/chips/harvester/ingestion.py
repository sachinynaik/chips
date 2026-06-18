from __future__ import annotations
import math
import psycopg

from chips.harvester.defect_corpus import extract_defect_evidence
from chips.harvester.git_reader import CommitRecord, GitReader


class GitIngestion:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def ingest_commits(self, commits: list[CommitRecord]) -> None:
        if not commits:
            return
        self._upsert_commits(commits)
        self._upsert_defect_corpus(commits)
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

    def _upsert_defect_corpus(self, commits: list[CommitRecord]) -> None:
        for commit in commits:
            evidence = extract_defect_evidence(commit.message)
            self._conn.execute(
                """
                INSERT INTO cortex_defect_corpus (
                    sha,
                    issue_refs,
                    revert_of_sha,
                    has_bug_keyword,
                    has_defect_keyword,
                    has_hotfix_keyword,
                    has_incident_keyword,
                    captured_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (sha)
                DO UPDATE SET
                    issue_refs = EXCLUDED.issue_refs,
                    revert_of_sha = EXCLUDED.revert_of_sha,
                    has_bug_keyword = EXCLUDED.has_bug_keyword,
                    has_defect_keyword = EXCLUDED.has_defect_keyword,
                    has_hotfix_keyword = EXCLUDED.has_hotfix_keyword,
                    has_incident_keyword = EXCLUDED.has_incident_keyword,
                    captured_at = now()
                """,
                (
                    commit.sha,
                    evidence.issue_refs,
                    evidence.revert_of_sha,
                    evidence.has_bug_keyword,
                    evidence.has_defect_keyword,
                    evidence.has_hotfix_keyword,
                    evidence.has_incident_keyword,
                ),
            )

    def _upsert_file_signals(self, commits: list[CommitRecord]) -> None:
        reader = GitReader.__new__(GitReader)
        signals = reader._compute_file_signals(commits)
        for signal in signals:
            cochange_entropy = self._compute_stored_cochange_entropy(signal.file_path)
            self._conn.execute(
                """
                INSERT INTO cortex_file_signals
                    (file_path, churn_score, cochange_entropy, last_changed_at, updated_at)
                VALUES (%s, %s, %s, now(), now())
                ON CONFLICT (file_path)
                DO UPDATE SET
                    churn_score = cortex_file_signals.churn_score + EXCLUDED.churn_score,
                    cochange_entropy = EXCLUDED.cochange_entropy,
                    last_changed_at = now(),
                    updated_at = now()
                """,
                (signal.file_path, signal.churn_score, cochange_entropy),
            )

    def _compute_stored_cochange_entropy(self, file_path: str) -> float:
        rows = self._conn.execute(
            """
            SELECT file_a, file_b, frequency
            FROM cortex_cochange_pairs
            WHERE file_a = %s OR file_b = %s
            """,
            (file_path, file_path),
        ).fetchall()
        partner_frequencies = [
            float(frequency)
            for file_a, file_b, frequency in rows
            if (file_a == file_path or file_b == file_path) and frequency > 0
        ]
        if len(partner_frequencies) <= 1:
            return 0.0
        total = sum(partner_frequencies)
        if total <= 0:
            return 0.0
        entropy = 0.0
        for value in partner_frequencies:
            probability = value / total
            entropy -= probability * math.log(probability)
        return entropy / math.log(len(partner_frequencies))
