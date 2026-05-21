from __future__ import annotations
import json
from uuid import UUID

import psycopg
from pgvector.psycopg import register_vector

from chips.memory.models import MemoryRecord, MemoryType

__all__ = ["MemoryRepository", "MemoryRecord", "MemoryType"]


class MemoryRepository:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn
        register_vector(conn)

    def insert(self, record: MemoryRecord) -> UUID:
        row = self._conn.execute(
            """
            INSERT INTO cortex_memories
                (type, scope, content, tags, evidence_refs, confidence,
                 source, author, embedding, tenant_id, structured_findings)
            VALUES
                (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s::jsonb)
            RETURNING id
            """,
            (
                str(record.type),
                record.scope,
                record.content,
                record.tags,
                json.dumps(record.evidence_refs),
                record.confidence,
                record.source,
                record.author,
                record.embedding,
                record.tenant_id,
                json.dumps(record.structured_findings),
            ),
        ).fetchone()
        assert row is not None
        return row[0]

    def get(self, memory_id: UUID) -> MemoryRecord | None:
        row = self._conn.execute(
            """
            SELECT id, type, scope, content, tags, evidence_refs,
                   confidence, source, author, created_at, updated_at,
                   archived_at, tenant_id, embedding, structured_findings
            FROM cortex_memories
            WHERE id = %s AND archived_at IS NULL
            """,
            (memory_id,),
        ).fetchone()
        return self._row_to_record(row) if row else None

    def archive(self, memory_id: UUID) -> None:
        self._conn.execute(
            "UPDATE cortex_memories SET archived_at = now() WHERE id = %s",
            (memory_id,),
        )

    def list_by_scope(self, scope: str) -> list[MemoryRecord]:
        rows = self._conn.execute(
            """
            SELECT id, type, scope, content, tags, evidence_refs,
                   confidence, source, author, created_at, updated_at,
                   archived_at, tenant_id, embedding, structured_findings
            FROM cortex_memories
            WHERE scope = %s AND archived_at IS NULL
            ORDER BY created_at DESC
            """,
            (scope,),
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def semantic_search(
        self,
        query_embedding: list[float],
        limit: int = 10,
        scope: str | None = None,
    ) -> list[MemoryRecord]:
        if scope:
            rows = self._conn.execute(
                """
                SELECT id, type, scope, content, tags, evidence_refs,
                       confidence, source, author, created_at, updated_at,
                       archived_at, tenant_id, embedding, structured_findings
                FROM cortex_memories
                WHERE embedding IS NOT NULL
                  AND archived_at IS NULL
                  AND scope = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (scope, query_embedding, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT id, type, scope, content, tags, evidence_refs,
                       confidence, source, author, created_at, updated_at,
                       archived_at, tenant_id, embedding, structured_findings
                FROM cortex_memories
                WHERE embedding IS NOT NULL
                  AND archived_at IS NULL
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (query_embedding, limit),
            ).fetchall()
        return [self._row_to_record(r) for r in rows]

    @staticmethod
    def _row_to_record(row: tuple) -> MemoryRecord:
        (
            id_, type_, scope, content, tags, evidence_refs,
            confidence, source, author, created_at, updated_at,
            archived_at, tenant_id, embedding, structured_findings_,
        ) = row
        return MemoryRecord(
            id=id_,
            type=MemoryType(type_),
            scope=scope,
            content=content,
            tags=list(tags) if tags else [],
            evidence_refs=evidence_refs if evidence_refs else [],
            confidence=confidence,
            source=source,
            author=author,
            created_at=created_at,
            updated_at=updated_at,
            archived_at=archived_at,
            tenant_id=tenant_id,
            embedding=list(embedding) if embedding is not None else None,
            structured_findings=structured_findings_ if structured_findings_ else {},
        )
