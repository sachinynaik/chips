"""Phase-3 verifier — STEP 1 skeleton (shadow-only, no rule yet).

Pure plumbing: labels every decision-log row with a NULL ``verifier_outcome``
as ``{"status": "unknown", "reason": "verifier_skeleton_no_rule"}``. Commits to
ZERO product decisions — the durability/outcome rule is a later step. Nothing
downstream consumes these labels; do not wire this into reward/composite_reward.

Deterministic, replayable, idempotent, no LLM/network/randomness: run_once
always processes rows in (created_at ASC, id ASC) order and a second run_once
labels 0 rows once all NULLs are filled.

Design: docs/design_docs/phase3_verifier_design.md.
"""
from __future__ import annotations

import psycopg

from chips.compiler.decision_log_repository import (
    _SELECT_COLS,
    DecisionLogRepository,
)
from chips.compiler.models import DecisionLogEntry
from chips.tenant import build_tenant_scope

_UNKNOWN_OUTCOME = {"status": "unknown", "reason": "verifier_skeleton_no_rule"}


class Verifier:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn
        self._repo = DecisionLogRepository(conn)

    def run_once(self, tenant_id: str | None = None) -> int:
        """Label every decision-log row with a NULL verifier_outcome.

        Tenant-scoped, deterministic order. Returns the count newly labeled.
        """
        count = 0
        for entry in self._unlabeled(tenant_id=tenant_id):
            outcome = self._label(entry)
            if self._repo.set_verifier_outcome(
                entry.id, outcome, tenant_id=tenant_id
            ):
                count += 1
        return count

    def _unlabeled(self, tenant_id: str | None = None) -> list[DecisionLogEntry]:
        scoped = build_tenant_scope(["verifier_outcome IS NULL"], [], tenant_id)
        rows = self._conn.execute(  # type: ignore[arg-type]
            f"SELECT {_SELECT_COLS} FROM cortex_decision_log "
            f"WHERE {' AND '.join(scoped.conditions)} "
            f"ORDER BY created_at ASC, id ASC",
            tuple(scoped.params),
        ).fetchall()
        return [DecisionLogRepository._row_to_entry(r) for r in rows]

    def _label(self, entry: DecisionLogEntry) -> dict:
        """STEP 1: no rule yet. Always returns the fixed 'unknown' label."""
        return dict(_UNKNOWN_OUTCOME)
