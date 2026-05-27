"""Phase 1: stable evidence ID scheme — content-hashed finding IDs.

Locks the contract from docs/27_05_phase1_evidence_hypotheses_contract.md §A:
IDs are <kind>:<natural-key>; the natural key is derived from content/identity,
never from position. finding IDs are content hashes so they are stable across
compiles (replacing the positional `finding:{index}`).
"""
from __future__ import annotations

import pytest

from chips.compiler.evidence import (
    finding_content_hash,
    finding_evidence_id,
    make_evidence_id,
)


def test_make_evidence_id_formats_kind_colon_key():
    assert make_evidence_id("mem", "abc-123") == "mem:abc-123"
    assert make_evidence_id("diff", "deadbeef") == "diff:deadbeef"


def test_make_evidence_id_rejects_empty_kind():
    # guards reserved kinds (rule/span) against malformed IDs before they are wired
    with pytest.raises(ValueError):
        make_evidence_id("", "abc")


def test_make_evidence_id_rejects_empty_key():
    with pytest.raises(ValueError):
        make_evidence_id("span", "")


def test_finding_evidence_id_has_find_prefix_and_12_hex_hash():
    eid = finding_evidence_id({"test_id": "B105", "file": "a.py", "line": 4, "message": "x"})
    assert eid.startswith("find:")
    hash_part = eid.split(":", 1)[1]
    assert len(hash_part) == 12
    assert all(c in "0123456789abcdef" for c in hash_part)


def test_finding_id_is_deterministic_for_same_content():
    finding = {"test_id": "B105", "file": "a.py", "line": 4, "message": "x"}
    assert finding_evidence_id(finding) == finding_evidence_id(dict(finding))


def test_finding_id_is_independent_of_key_insertion_order():
    a = {"test_id": "B105", "file": "a.py", "line": 4, "message": "x"}
    b = {"message": "x", "line": 4, "file": "a.py", "test_id": "B105"}
    assert finding_evidence_id(a) == finding_evidence_id(b)


def test_finding_id_distinguishes_distinct_findings():
    a = {"test_id": "B105", "file": "a.py", "line": 4, "message": "x"}
    b = {"test_id": "B105", "file": "a.py", "line": 5, "message": "x"}  # different line
    assert finding_evidence_id(a) != finding_evidence_id(b)


def test_finding_content_hash_handles_nested_and_nonserializable_values():
    # must not raise; deterministic regardless of nested dict ordering
    a = {"meta": {"sev": "HIGH", "rank": 1}, "file": "a.py"}
    b = {"file": "a.py", "meta": {"rank": 1, "sev": "HIGH"}}
    assert finding_content_hash(a) == finding_content_hash(b)
