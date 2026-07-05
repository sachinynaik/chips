from __future__ import annotations

from uuid import uuid4
from unittest.mock import MagicMock, patch

from mcp.server.fastmcp import FastMCP


def _make_module():
    from chips.mcp.modules.hypotheses import HypothesesModule

    return HypothesesModule(conn_factory=MagicMock())


def test_hypotheses_module_name():
    assert _make_module().name == "hypotheses"


def test_submit_hypotheses_delegates_to_tool():
    payload = {"bundle_id": "b1", "ranked_hypotheses": [], "constraint_candidates": []}
    with patch("chips.mcp.modules.hypotheses._submit_hypotheses", return_value=payload) as fn:
        result = _make_module().submit_hypotheses(evidence_bundle={"bundle_id": "b1"}, hypotheses=[])

    assert result == payload
    fn.assert_called_once()


def test_get_constraint_candidates_delegates_to_tool():
    payload = {"status": "ok", "candidates": []}
    with patch("chips.mcp.modules.hypotheses._get_constraint_candidates", return_value=payload) as fn:
        result = _make_module().get_constraint_candidates(scope="checkout", tenant_id="t1")

    assert result == payload
    fn.assert_called_once()


def test_review_constraint_candidate_delegates_to_tool():
    payload = {"status": "ok", "reviewed": True}
    cid = str(uuid4())
    with patch("chips.mcp.modules.hypotheses._review_constraint_candidate", return_value=payload) as fn:
        result = _make_module().review_constraint_candidate(
            candidate_id=cid,
            resolution="dismissed",
            tenant_id="t1",
        )

    assert result == payload
    fn.assert_called_once()


def test_hypotheses_module_closes_connection_for_queue_tools():
    conn = MagicMock()
    from chips.mcp.modules.hypotheses import HypothesesModule

    with patch("chips.mcp.modules.hypotheses._get_constraint_candidates", return_value={"status": "ok", "candidates": []}):
        HypothesesModule(conn_factory=MagicMock(return_value=conn)).get_constraint_candidates()

    conn.close.assert_called_once()


def test_hypotheses_module_registers_tool():
    app = FastMCP("test")
    _make_module().register(app)
    assert "submit_hypotheses" in app._tool_manager._tools
    assert "get_constraint_candidates" in app._tool_manager._tools
    assert "review_constraint_candidate" in app._tool_manager._tools
