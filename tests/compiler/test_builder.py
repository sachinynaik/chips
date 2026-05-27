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
    compressor.compress_with_trace.return_value = (output, [])
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


# ── Diffs evidence fusion ─────────────────────────────────────────────────────

from unittest.mock import patch


def _fake_diff(sha="abc123"):
    return {
        "sha": sha,
        "message": "fix auth flow",
        "author": "dev",
        "committed_at": "2026-05-01T00:00:00+00:00",
        "files_changed": ["src/auth/service.py"],
        "cochange_pairs": [],
    }


def test_build_calls_retrieve_diffs(conn):
    with patch("chips.compiler.builder.retrieve_diffs", return_value=[]) as mock_diffs:
        BriefBuilder(conn, _make_embedder(), _make_compressor()).build("fix auth", scope="auth")
    mock_diffs.assert_called_once()


def test_build_passes_scope_to_retrieve_diffs(conn):
    with patch("chips.compiler.builder.retrieve_diffs", return_value=[]) as mock_diffs:
        BriefBuilder(conn, _make_embedder(), _make_compressor()).build("fix auth", scope="payments")
    _, kwargs = mock_diffs.call_args
    assert kwargs.get("scope") == "payments"


def test_build_includes_diffs_in_retrieved_items(conn):
    diff = _fake_diff("sha_retrieved")
    with patch("chips.compiler.builder.retrieve_diffs", return_value=[diff]):
        brief = BriefBuilder(conn, _make_embedder(), _make_compressor()).build("fix auth")
    assert diff in brief.retrieved.diffs


def test_build_includes_diff_in_ranked_signals(conn):
    with patch("chips.compiler.builder.retrieve_diffs", return_value=[_fake_diff("sha_ranked")]):
        brief = BriefBuilder(conn, _make_embedder(), _make_compressor()).build("fix auth")
    item_types = {s.item_type for s in brief.ranked_signals}
    assert "diff" in item_types


def test_build_persists_retrieved_diffs(conn):
    diff = _fake_diff("sha_persisted")
    with patch("chips.compiler.builder.retrieve_diffs", return_value=[diff]):
        brief = BriefBuilder(conn, _make_embedder(), _make_compressor()).build("fix auth")
    row = conn.execute(
        "SELECT retrieved_diffs FROM cortex_briefs WHERE brief_id = %s",
        (str(brief.brief_id),),
    ).fetchone()
    assert row is not None
    stored = row[0]
    assert isinstance(stored, list)
    assert stored[0]["sha"] == "sha_persisted"


# ── Gap 5: tenant_id threading ────────────────────────────────────────────────

_TENANT = "aaaaaaaa-0000-0000-0000-000000000001"


def test_build_stores_tenant_id_in_brief(conn):
    builder = BriefBuilder(conn, _make_embedder(), _make_compressor())
    brief = builder.build("fix crash", tenant_id=_TENANT)
    assert brief.tenant_id == _TENANT


def test_build_threads_tenant_id_to_retrieve_memories(conn):
    with patch("chips.compiler.builder.retrieve_memories", return_value=[]) as mock_mem:
        BriefBuilder(conn, _make_embedder(), _make_compressor()).build(
            "fix auth", tenant_id=_TENANT
        )
    _, kwargs = mock_mem.call_args
    assert kwargs.get("tenant_id") == _TENANT


def test_build_threads_tenant_id_to_retrieve_diffs(conn):
    with patch("chips.compiler.builder.retrieve_diffs", return_value=[]) as mock_diffs:
        BriefBuilder(conn, _make_embedder(), _make_compressor()).build(
            "fix auth", tenant_id=_TENANT
        )
    _, kwargs = mock_diffs.call_args
    assert kwargs.get("tenant_id") == _TENANT


def test_build_threads_tenant_id_to_retrieve_file_signals(conn):
    with patch("chips.compiler.builder.retrieve_file_signals", return_value=[]) as mock_fs:
        BriefBuilder(conn, _make_embedder(), _make_compressor()).build(
            "fix auth", files=["src/auth.py"], tenant_id=_TENANT
        )
    _, kwargs = mock_fs.call_args
    assert kwargs.get("tenant_id") == _TENANT


def test_build_persists_tenant_id_to_db(conn):
    builder = BriefBuilder(conn, _make_embedder(), _make_compressor())
    brief = builder.build("fix crash", tenant_id=_TENANT)
    row = conn.execute(
        "SELECT tenant_id FROM cortex_briefs WHERE brief_id = %s",
        (str(brief.brief_id),),
    ).fetchone()
    assert row is not None
    assert str(row[0]) == _TENANT


def test_build_tenant_id_none_by_default(conn):
    builder = BriefBuilder(conn, _make_embedder(), _make_compressor())
    brief = builder.build("fix crash")
    assert brief.tenant_id is None


def test_build_raises_when_require_tenant_set_and_none_passed(conn, monkeypatch):
    import pytest
    monkeypatch.setenv("CHIPS_REQUIRE_TENANT_ID", "1")
    with pytest.raises(ValueError, match="CHIPS_REQUIRE_TENANT_ID"):
        BriefBuilder(conn, _make_embedder(), _make_compressor()).build("fix crash")
