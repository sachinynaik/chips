from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class EnrichmentResult:
    # Layer 1
    diff_content: str = ""
    hunk_headers: list[str] = field(default_factory=list)
    complexity_metrics: list[dict] = field(default_factory=list)
    semgrep_findings: list[dict] = field(default_factory=list)
    # Layer 2
    similar_commits: list[dict] = field(default_factory=list)
    # Layer 3
    related_symbols: list[dict] = field(default_factory=list)
    community_context: str | None = None
    # Layer 4 stubs
    refactoring_type: str | None = None
    cpg_findings: list[dict] = field(default_factory=list)
    defect_risk: dict = field(default_factory=lambda: {"risk_score": None, "reason": "insufficient_history"})
    # DB
    scope_memories: list[dict] = field(default_factory=list)
    cochange_pairs: list[dict] = field(default_factory=list)
