from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class AnalyzerStatus(str, Enum):
    """Outcome of a single enrichment analyzer run.

    CHIPS principle "Evidence > Guessing": a tool that did not run (not
    installed, crashed, timed out) must NOT read as "no findings = clean".
    Consumers can branch on this to distinguish a genuine clean result
    (``ok``) from a non-result.
    """

    OK = "ok"
    NOT_INSTALLED = "not_installed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    SKIPPED = "skipped"


@dataclass
class EnrichmentResult:
    # Layer 1 — static analysis
    diff_content: str = ""
    hunk_headers: list[str] = field(default_factory=list)
    complexity_metrics: list[dict] = field(default_factory=list)
    semgrep_findings: list[dict] = field(default_factory=list)
    # Layer 1 — type checker (configurable backend)
    type_errors: list[dict] = field(default_factory=list)
    type_coverage: dict = field(default_factory=dict)
    type_checker_backend: str = "none"
    # Layer 1 — API surface (griffe)
    api_surface_findings: list[dict] = field(default_factory=list)
    # Layer 1 — dead code (vulture)
    dead_code_findings: list[dict] = field(default_factory=list)
    # Layer 1 — security (bandit)
    security_findings: list[dict] = field(default_factory=list)
    # Layer 1 — test line coverage (coverage.py reader)
    line_coverage: dict = field(default_factory=dict)
    # Layer 1 — architecture violations (import-linter)
    architecture_violations: list[dict] = field(default_factory=list)
    # Layer 1 — clone detection (jscpd)
    clone_findings: list[dict] = field(default_factory=list)
    # Layer 1 — ownership (CODEOWNERS)
    ownership: dict = field(default_factory=dict)
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
    # Per-analyzer run status (AnalyzerStatus values keyed by analyzer name).
    # Empty for analyzers that did not run or were not wired. Lets consumers
    # tell a genuine clean result (status "ok") from a non-result.
    analyzer_status: dict[str, str] = field(default_factory=dict)
