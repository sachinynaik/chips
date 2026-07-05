from __future__ import annotations

import json
from uuid import UUID

import psycopg

from chips.compiler.models import ConstraintCandidate, QueuedConstraintCandidate
from chips.tenant import build_tenant_scope

_SELECT_COLS = (
    "id, tenant_id, scope, claim, mechanism, cited_evidence, source_brief_id, "
    "source_hypothesis_id, proposed_kind, proposed_target, status, "
    "promoted_constraint_id, created_at, reviewed_at"
)


class ConstraintCandidateRepository:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def enqueue(self, candidate: ConstraintCandidate) -> UUID:
        existing = self._conn.execute(
            """
            SELECT id
            FROM cortex_constraint_candidates
            WHERE source_brief_id = %s AND source_hypothesis_id = %s
            """,
            (str(candidate.source_brief_id), candidate.source_hypothesis_id),
        ).fetchone()
        if existing is not None:
            return UUID(str(existing[0]))

        row = self._conn.execute(
            """
            INSERT INTO cortex_constraint_candidates (
                tenant_id, scope, claim, mechanism, cited_evidence,
                source_brief_id, source_hypothesis_id, proposed_kind, proposed_target
            )
            VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s::jsonb)
            RETURNING id
            """,
            (
                candidate.tenant_id,
                candidate.scope,
                candidate.claim,
                candidate.mechanism,
                json.dumps(candidate.cited_evidence),
                str(candidate.source_brief_id),
                candidate.source_hypothesis_id,
                candidate.proposed_kind,
                json.dumps(candidate.proposed_target),
            ),
        ).fetchone()
        self._conn.commit()
        assert row is not None
        return UUID(str(row[0]))

    def list(
        self,
        *,
        scope: str | None = None,
        status: str = "pending",
        tenant_id: str | None = None,
    ) -> list[QueuedConstraintCandidate]:
        conditions = ["status = %s"]
        params: list[object] = [status]
        if scope is not None:
            conditions.append("scope = %s")
            params.append(scope)
        scoped = build_tenant_scope(conditions, params, tenant_id)
        rows = self._conn.execute(  # type: ignore[arg-type]
            f"SELECT {_SELECT_COLS} FROM cortex_constraint_candidates "
            f"WHERE {' AND '.join(scoped.conditions)} "
            f"ORDER BY created_at ASC, id ASC",
            tuple(scoped.params),
        ).fetchall()
        return [self._row_to_candidate(r) for r in rows]

    def review(
        self,
        candidate_id: UUID,
        *,
        resolution: str,
        promoted_constraint_id: UUID | None = None,
        tenant_id: str | None = None,
    ) -> bool:
        scoped = build_tenant_scope(["id = %s"], [str(candidate_id)], tenant_id)
        result = self._conn.execute(  # type: ignore[arg-type]
            f"""
            UPDATE cortex_constraint_candidates
            SET status = %s,
                promoted_constraint_id = %s,
                reviewed_at = now()
            WHERE {' AND '.join(scoped.conditions)}
            """,
            (resolution, str(promoted_constraint_id) if promoted_constraint_id else None, *scoped.params),
        )
        self._conn.commit()
        return result.rowcount > 0

    @staticmethod
    def _row_to_candidate(r) -> QueuedConstraintCandidate:
        return QueuedConstraintCandidate(
            id=UUID(str(r[0])),
            tenant_id=str(r[1]) if r[1] else None,
            scope=r[2],
            claim=r[3],
            mechanism=r[4],
            cited_evidence=list(r[5] or []),
            source_brief_id=UUID(str(r[6])),
            source_hypothesis_id=r[7],
            proposed_kind=r[8],
            proposed_target=r[9] or {},
            status=r[10],
            promoted_constraint_id=UUID(str(r[11])) if r[11] else None,
            created_at=r[12],
            reviewed_at=r[13],
        )
