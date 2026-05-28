"""Phase 0: ConstraintRepository — mock-conn unit tests.

Covers idempotent add (SELECT-then-insert + race-safe unique-violation fallback),
soft retire, and for_scope query shape (mirrors PolicyLoader: '*' OR exact, active only).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import psycopg

from chips.compiler.constraint_repository import ConstraintRepository
from chips.compiler.constraints import dedup_hash
from chips.compiler.models import Constraint


def test_add_inserts_when_not_duplicate():
    conn = MagicMock()
    new_id = str(uuid.uuid4())
    select_mock = MagicMock(); select_mock.fetchone.return_value = None
    insert_mock = MagicMock(); insert_mock.fetchone.return_value = (new_id,)
    conn.execute.side_effect = [select_mock, insert_mock]

    repo = ConstraintRepository(conn)
    result = repo.add(scope_pattern="checkout", kind="forbidden", text="no pay edits",
                      target={"path": "pay.py"}, tenant_id="t1")

    assert str(result) == new_id
    conn.commit.assert_called_once()
    insert_sql = conn.execute.call_args_list[1][0][0]
    assert "INSERT INTO cortex_constraints" in insert_sql
    # dedup_hash is computed and stored
    expected_hash = dedup_hash("t1", "checkout", "forbidden", "no pay edits", {"path": "pay.py"})
    assert expected_hash in conn.execute.call_args_list[1][0][1]


def test_add_is_idempotent_returns_existing_without_insert():
    conn = MagicMock()
    existing = str(uuid.uuid4())
    select_mock = MagicMock(); select_mock.fetchone.return_value = (existing,)
    conn.execute.side_effect = [select_mock]

    repo = ConstraintRepository(conn)
    result = repo.add(scope_pattern="checkout", kind="forbidden", text="x", tenant_id="t1")

    assert str(result) == existing
    assert conn.execute.call_count == 1          # SELECT only, no INSERT
    conn.commit.assert_not_called()


def test_add_race_unique_violation_falls_back_to_existing():
    conn = MagicMock()
    existing = str(uuid.uuid4())
    select_none = MagicMock(); select_none.fetchone.return_value = None
    reselect = MagicMock(); reselect.fetchone.return_value = (existing,)
    conn.execute.side_effect = [
        select_none,
        psycopg.errors.UniqueViolation("dup"),   # INSERT races and loses
        reselect,
    ]

    repo = ConstraintRepository(conn)
    result = repo.add(scope_pattern="checkout", kind="forbidden", text="x", tenant_id="t1")

    assert str(result) == existing
    conn.rollback.assert_called_once()


def test_add_stores_kind_and_text():
    conn = MagicMock()
    select_mock = MagicMock(); select_mock.fetchone.return_value = None
    insert_mock = MagicMock(); insert_mock.fetchone.return_value = (str(uuid.uuid4()),)
    conn.execute.side_effect = [select_mock, insert_mock]

    ConstraintRepository(conn).add(scope_pattern="checkout", kind="known_issue",
                                   text="double decrement", reason="race", tenant_id="t1")
    params = conn.execute.call_args_list[1][0][1]
    assert "known_issue" in params
    assert "double decrement" in params


def test_retire_soft_updates_status():
    conn = MagicMock()
    cid = uuid.uuid4()
    ConstraintRepository(conn).retire(cid, tenant_id="t1")
    sql = conn.execute.call_args[0][0]
    params = conn.execute.call_args[0][1]
    assert "UPDATE cortex_constraints" in sql
    assert "superseded" in sql
    assert "tenant_id" in sql           # tenant-scoped
    assert str(cid) in params
    conn.commit.assert_called_once()


def test_for_scope_query_shape_and_parsing():
    conn = MagicMock()
    row = (
        str(uuid.uuid4()), "t1", "checkout", "forbidden", "no pay edits",
        "race", "human", "otlp-1", {"path": "pay.py"}, "active",
        datetime(2026, 5, 27, tzinfo=timezone.utc),
    )
    conn.execute.return_value.fetchall.return_value = [row]

    result = ConstraintRepository(conn).for_scope("checkout", tenant_id="t1")
    sql = conn.execute.call_args[0][0]
    assert "scope_pattern = '*'" in sql
    assert "status = 'active'" in sql
    assert "tenant_id = %s" in sql          # tenant filter predicate (not just the SELECT column)
    assert len(result) == 1
    c = result[0]
    assert isinstance(c, Constraint)
    assert c.kind == "forbidden"
    assert c.target == {"path": "pay.py"}


def test_for_scope_without_tenant_omits_tenant_filter():
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = []
    ConstraintRepository(conn).for_scope("checkout")
    sql = conn.execute.call_args[0][0]
    assert "tenant_id = %s" not in sql      # no tenant predicate when tenant omitted
