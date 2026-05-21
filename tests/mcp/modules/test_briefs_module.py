from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from chips.mcp.modules.briefs import BriefsModule


def _module() -> BriefsModule:
    conn = MagicMock()
    return BriefsModule(conn_factory=lambda: conn)


def _module_with_conn(conn: MagicMock) -> BriefsModule:
    return BriefsModule(conn_factory=lambda: conn)


# ── Module interface ──────────────────────────────────────────────────────────

def test_module_name_is_briefs():
    assert BriefsModule(conn_factory=MagicMock()).name == "briefs"


def test_module_registers_get_brief_tool():
    from mcp.server.fastmcp import FastMCP
    app = FastMCP("test")
    _module().register(app)
    tool_names = list(app._tool_manager._tools.keys())
    assert any("brief" in t for t in tool_names)


def test_module_registers_record_outcome_tool():
    from mcp.server.fastmcp import FastMCP
    app = FastMCP("test")
    _module().register(app)
    tool_names = list(app._tool_manager._tools.keys())
    assert any("outcome" in t for t in tool_names)


# ── get_brief ─────────────────────────────────────────────────────────────────

def test_get_brief_returns_brief_row():
    brief_id = str(uuid.uuid4())
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = (
        brief_id, "fix auth crash", "auth", "2026-05-01T00:00:00+00:00",
        150, "context text", None, None,
    )
    module = _module_with_conn(conn)
    result = module.get_brief(brief_id)
    assert result["brief_id"] == brief_id
    assert result["task"] == "fix auth crash"
    assert result["scope"] == "auth"


def test_get_brief_returns_not_found_for_missing_brief():
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = None
    module = _module_with_conn(conn)
    result = module.get_brief(str(uuid.uuid4()))
    assert result["status"] == "not_found"


def test_get_brief_returns_compressed_context():
    brief_id = str(uuid.uuid4())
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = (
        brief_id, "add dark mode", None, "2026-05-01T00:00:00+00:00",
        200, "## Constraints\n- never break auth", None, None,
    )
    module = _module_with_conn(conn)
    result = module.get_brief(brief_id)
    assert "Constraints" in result["compressed_context"]


def test_get_brief_includes_outcome_fields():
    brief_id = str(uuid.uuid4())
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = (
        brief_id, "task", "scope", "2026-05-01T00:00:00+00:00",
        100, "context", "success", "2026-05-01T01:00:00+00:00",
    )
    module = _module_with_conn(conn)
    result = module.get_brief(brief_id)
    assert result["post_task_outcome"] == "success"


# ── record_outcome ────────────────────────────────────────────────────────────

def test_record_outcome_updates_db():
    brief_id = str(uuid.uuid4())
    conn = MagicMock()
    conn.execute.return_value.rowcount = 1
    module = _module_with_conn(conn)
    result = module.record_outcome(brief_id=brief_id, outcome="success")
    conn.execute.assert_called_once()
    assert result["status"] == "ok"
    assert result["brief_id"] == brief_id


def test_record_outcome_returns_not_found_when_no_rows_updated():
    brief_id = str(uuid.uuid4())
    conn = MagicMock()
    conn.execute.return_value.rowcount = 0
    module = _module_with_conn(conn)
    result = module.record_outcome(brief_id=brief_id, outcome="success")
    assert result["status"] == "not_found"


def test_record_outcome_accepts_valid_outcomes():
    conn = MagicMock()
    conn.execute.return_value.rowcount = 1
    module = _module_with_conn(conn)
    for outcome in ("success", "partial", "failure", "abandoned"):
        result = module.record_outcome(brief_id=str(uuid.uuid4()), outcome=outcome)
        assert result["status"] == "ok"


def test_record_outcome_rejects_invalid_outcome():
    module = _module()
    result = module.record_outcome(brief_id=str(uuid.uuid4()), outcome="unknown_value")
    assert result["status"] == "error"
    assert "outcome" in result["message"].lower()


def test_record_outcome_stores_notes_when_provided():
    brief_id = str(uuid.uuid4())
    conn = MagicMock()
    conn.execute.return_value.rowcount = 1
    module = _module_with_conn(conn)
    module.record_outcome(brief_id=brief_id, outcome="partial", notes="ran out of context")
    call_args = conn.execute.call_args
    assert "ran out of context" in str(call_args)


def test_record_outcome_commits_after_update():
    conn = MagicMock()
    conn.execute.return_value.rowcount = 1
    module = _module_with_conn(conn)
    module.record_outcome(brief_id=str(uuid.uuid4()), outcome="success")
    conn.commit.assert_called_once()
