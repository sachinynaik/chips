"""Tests for _extract_brief_signals in builder.py."""
from __future__ import annotations

from chips.compiler.builder import _extract_brief_signals


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mem(structured_findings: dict | None = None, **kwargs) -> dict:
    """Build a minimal memory dict."""
    result = {"type": "lesson", "content": "some content"}
    result.update(kwargs)
    if structured_findings is not None:
        result["structured_findings"] = structured_findings
    return result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_empty_memories_returns_empty_lists():
    hard, soft = _extract_brief_signals([])
    assert hard == []
    assert soft == []


def test_memories_without_findings_returns_empty():
    memories = [
        _mem(),                                          # no structured_findings key
        {"type": "decision", "content": "use postgres"}, # also no key
    ]
    hard, soft = _extract_brief_signals(memories)
    assert hard == []
    assert soft == []


def test_high_security_goes_to_hard():
    findings = {"security": [
        {"test_id": "B602", "severity": "HIGH", "message": "shell injection", "line": 10, "file": "app.py"}
    ]}
    hard, soft = _extract_brief_signals([_mem(findings)])

    assert len(hard) == 1
    assert "B602" in hard[0]
    assert "shell injection" in hard[0]
    assert soft == []


def test_medium_security_goes_to_hard():
    findings = {"security": [
        {"test_id": "B101", "severity": "MEDIUM", "message": "assert used", "line": 5, "file": "utils.py"}
    ]}
    hard, soft = _extract_brief_signals([_mem(findings)])

    assert len(hard) == 1
    assert "B101" in hard[0]
    assert soft == []


def test_low_security_goes_to_soft():
    findings = {"security": [
        {"test_id": "B404", "severity": "LOW", "message": "subprocess import", "line": 1, "file": "run.py"}
    ]}
    hard, soft = _extract_brief_signals([_mem(findings)])

    assert hard == []
    assert len(soft) == 1
    assert "B404" in soft[0][1]


def test_architecture_violation_goes_to_hard():
    findings = {"architecture_violations": [
        {"contract": "no-db-in-api", "message": "API layer imports DB directly"}
    ]}
    hard, soft = _extract_brief_signals([_mem(findings)])

    assert len(hard) == 1
    assert "no-db-in-api" in hard[0]
    assert "API layer imports DB directly" in hard[0]
    assert soft == []


def test_dead_code_goes_to_soft():
    findings = {"dead_code": [
        {"type": "function", "name": "old_util", "file": "utils.py", "confidence": 80}
    ]}
    hard, soft = _extract_brief_signals([_mem(findings)])

    assert hard == []
    assert len(soft) == 1
    assert "old_util" in soft[0][1]
    assert "utils.py" in soft[0][1]
    assert "80%" in soft[0][1]


def test_api_surface_goes_to_soft():
    findings = {"api_surface": [
        {"change_type": "removed", "symbol": "MyClass.foo", "details": "parameter dropped"}
    ]}
    hard, soft = _extract_brief_signals([_mem(findings)])

    assert hard == []
    assert len(soft) == 1
    assert "removed" in soft[0][1]
    assert "MyClass.foo" in soft[0][1]
    assert "parameter dropped" in soft[0][1]


def test_clone_goes_to_soft():
    findings = {"clones": [
        {"lines": 15, "file_a": "src/a.py", "file_b": "src/b.py"}
    ]}
    hard, soft = _extract_brief_signals([_mem(findings)])

    assert hard == []
    assert len(soft) == 1
    assert "15" in soft[0][1]
    assert "src/a.py" in soft[0][1]
    assert "src/b.py" in soft[0][1]


def test_type_error_goes_to_soft():
    findings = {"type_errors": [
        {"code": "E203", "line": 42, "message": "incompatible types"}
    ]}
    hard, soft = _extract_brief_signals([_mem(findings)])

    assert hard == []
    assert len(soft) == 1
    assert "E203" in soft[0][1]
    assert "42" in soft[0][1]
    assert "incompatible types" in soft[0][1]


def test_fragility_goes_to_soft():
    findings = {"fragility": {
        "history_count": 2,
        "matched_commits": ["def456", "abc123"],
        "reason": "history_found",
    }}
    hard, soft = _extract_brief_signals([_mem(findings)])

    assert hard == []
    assert len(soft) == 1
    assert "2 prior defect-linked fixes" in soft[0][1]
    assert "abc123" in soft[0][1]
    assert "def456" in soft[0][1]


def test_yield_score_never_becomes_a_brief_finding():
    # Locked invariant (build-brief two-consumers rule): the Yield score is
    # external/demo-only and must NEVER enter the gate-facing brief findings.
    # Fragility is the gate-relevant signal; Yield is not. This locks the
    # mechanism so a future change cannot silently leak Yield into the gate path.
    findings = {
        "yield_score": {"score": 3.2, "mode": "raw", "calibrated": False},
        "fragility": {
            "history_count": 1,
            "matched_commits": ["abc123"],
            "reason": "history_found",
        },
    }
    hard, soft = _extract_brief_signals([_mem(findings)])

    all_text = " ".join(text for _, text in hard + soft).lower()
    assert "yield" not in all_text
    # Fragility still surfaces — it is the gate-relevant signal.
    assert any("prior defect-linked fixes" in text for _, text in soft)


def test_uncovered_changes_goes_to_soft():
    # uncovered_changes is a dict[path → info], not a list
    findings = {"uncovered_changes": {
        "src/chips/memory/repository.py": {"changed_lines_missing": 7, "changed_lines_coverage_pct": 0.0}
    }}
    hard, soft = _extract_brief_signals([_mem(findings)])

    assert hard == []
    assert len(soft) == 1
    assert "repository.py" in soft[0][1]
    assert "7" in soft[0][1]


def test_multiple_memories_findings_aggregated():
    """Findings from two memories are aggregated into the same lists."""
    memory_1 = _mem({"security": [
        {"test_id": "B602", "severity": "HIGH", "message": "shell inj", "line": 1, "file": "a.py"}
    ]})
    memory_2 = _mem({"dead_code": [
        {"type": "class", "name": "OldManager", "file": "mgr.py", "confidence": 90}
    ]})

    hard, soft = _extract_brief_signals([memory_1, memory_2])

    assert len(hard) == 1
    assert "B602" in hard[0]

    assert len(soft) == 1
    assert "OldManager" in soft[0][1]
