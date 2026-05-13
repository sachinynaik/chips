from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from chips.compiler.builder import BriefBuilder
from chips.compiler.models import ContextBrief


def _make_embedder(vector: list[float] | None = None) -> MagicMock:
    embedder = MagicMock()
    embedder.embed.return_value = vector or [0.1] * 768
    return embedder


def _make_compressor(output: str = "compressed context") -> MagicMock:
    compressor = MagicMock()
    compressor.compress.return_value = output
    return compressor


def test_build_returns_context_brief(conn):
    builder = BriefBuilder(conn, _make_embedder(), _make_compressor())
    brief = builder.build("fix the login crash")
    assert isinstance(brief, ContextBrief)


def test_build_sets_task(conn):
    builder = BriefBuilder(conn, _make_embedder(), _make_compressor())
    brief = builder.build("add dark mode")
    assert brief.task == "add dark mode"


def test_build_sets_task_kind(conn):
    builder = BriefBuilder(conn, _make_embedder(), _make_compressor())
    brief = builder.build("fix the broken pipeline")
    assert brief.task_kind == "bugfix"


def test_build_records_latency(conn):
    builder = BriefBuilder(conn, _make_embedder(), _make_compressor())
    brief = builder.build("refactor the auth module")
    assert brief.latency_ms >= 0


def test_build_persists_to_db(conn):
    builder = BriefBuilder(conn, _make_embedder(), _make_compressor("summary text"))
    brief = builder.build("implement retry logic")
    row = conn.execute(
        "SELECT task, compressed_context FROM cortex_briefs WHERE brief_id = %s",
        (str(brief.brief_id),),
    ).fetchone()
    assert row is not None
    assert row[0] == "implement retry logic"
    assert row[1] == "summary text"


def test_build_assigns_unique_brief_ids(conn):
    builder = BriefBuilder(conn, _make_embedder(), _make_compressor())
    b1 = builder.build("task one")
    b2 = builder.build("task two")
    assert b1.brief_id != b2.brief_id


def test_build_with_scope(conn):
    builder = BriefBuilder(conn, _make_embedder(), _make_compressor())
    brief = builder.build("fix crash", scope="auth")
    assert brief.scope == "auth"
