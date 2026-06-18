"""Slice 0 (contract §A): soft findings carry stable ``find:<content-hash>`` IDs.

These assert the wiring of ``evidence.finding_evidence_id`` into
``builder._extract_brief_signals`` — IDs derived from normalized finding
*content*, never from position. Pure (no DB).
"""
from __future__ import annotations

import re

from chips.compiler.builder import _extract_brief_signals
from chips.compiler.evidence import finding_evidence_id

_FIND_ID = re.compile(r"^find:[0-9a-f]{12}$")


def _mem(structured_findings: dict) -> dict:
    return {"type": "lesson", "content": "c", "structured_findings": structured_findings}


def test_soft_entries_are_id_text_pairs_with_find_format():
    findings = {"security": [
        {"test_id": "B404", "severity": "LOW", "message": "subprocess import", "line": 1, "file": "run.py"}
    ]}
    _hard, soft = _extract_brief_signals([_mem(findings)])

    assert len(soft) == 1
    find_id, text = soft[0]
    assert _FIND_ID.match(find_id), find_id
    assert "B404" in text


def test_security_id_matches_locked_normalization():
    """ID = hash over {kind, test_id, file, line, message} — severity excluded."""
    findings = {"security": [
        {"test_id": "B404", "severity": "LOW", "message": "subprocess import", "line": 1, "file": "run.py"}
    ]}
    _hard, soft = _extract_brief_signals([_mem(findings)])

    expected = finding_evidence_id({
        "kind": "security",
        "test_id": "B404", "file": "run.py", "line": 1, "message": "subprocess import",
    })
    assert soft[0][0] == expected


def test_severity_change_does_not_change_id():
    """LOW vs (hypothetically) a re-tuned LOW finding hash the same — severity is excluded."""
    base = {"test_id": "B404", "message": "subprocess import", "line": 1, "file": "run.py"}
    _h1, soft1 = _extract_brief_signals([_mem({"security": [{**base, "severity": "LOW"}]})])
    # Same identity fields, different volatile metadata key that is NOT in the normalized set.
    _h2, soft2 = _extract_brief_signals([_mem({"security": [{**base, "severity": "LOW", "confidence": 42}]})])
    assert soft1[0][0] == soft2[0][0]


def test_ids_stable_across_two_builds():
    findings = {"dead_code": [
        {"type": "function", "name": "old_util", "file": "utils.py", "confidence": 80}
    ]}
    _h1, soft1 = _extract_brief_signals([_mem(findings)])
    _h2, soft2 = _extract_brief_signals([_mem(findings)])
    assert soft1[0][0] == soft2[0][0]


def test_ids_are_order_independent():
    """Reordering findings in the input yields the same ID per finding (content-based)."""
    a = {"type": "function", "name": "alpha", "file": "a.py", "confidence": 60}
    b = {"type": "class", "name": "Beta", "file": "b.py", "confidence": 90}
    _h1, soft_ab = _extract_brief_signals([_mem({"dead_code": [a, b]})])
    _h2, soft_ba = _extract_brief_signals([_mem({"dead_code": [b, a]})])

    ids_ab = {fid for fid, _ in soft_ab}
    ids_ba = {fid for fid, _ in soft_ba}
    assert ids_ab == ids_ba


def test_clone_id_is_pair_order_independent():
    """file_a/file_b swapped describe the same clone → same ID (pair is sorted)."""
    _h1, soft1 = _extract_brief_signals([_mem({"clones": [{"lines": 15, "file_a": "a.py", "file_b": "b.py"}]})])
    _h2, soft2 = _extract_brief_signals([_mem({"clones": [{"lines": 15, "file_a": "b.py", "file_b": "a.py"}]})])
    assert soft1[0][0] == soft2[0][0]


def test_different_kinds_do_not_collide():
    """The kind discriminator keeps distinct kinds apart even with overlapping field values."""
    dead = {"dead_code": [{"type": "x", "name": "x", "file": "x"}]}
    typ = {"type_errors": [{"code": "x", "line": "x", "message": "x"}]}
    _h1, soft_dead = _extract_brief_signals([_mem(dead)])
    _h2, soft_typ = _extract_brief_signals([_mem(typ)])
    assert soft_dead[0][0] != soft_typ[0][0]


def test_fragility_id_is_commit_order_independent():
    a = {"fragility": {"history_count": 2, "matched_commits": ["def456", "abc123"], "reason": "history_found"}}
    b = {"fragility": {"history_count": 2, "matched_commits": ["abc123", "def456"], "reason": "history_found"}}

    _h1, soft_a = _extract_brief_signals([_mem(a)])
    _h2, soft_b = _extract_brief_signals([_mem(b)])

    assert soft_a[0][0] == soft_b[0][0]
    expected = finding_evidence_id({
        "kind": "fragility",
        "matched_commits": ["abc123", "def456"],
        "reason": "history_found",
    })
    assert soft_a[0][0] == expected


def test_uncovered_changes_keyed_on_path():
    findings = {"uncovered_changes": {
        "src/chips/memory/repository.py": {"changed_lines_missing": 7, "changed_lines_coverage_pct": 0.0}
    }}
    _hard, soft = _extract_brief_signals([_mem(findings)])
    expected = finding_evidence_id({"kind": "uncovered_changes", "path": "src/chips/memory/repository.py"})
    assert soft[0][0] == expected
    # Missing-line count is excluded — changing it must not change the ID.
    findings2 = {"uncovered_changes": {
        "src/chips/memory/repository.py": {"changed_lines_missing": 99, "changed_lines_coverage_pct": 0.0}
    }}
    _h2, soft2 = _extract_brief_signals([_mem(findings2)])
    assert soft2[0][0] == expected
