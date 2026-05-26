from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
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
    diffs: list[dict] = field(default_factory=list)


@dataclass
class SourceStatus:
    status: Literal["not_configured", "available", "unavailable", "error"]
    detail: str = ""


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
    # tenant_id=None: single-tenant/dev mode only. Production callers must pass a value.
    tenant_id: str | None = None
    data_sources: dict[str, SourceStatus] = field(default_factory=dict)
    schema_version: int = 1
    forbidden_edits: list[str] = field(default_factory=list)
    allowed_edits: list[str] = field(default_factory=list)
