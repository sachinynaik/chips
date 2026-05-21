"""Tests for structured_findings in MemoryRepository (mocked DB, no Docker)."""
from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from chips.memory.models import MemoryRecord, MemoryType
from chips.memory.repository import MemoryRepository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_repo():
    """Return (repo, mock_conn) with register_vector patched out."""
    conn = MagicMock()
    with patch("chips.memory.repository.register_vector"):
        repo = MemoryRepository(conn)
    return repo, conn


def _base_record(**kwargs) -> MemoryRecord:
    defaults = dict(
        type=MemoryType.LESSON,
        scope="auth",
        content="some lesson",
        source="test",
    )
    defaults.update(kwargs)
    return MemoryRecord(**defaults)


def _make_row(
    structured_findings=None,
    *,
    id_=None,
    type_="lesson",
    scope="auth",
    content="some lesson",
    tags=None,
    evidence_refs=None,
    confidence=0.8,
    source="test",
    author=None,
    created_at=None,
    updated_at=None,
    archived_at=None,
    tenant_id=None,
    embedding=None,
):
    """Build a row tuple matching the SELECT column order in repository.py."""
    return (
        id_ or uuid.uuid4(),
        type_,
        scope,
        content,
        tags or [],
        evidence_refs or [],
        confidence,
        source,
        author,
        created_at or datetime(2024, 1, 1, tzinfo=timezone.utc),
        updated_at or datetime(2024, 1, 1, tzinfo=timezone.utc),
        archived_at,
        tenant_id,
        embedding,
        structured_findings,          # position 14 — last column
    )


# ---------------------------------------------------------------------------
# INSERT tests
# ---------------------------------------------------------------------------

def test_insert_includes_structured_findings_in_query():
    repo, conn = _make_repo()
    conn.execute.return_value.fetchone.return_value = (uuid.uuid4(),)

    record = _base_record(structured_findings={"security": [{"test_id": "B602"}]})
    repo.insert(record)

    sql = conn.execute.call_args[0][0]
    assert "structured_findings" in sql


def test_insert_serializes_structured_findings_as_json():
    repo, conn = _make_repo()
    conn.execute.return_value.fetchone.return_value = (uuid.uuid4(),)

    findings = {"dead_code": [{"name": "foo", "type": "function"}]}
    record = _base_record(structured_findings=findings)
    repo.insert(record)

    params = conn.execute.call_args[0][1]
    # structured_findings is the last positional param
    sf_param = params[-1]
    assert sf_param == json.dumps(findings)


def test_insert_empty_findings_serializes_as_empty_json_object():
    repo, conn = _make_repo()
    conn.execute.return_value.fetchone.return_value = (uuid.uuid4(),)

    record = _base_record(structured_findings={})
    repo.insert(record)

    params = conn.execute.call_args[0][1]
    sf_param = params[-1]
    assert sf_param == "{}"


# ---------------------------------------------------------------------------
# SELECT / get tests
# ---------------------------------------------------------------------------

def test_get_selects_structured_findings_column():
    repo, conn = _make_repo()
    conn.execute.return_value.fetchone.return_value = None

    repo.get(uuid.uuid4())

    sql = conn.execute.call_args[0][0]
    assert "structured_findings" in sql


def test_get_returns_record_with_structured_findings():
    repo, conn = _make_repo()
    findings = {"security": [{"test_id": "B101", "severity": "HIGH"}]}
    row = _make_row(structured_findings=findings)
    conn.execute.return_value.fetchone.return_value = row

    record = repo.get(uuid.uuid4())

    assert record is not None
    assert record.structured_findings == findings


def test_get_handles_null_structured_findings():
    repo, conn = _make_repo()
    row = _make_row(structured_findings=None)
    conn.execute.return_value.fetchone.return_value = row

    record = repo.get(uuid.uuid4())

    assert record is not None
    assert record.structured_findings == {}


# ---------------------------------------------------------------------------
# list_by_scope tests
# ---------------------------------------------------------------------------

def test_list_by_scope_selects_structured_findings():
    repo, conn = _make_repo()
    conn.execute.return_value.fetchall.return_value = []

    repo.list_by_scope("auth")

    sql = conn.execute.call_args[0][0]
    assert "structured_findings" in sql


# ---------------------------------------------------------------------------
# semantic_search tests
# ---------------------------------------------------------------------------

def test_semantic_search_selects_structured_findings():
    repo, conn = _make_repo()
    conn.execute.return_value.fetchall.return_value = []

    repo.semantic_search(query_embedding=[0.1] * 4, limit=5)

    sql = conn.execute.call_args[0][0]
    assert "structured_findings" in sql


# ---------------------------------------------------------------------------
# _row_to_record tests
# ---------------------------------------------------------------------------

def test_row_to_record_with_findings():
    findings = {"clones": [{"file_a": "a.py", "file_b": "b.py", "lines": 10}]}
    row = _make_row(structured_findings=findings)

    record = MemoryRepository._row_to_record(row)

    assert record.structured_findings == findings


def test_row_to_record_with_none_findings():
    row = _make_row(structured_findings=None)

    record = MemoryRepository._row_to_record(row)

    assert record.structured_findings == {}


def test_insert_with_nested_findings():
    """Nested findings dict round-trips correctly through JSON serialization."""
    repo, conn = _make_repo()
    conn.execute.return_value.fetchone.return_value = (uuid.uuid4(),)

    findings = {"security": [{"test_id": "B602", "severity": "HIGH", "line": 42}]}
    record = _base_record(structured_findings=findings)
    repo.insert(record)

    params = conn.execute.call_args[0][1]
    sf_param = params[-1]
    # Must round-trip through JSON
    assert json.loads(sf_param) == findings


def test_row_to_record_preserves_all_fields():
    """Other fields are still correct when structured_findings is present."""
    findings = {"type_errors": [{"code": "E001", "line": 5, "message": "bad type"}]}
    record_id = uuid.uuid4()
    row = _make_row(
        id_=record_id,
        type_="invariant",
        scope="payments",
        content="Never double-charge.",
        confidence=0.95,
        source="manual",
        structured_findings=findings,
    )

    record = MemoryRepository._row_to_record(row)

    assert record.id == record_id
    assert record.type == MemoryType.INVARIANT
    assert record.scope == "payments"
    assert record.content == "Never double-charge."
    assert record.confidence == pytest.approx(0.95)
    assert record.source == "manual"
    assert record.structured_findings == findings
