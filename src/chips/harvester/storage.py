from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

import psycopg

from chips.harvester.defect_corpus import extract_defect_evidence
from chips.harvester.git_reader import CommitRecord


TRUTH_TABLES = ("cortex_git_commits",)
DERIVED_TABLES = (
    "cortex_defect_corpus",
    "cortex_cochange_pairs",
    "cortex_file_signals",
    "cortex_file_signal_snapshots",
)


def is_truth_table(table_name: str) -> bool:
    return table_name in TRUTH_TABLES


def is_derived_table(table_name: str) -> bool:
    return table_name in DERIVED_TABLES


class HarvesterStore(Protocol):
    def append_git_commits(self, commits: list[CommitRecord]) -> None: ...

    def rebuild_defect_corpus(self, commits: list[CommitRecord]) -> None: ...

    def merge_cochange_pairs(self, pairs: list[tuple[str, str, int]]) -> None: ...

    def partner_frequencies(self, file_path: str) -> Mapping[str, float]: ...

    def upsert_file_signal(
        self,
        *,
        file_path: str,
        churn_score: float,
        cochange_entropy: float,
        generated_kind: str | None,
    ) -> None: ...

    def snapshot_file_signal(
        self,
        *,
        basis_sha: str,
        file_path: str,
        churn_score: float,
        cochange_entropy: float,
        generated_kind: str | None,
        fragility: float,
        fragility_complete: bool,
        fragility_inputs_present: list[str],
        fragility_inputs_missing: list[str],
    ) -> None: ...

    def latest_ingested_sha(self) -> str | None: ...


class PostgresHarvesterStore:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def append_git_commits(self, commits: list[CommitRecord]) -> None:
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

    def rebuild_defect_corpus(self, commits: list[CommitRecord]) -> None:
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

    def merge_cochange_pairs(self, pairs: list[tuple[str, str, int]]) -> None:
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

    def partner_frequencies(self, file_path: str) -> Mapping[str, float]:
        rows = self._conn.execute(
            """
            SELECT file_a, file_b, frequency
            FROM cortex_cochange_pairs
            WHERE file_a = %s OR file_b = %s
            """,
            (file_path, file_path),
        ).fetchall()
        partner_frequencies: dict[str, float] = {}
        for file_a, file_b, frequency in rows:
            partner = file_b if file_a == file_path else file_a
            partner_frequencies[partner] = float(frequency)
        return partner_frequencies

    def upsert_file_signal(
        self,
        *,
        file_path: str,
        churn_score: float,
        cochange_entropy: float,
        generated_kind: str | None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO cortex_file_signals
                (file_path, churn_score, cochange_entropy, generated_kind, last_changed_at, updated_at)
            VALUES (%s, %s, %s, %s, now(), now())
            ON CONFLICT (file_path)
            DO UPDATE SET
                churn_score = cortex_file_signals.churn_score + EXCLUDED.churn_score,
                cochange_entropy = EXCLUDED.cochange_entropy,
                generated_kind = EXCLUDED.generated_kind,
                last_changed_at = now(),
                updated_at = now()
            """,
            (file_path, churn_score, cochange_entropy, generated_kind),
        )

    def snapshot_file_signal(
        self,
        *,
        basis_sha: str,
        file_path: str,
        churn_score: float,
        cochange_entropy: float,
        generated_kind: str | None,
        fragility: float,
        fragility_complete: bool,
        fragility_inputs_present: list[str],
        fragility_inputs_missing: list[str],
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO cortex_file_signal_snapshots (
                basis_sha,
                file_path,
                churn_score,
                cochange_entropy,
                generated_kind,
                fragility,
                fragility_complete,
                fragility_inputs_present,
                fragility_inputs_missing,
                captured_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now())
            """,
            (
                basis_sha,
                file_path,
                churn_score,
                cochange_entropy,
                generated_kind,
                fragility,
                fragility_complete,
                fragility_inputs_present,
                fragility_inputs_missing,
            ),
        )

    def latest_ingested_sha(self) -> str | None:
        row = self._conn.execute(
            """
            SELECT sha FROM cortex_git_commits
            ORDER BY committed_at DESC
            LIMIT 1
            """
        ).fetchone()
        return row[0] if row else None
