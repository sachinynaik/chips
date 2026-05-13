from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class MemoryType(StrEnum):
    INVARIANT = "invariant"
    DECISION = "decision"
    PITFALL = "pitfall"
    CONTRACT = "contract"
    LESSON = "lesson"


@dataclass
class MemoryRecord:
    type: MemoryType
    scope: str
    content: str
    source: str | None = None
    author: str | None = None
    tags: list[str] = field(default_factory=list)
    evidence_refs: list[dict] = field(default_factory=list)
    confidence: float = 0.8
    embedding: list[float] | None = None
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    archived_at: datetime | None = None
    tenant_id: UUID | None = None
