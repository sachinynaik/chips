"""Tests for FindingsExtractor — 100% TDD, written before the source."""
from __future__ import annotations

from chips.harvester.enrichment.models import EnrichmentResult
from chips.harvester.findings import extract_findings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _security(severity="HIGH", line=1, **extra):
    return {"severity": severity, "line": line, "test_id": "B001",
            "message": "msg", "file": "f.py", "confidence": "HIGH",
            "test_name": "tn", **extra}


def _dead_code(confidence=80, **extra):
    return {"confidence": confidence, "name": "fn", "file": "f.py",
            "line": 1, "type": "function", **extra}


def _api(name="func", **extra):
    return {"name": name, "file": "f.py", "change_type": "added", **extra}


def _arch(**extra):
    return {"from_module": "a", "to_module": "b", "rule": "r", **extra}


def _clone(lines=10, **extra):
    return {"lines": lines, "tokens": 50, "instances": [], **extra}


def _type_error(file="f.py", line=1, **extra):
    return {"file": file, "line": line, "message": "err", **extra}


def _semgrep(rule_id="r1", **extra):
    return {"rule_id": rule_id, "file": "f.py", "line": 1, **extra}


def _ownership(codeowners_available=True, cross_team=False, owners=None, **extra):
    return {
        "codeowners_available": codeowners_available,
        "cross_team_change": cross_team,
        "all_owners": owners or ["@team-a"],
        "owners_by_file": {"f.py": ["@team-a"]},
        **extra,
    }


def _line_coverage(files: dict | None = None, available: bool = True):
    """Build a line_coverage dict.

    files = {path: {"changed_lines_coverage_pct": float, "changed_lines_missing": int}}
    """
    base: dict = {"coverage_available": available}
    if files:
        base["files"] = files
    return base


# ===========================================================================
# Empty input
# ===========================================================================

def test_empty_enrichment_returns_empty_dict():
    assert extract_findings(EnrichmentResult()) == {}


def test_all_empty_lists_return_empty_dict():
    e = EnrichmentResult(
        security_findings=[],
        dead_code_findings=[],
        api_surface_findings=[],
        architecture_violations=[],
        clone_findings=[],
        type_errors=[],
        semgrep_findings=[],
    )
    assert extract_findings(e) == {}


# ===========================================================================
# Security findings
# ===========================================================================

def test_security_key_present_when_findings_exist():
    e = EnrichmentResult(security_findings=[_security()])
    result = extract_findings(e)
    assert "security" in result


def test_security_capped_at_10():
    findings = [_security(line=i) for i in range(11)]
    e = EnrichmentResult(security_findings=findings)
    result = extract_findings(e)
    assert len(result["security"]) == 10


def test_security_sorted_high_before_medium_before_low():
    findings = [
        _security(severity="LOW", line=1),
        _security(severity="HIGH", line=2),
        _security(severity="MEDIUM", line=3),
    ]
    e = EnrichmentResult(security_findings=findings)
    result = extract_findings(e)
    severities = [f["severity"] for f in result["security"]]
    assert severities == ["HIGH", "MEDIUM", "LOW"]


def test_security_same_severity_sorted_by_line_asc():
    findings = [
        _security(severity="HIGH", line=5),
        _security(severity="HIGH", line=2),
        _security(severity="HIGH", line=8),
    ]
    e = EnrichmentResult(security_findings=findings)
    result = extract_findings(e)
    lines = [f["line"] for f in result["security"]]
    assert lines == [2, 5, 8]


def test_security_all_fields_preserved():
    f = _security(severity="MEDIUM", line=42, test_id="B602",
                  message="shell=True", file="run.py", confidence="HIGH",
                  test_name="subprocess_popen_with_shell_equals_true")
    e = EnrichmentResult(security_findings=[f])
    result = extract_findings(e)
    assert result["security"][0] == f


def test_security_empty_no_key():
    e = EnrichmentResult(security_findings=[])
    assert "security" not in extract_findings(e)


# ===========================================================================
# Dead code findings
# ===========================================================================

def test_dead_code_key_present_when_findings_exist():
    e = EnrichmentResult(dead_code_findings=[_dead_code()])
    assert "dead_code" in extract_findings(e)


def test_dead_code_sorted_by_confidence_desc():
    findings = [_dead_code(confidence=60), _dead_code(confidence=90),
                _dead_code(confidence=75)]
    e = EnrichmentResult(dead_code_findings=findings)
    result = extract_findings(e)
    confs = [f["confidence"] for f in result["dead_code"]]
    assert confs == [90, 75, 60]


def test_dead_code_capped_at_10():
    findings = [_dead_code(confidence=i) for i in range(11)]
    e = EnrichmentResult(dead_code_findings=findings)
    result = extract_findings(e)
    assert len(result["dead_code"]) == 10


def test_dead_code_all_fields_preserved():
    f = _dead_code(confidence=80, name="unused_fn", file="util.py",
                   line=99, type="function")
    e = EnrichmentResult(dead_code_findings=[f])
    result = extract_findings(e)
    assert result["dead_code"][0] == f


def test_dead_code_empty_no_key():
    e = EnrichmentResult(dead_code_findings=[])
    assert "dead_code" not in extract_findings(e)


# ===========================================================================
# API surface findings
# ===========================================================================

def test_api_surface_key_present_when_findings_exist():
    e = EnrichmentResult(api_surface_findings=[_api()])
    assert "api_surface" in extract_findings(e)


def test_api_surface_capped_at_20():
    findings = [_api(name=f"fn_{i}") for i in range(21)]
    e = EnrichmentResult(api_surface_findings=findings)
    result = extract_findings(e)
    assert len(result["api_surface"]) == 20


def test_api_surface_no_reordering():
    findings = [_api(name=f"fn_{i}") for i in [3, 1, 2]]
    e = EnrichmentResult(api_surface_findings=findings)
    result = extract_findings(e)
    names = [f["name"] for f in result["api_surface"]]
    assert names == ["fn_3", "fn_1", "fn_2"]


def test_api_surface_empty_no_key():
    e = EnrichmentResult(api_surface_findings=[])
    assert "api_surface" not in extract_findings(e)


# ===========================================================================
# Architecture violations
# ===========================================================================

def test_architecture_violations_key_present():
    e = EnrichmentResult(architecture_violations=[_arch()])
    assert "architecture_violations" in extract_findings(e)


def test_architecture_violations_no_cap_15_included():
    findings = [_arch(rule=f"rule_{i}") for i in range(15)]
    e = EnrichmentResult(architecture_violations=findings)
    result = extract_findings(e)
    assert len(result["architecture_violations"]) == 15


def test_architecture_violations_empty_no_key():
    e = EnrichmentResult(architecture_violations=[])
    assert "architecture_violations" not in extract_findings(e)


# ===========================================================================
# Clone findings
# ===========================================================================

def test_clones_key_present_when_findings_exist():
    e = EnrichmentResult(clone_findings=[_clone()])
    assert "clones" in extract_findings(e)


def test_clones_sorted_by_lines_desc():
    findings = [_clone(lines=5), _clone(lines=20), _clone(lines=10)]
    e = EnrichmentResult(clone_findings=findings)
    result = extract_findings(e)
    lines = [f["lines"] for f in result["clones"]]
    assert lines == [20, 10, 5]


def test_clones_capped_at_5():
    findings = [_clone(lines=i) for i in range(6)]
    e = EnrichmentResult(clone_findings=findings)
    result = extract_findings(e)
    assert len(result["clones"]) == 5


def test_clones_empty_no_key():
    e = EnrichmentResult(clone_findings=[])
    assert "clones" not in extract_findings(e)


# ===========================================================================
# Ownership
# ===========================================================================

def test_ownership_key_present_when_codeowners_available_true():
    e = EnrichmentResult(ownership=_ownership(codeowners_available=True))
    assert "ownership" in extract_findings(e)


def test_ownership_stores_cross_team_and_all_owners():
    e = EnrichmentResult(ownership=_ownership(
        codeowners_available=True, cross_team=True, owners=["@team-a", "@team-b"]))
    result = extract_findings(e)
    assert result["ownership"] == {
        "cross_team_change": True,
        "all_owners": ["@team-a", "@team-b"],
    }


def test_ownership_owners_by_file_not_stored():
    e = EnrichmentResult(ownership=_ownership(codeowners_available=True))
    result = extract_findings(e)
    assert "owners_by_file" not in result["ownership"]


def test_ownership_codeowners_false_no_key():
    e = EnrichmentResult(ownership=_ownership(codeowners_available=False))
    assert "ownership" not in extract_findings(e)


def test_ownership_empty_dict_no_key():
    e = EnrichmentResult(ownership={})
    assert "ownership" not in extract_findings(e)


# ===========================================================================
# Type errors
# ===========================================================================

def test_type_errors_key_present_when_findings_exist():
    e = EnrichmentResult(type_errors=[_type_error()])
    assert "type_errors" in extract_findings(e)


def test_type_errors_capped_at_10():
    findings = [_type_error(line=i) for i in range(11)]
    e = EnrichmentResult(type_errors=findings)
    result = extract_findings(e)
    assert len(result["type_errors"]) == 10


def test_type_errors_empty_no_key():
    e = EnrichmentResult(type_errors=[])
    assert "type_errors" not in extract_findings(e)


# ===========================================================================
# Semgrep findings
# ===========================================================================

def test_semgrep_key_present_when_findings_exist():
    e = EnrichmentResult(semgrep_findings=[_semgrep()])
    assert "semgrep" in extract_findings(e)


def test_semgrep_capped_at_10():
    findings = [_semgrep(rule_id=f"r{i}") for i in range(11)]
    e = EnrichmentResult(semgrep_findings=findings)
    result = extract_findings(e)
    assert len(result["semgrep"]) == 10


def test_semgrep_empty_no_key():
    e = EnrichmentResult(semgrep_findings=[])
    assert "semgrep" not in extract_findings(e)


# ===========================================================================
# Line coverage — uncovered_changes
# ===========================================================================

def test_uncovered_changes_present_when_coverage_available_and_zero_pct():
    lc = _line_coverage(
        files={"src/a.py": {"changed_lines_coverage_pct": 0.0, "changed_lines_missing": 5}},
        available=True,
    )
    e = EnrichmentResult(line_coverage=lc)
    result = extract_findings(e)
    assert "uncovered_changes" in result
    assert result["uncovered_changes"]["src/a.py"]["changed_lines_missing"] == 5
    assert result["uncovered_changes"]["src/a.py"]["changed_lines_coverage_pct"] == 0.0


def test_uncovered_changes_excludes_partially_covered_files():
    lc = _line_coverage(
        files={
            "src/a.py": {"changed_lines_coverage_pct": 0.0, "changed_lines_missing": 3},
            "src/b.py": {"changed_lines_coverage_pct": 50.0, "changed_lines_missing": 2},
        },
        available=True,
    )
    e = EnrichmentResult(line_coverage=lc)
    result = extract_findings(e)
    assert "uncovered_changes" in result
    assert "src/b.py" not in result["uncovered_changes"]
    assert "src/a.py" in result["uncovered_changes"]


def test_uncovered_changes_not_present_when_coverage_unavailable():
    lc = _line_coverage(
        files={"src/a.py": {"changed_lines_coverage_pct": 0.0, "changed_lines_missing": 5}},
        available=False,
    )
    e = EnrichmentResult(line_coverage=lc)
    assert "uncovered_changes" not in extract_findings(e)


def test_uncovered_changes_not_present_when_all_files_covered():
    lc = _line_coverage(
        files={"src/a.py": {"changed_lines_coverage_pct": 100.0, "changed_lines_missing": 0}},
        available=True,
    )
    e = EnrichmentResult(line_coverage=lc)
    assert "uncovered_changes" not in extract_findings(e)


def test_uncovered_changes_not_present_when_line_coverage_empty():
    e = EnrichmentResult(line_coverage={})
    assert "uncovered_changes" not in extract_findings(e)


# ===========================================================================
# Fields that must NOT appear in result
# ===========================================================================

def test_excluded_fields_not_in_result():
    e = EnrichmentResult(
        diff_content="diff --git ...",
        hunk_headers=["@@ -1,5 +1,6 @@"],
        complexity_metrics=[{"file": "f.py", "cyclomatic": 5}],
        community_context="some context",
        similar_commits=[{"sha": "abc"}],
        related_symbols=[{"name": "fn"}],
        scope_memories=[{"id": "1"}],
        cochange_pairs=[{"file": "a.py"}],
        refactoring_type="extract_method",
        cpg_findings=[{"node": "n"}],
        defect_risk={"risk_score": 0.9, "reason": "high churn"},
        type_coverage={"pct": 80.0},
        type_checker_backend="mypy",
    )
    result = extract_findings(e)
    for key in ("diff_content", "hunk_headers", "complexity_metrics",
                "community_context", "similar_commits", "related_symbols",
                "scope_memories", "cochange_pairs", "refactoring_type",
                "cpg_findings", "defect_risk", "type_coverage",
                "type_checker_backend"):
        assert key not in result, f"Excluded key '{key}' found in result"
