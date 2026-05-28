"""Gap 1: BriefOutcomeRepository — unit tests with mock cursor."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from chips.memory.outcome_repository import BriefOutcomeRepository


def _make_repo():
    conn = MagicMock()
    fake_id = str(uuid.uuid4())
    # Brief existence check: brief found, stored tenant = None (dev/unscoped mode).
    brief_mock = MagicMock()
    brief_mock.fetchone.return_value = (None,)
    # INSERT RETURNING id
    insert_mock = MagicMock()
    insert_mock.fetchone.return_value = (fake_id,)
    conn.execute.side_effect = [brief_mock, insert_mock]
    return BriefOutcomeRepository(conn), conn, fake_id


def test_record_returns_uuid():
    repo, _, fake_id = _make_repo()
    result = repo.record(uuid.uuid4(), outcome="accepted")
    assert isinstance(result, uuid.UUID)
    assert str(result) == fake_id


def test_record_commits_after_insert():
    repo, conn, _ = _make_repo()
    repo.record(uuid.uuid4(), outcome="rejected")
    conn.commit.assert_called_once()


def test_record_passes_outcome_to_sql():
    repo, conn, _ = _make_repo()
    brief_id = uuid.uuid4()
    repo.record(brief_id, outcome="ignored", note="too noisy")
    args = conn.execute.call_args[0]
    params = args[1]
    assert "ignored" in params
    assert "too noisy" in params


def test_record_passes_tenant_id_when_provided():
    repo, conn, _ = _make_repo()
    tenant = "cccccccc-0000-0000-0000-000000000001"
    repo.record(uuid.uuid4(), outcome="accepted", tenant_id=tenant)
    args = conn.execute.call_args[0]
    params = args[1]
    assert tenant in params


def test_record_passes_none_tenant_when_omitted():
    repo, conn, _ = _make_repo()
    repo.record(uuid.uuid4(), outcome="accepted")
    args = conn.execute.call_args[0]
    params = args[1]
    assert None in params


def test_get_for_brief_returns_list():
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = []
    result = BriefOutcomeRepository(conn).get_for_brief(uuid.uuid4())
    assert isinstance(result, list)


def test_get_for_brief_includes_tenant_filter_when_provided():
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = []
    tenant = "cccccccc-0000-0000-0000-000000000001"
    BriefOutcomeRepository(conn).get_for_brief(uuid.uuid4(), tenant_id=tenant)
    sql = conn.execute.call_args[0][0]
    assert "tenant_id" in sql
