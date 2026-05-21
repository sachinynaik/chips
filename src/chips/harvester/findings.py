"""FindingsExtractor — distil EnrichmentResult into a compact structured_findings dict."""
from __future__ import annotations

from chips.harvester.enrichment.models import EnrichmentResult

_SEVERITY_RANK = {"HIGH": 2, "MEDIUM": 1, "LOW": 0}


def extract_findings(enrichment: EnrichmentResult) -> dict:
    """Distil *enrichment* into a compact dict suitable for MemoryRecord.structured_findings.

    Only a curated subset of signals is included; all excluded fields are silently dropped.
    Returns ``{}`` when every included signal is empty / unavailable.
    """
    result: dict = {}

    # ------------------------------------------------------------------
    # security_findings → "security"
    # Sort: severity desc (HIGH>MEDIUM>LOW), then line asc. Cap at 10.
    # ------------------------------------------------------------------
    if enrichment.security_findings:
        sorted_sec = sorted(
            enrichment.security_findings,
            key=lambda f: (-_SEVERITY_RANK.get(f.get("severity", "LOW"), 0),
                           f.get("line", 0)),
        )
        result["security"] = sorted_sec[:10]

    # ------------------------------------------------------------------
    # dead_code_findings → "dead_code"
    # Sort: confidence desc. Cap at 10.
    # ------------------------------------------------------------------
    if enrichment.dead_code_findings:
        sorted_dc = sorted(
            enrichment.dead_code_findings,
            key=lambda f: -f.get("confidence", 0),
        )
        result["dead_code"] = sorted_dc[:10]

    # ------------------------------------------------------------------
    # api_surface_findings → "api_surface"
    # No reordering. Cap at 20.
    # ------------------------------------------------------------------
    if enrichment.api_surface_findings:
        result["api_surface"] = enrichment.api_surface_findings[:20]

    # ------------------------------------------------------------------
    # architecture_violations → "architecture_violations"
    # No cap — violations are always few.
    # ------------------------------------------------------------------
    if enrichment.architecture_violations:
        result["architecture_violations"] = list(enrichment.architecture_violations)

    # ------------------------------------------------------------------
    # clone_findings → "clones"
    # Sort: lines desc. Cap at 5.
    # ------------------------------------------------------------------
    if enrichment.clone_findings:
        sorted_cl = sorted(
            enrichment.clone_findings,
            key=lambda f: -f.get("lines", 0),
        )
        result["clones"] = sorted_cl[:5]

    # ------------------------------------------------------------------
    # ownership → "ownership"
    # Only when codeowners_available == True.
    # Store only cross_team_change + all_owners.
    # ------------------------------------------------------------------
    own = enrichment.ownership
    if own and own.get("codeowners_available") is True:
        result["ownership"] = {
            "cross_team_change": own.get("cross_team_change", False),
            "all_owners": own.get("all_owners", []),
        }

    # ------------------------------------------------------------------
    # type_errors → "type_errors"
    # No reordering. Cap at 10.
    # ------------------------------------------------------------------
    if enrichment.type_errors:
        result["type_errors"] = enrichment.type_errors[:10]

    # ------------------------------------------------------------------
    # semgrep_findings → "semgrep"
    # No reordering. Cap at 10.
    # ------------------------------------------------------------------
    if enrichment.semgrep_findings:
        result["semgrep"] = enrichment.semgrep_findings[:10]

    # ------------------------------------------------------------------
    # line_coverage → "uncovered_changes"
    # Only when coverage_available == True.
    # Only files where changed_lines_coverage_pct == 0.0 (and not None).
    # ------------------------------------------------------------------
    lc = enrichment.line_coverage
    if lc and lc.get("coverage_available") is True:
        files = lc.get("files", {})
        uncovered = {
            path: {
                "changed_lines_missing": info.get("changed_lines_missing", 0),
                "changed_lines_coverage_pct": info.get("changed_lines_coverage_pct"),
            }
            for path, info in files.items()
            if info.get("changed_lines_coverage_pct") is not None
            and info["changed_lines_coverage_pct"] == 0.0
        }
        if uncovered:
            result["uncovered_changes"] = uncovered

    return result
