"""Tests for structured_findings in search_memory (mocked DB, no Docker)."""
from __future__ import annotations
import uuid
from unittest.mock import MagicMock, patch

import pytest

from chips.memory.models import MemoryRecord, MemoryType
from chips.mcp.tools.memory import search_memory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_record(**kwargs) -> MemoryRecord:
    defaults = dict(
        type=MemoryType.LESSON,
        scope="auth",
        content="lesson text",
        structured_findings=kwargs.pop("structured_findings", {}),
    )
    defaults.update(kwargs)
    return MemoryRecord(**defaults)


def _search_with_records(records: list[MemoryRecord]) -> list[dict]:
    """Call search_memory with a mocked repo that returns the given records."""
    conn = MagicMock()
    with patch("chips.mcp.tools.memory.MemoryRepository") as MockRepo:
        instance = MockRepo.return_value
        instance.semantic_search.return_value = records
        results = search_memory(
            conn=conn,
            query_embedding=[0.1] * 4,
            scope=None,
            limit=10,
        )
    return results


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_search_memory_result_includes_structured_findings_key():
    records = [_make_record()]
    results = _search_with_records(records)

    assert len(results) == 1
    assert "structured_findings" in results[0]


def test_search_memory_empty_findings_returns_empty_dict():
    records = [_make_record(structured_findings={})]
    results = _search_with_records(records)

    assert results[0]["structured_findings"] == {}


def test_search_memory_populated_findings_preserved():
    findings = {"security": [{"test_id": "B602", "severity": "HIGH", "line": 10}]}
    records = [_make_record(structured_findings=findings)]
    results = _search_with_records(records)

    assert results[0]["structured_findings"] == findings


def test_search_memory_multiple_records_each_has_findings():
    records = [
        _make_record(structured_findings={"dead_code": [{"name": f"fn_{i}"}]})
        for i in range(3)
    ]
    results = _search_with_records(records)

    assert len(results) == 3
    for result in results:
        assert "structured_findings" in result
        assert "dead_code" in result["structured_findings"]


def test_search_memory_findings_independent_per_record():
    findings_a = {"security": [{"test_id": "B101"}]}
    findings_b = {"clones": [{"file_a": "a.py", "file_b": "b.py", "lines": 5}]}
    findings_c = {}

    records = [
        _make_record(structured_findings=findings_a, content="record A"),
        _make_record(structured_findings=findings_b, content="record B"),
        _make_record(structured_findings=findings_c, content="record C"),
    ]
    results = _search_with_records(records)

    assert results[0]["structured_findings"] == findings_a
    assert results[1]["structured_findings"] == findings_b
    assert results[2]["structured_findings"] == findings_c


def test_search_memory_other_fields_still_present():
    findings = {"type_errors": [{"code": "E001", "line": 3, "message": "bad"}]}
    records = [_make_record(
        scope="payments",
        content="important lesson",
        source="ci",
        structured_findings=findings,
    )]
    results = _search_with_records(records)

    result = results[0]
    assert result["scope"] == "payments"
    assert result["content"] == "important lesson"
    assert result["source"] == "ci"
    assert result["structured_findings"] == findings
    assert "id" in result
    assert "type" in result
    assert "confidence" in result
    assert "tags" in result
    assert "score" in result
    assert "signal_breakdown" in result
