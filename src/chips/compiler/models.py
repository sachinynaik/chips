from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class RankedSignal:
    item_id: str
    item_type: str
    score: float
    signal_breakdown: dict


@dataclass
class RetrievedItems:
    memories: list[dict] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    traces: list[dict] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    diffs: list[str] = field(default_factory=list)


@dataclass
class ContextBrief:
    brief_id: UUID
    task: str
    scope: str | None
    generated_at: datetime
    latency_ms: int
    task_kind: str
    retrieved: RetrievedItems
    ranked_signals: list[RankedSignal]
    hard_constraints: list[str]
    compressed_context: str
    forbidden_edits: list[str] = field(default_factory=list)
    allowed_edits: list[str] = field(default_factory=list)
