"""MCP server wiring tests — verifies the bus app and tool registrations."""
from uuid import uuid4
from unittest.mock import MagicMock, patch


def test_server_app_exists():
    from chips.mcp.server import app
    assert app is not None
    assert app.name == "chips-cortex"


def test_server_exposes_health_and_feedback_tools():
    from chips.mcp.server import app
    registered = set(app._tool_manager._tools.keys())
    expected = {
        "search_memory",
        "get_recent_commits",
        "get_context_brief",
        "submit_brief_feedback",
        "get_source_health",
        "get_diffs",
        "get_runtime_context",
        "get_workflow_state",
        "get_contracts",
        "get_test_context",
        "get_policy",
        "get_constraints",
        "add_constraint",
        "retire_constraint",
        "submit_hypotheses",
        "get_constraint_candidates",
        "review_constraint_candidate",
    }
    assert expected.issubset(registered)


def test_submit_hypotheses_server_delegates_to_tool():
    payload = {"bundle_id": "b1", "ranked_hypotheses": [], "constraint_candidates": []}
    with (
        patch("chips.mcp.server._submit_hypotheses", return_value=payload) as fn,
        patch("chips.mcp.server._get_conn", return_value=MagicMock()),
    ):
        from chips.mcp.server import submit_hypotheses

        result = submit_hypotheses(
            evidence_bundle={"bundle_id": "b1", "constraints": [], "evidence": []},
            hypotheses=[],
        )

    assert result == payload
    fn.assert_called_once()


def test_get_constraint_candidates_server_delegates_to_tool():
    payload = {"status": "ok", "candidates": []}
    with (
        patch("chips.mcp.server._get_constraint_candidates", return_value=payload) as fn,
        patch("chips.mcp.server._get_conn", return_value=MagicMock()),
    ):
        from chips.mcp.server import get_constraint_candidates

        result = get_constraint_candidates(scope="checkout", tenant_id="t1")

    assert result == payload
    fn.assert_called_once()


def test_review_constraint_candidate_server_delegates_to_tool():
    payload = {"status": "ok", "reviewed": True}
    cid = str(uuid4())
    with (
        patch("chips.mcp.server._review_constraint_candidate", return_value=payload) as fn,
        patch("chips.mcp.server._get_conn", return_value=MagicMock()),
    ):
        from chips.mcp.server import review_constraint_candidate

        result = review_constraint_candidate(
            candidate_id=cid,
            resolution="dismissed",
            tenant_id="t1",
        )

    assert result == payload
    fn.assert_called_once()


def test_search_memory_tool_embeds_query_before_searching():
    fake_embedding = [0.1] * 768
    fake_results = [
        {
            "id": "abc",
            "type": "lesson",
            "scope": "api",
            "content": "always validate inputs",
            "confidence": 0.9,
            "source": None,
            "tags": [],
            "score": None,
            "signal_breakdown": {},
        }
    ]

    with patch("chips.mcp.modules.memory._search_memory", return_value=fake_results):
        from chips.mcp.modules.memory import MemoryModule
        embedder = MagicMock()
        embedder.embed.return_value = fake_embedding
        module = MemoryModule(conn_factory=MagicMock(), embedder=embedder)
        result = module.search_memory(query="test query", scope="api")

    embedder.embed.assert_called_once_with("test query")
    assert result == fake_results


def test_get_recent_commits_tool_delegates_to_db():
    fake_commits = [
        {
            "sha": "abc123",
            "author": "Alice",
            "committed_at": "2026-05-10T12:00:00+00:00",
            "message": "fix checkout",
            "files_changed": ["src/checkout.py"],
            "cochange_pairs": [],
        }
    ]

    with patch("chips.mcp.modules.git._get_recent_commits", return_value=fake_commits):
        from chips.mcp.modules.git import GitModule
        module = GitModule(conn_factory=MagicMock())
        result = module.get_recent_commits(limit=5)

    assert result == fake_commits


def test_get_context_brief_serializes_evidence_bundle_with_fragility_finding():
    import uuid
    from datetime import datetime, timezone
    from chips.compiler.models import EvidenceBundle, EvidenceItem

    fake_brief = MagicMock()
    fake_brief.brief_id = uuid.uuid4()
    fake_brief.task = "fix crash"
    fake_brief.task_kind = "bugfix"
    fake_brief.scope = "auth"
    fake_brief.tenant_id = None
    fake_brief.generated_at = datetime.now(timezone.utc)
    fake_brief.latency_ms = 42
    fake_brief.hard_constraints = []
    fake_brief.compressed_context = "ctx"
    fake_brief.schema_version = "1.0"
    fake_brief.data_sources = {}
    fake_brief.evidence_bundle = EvidenceBundle(
        bundle_id=uuid.uuid4(),
        constraints=[],
        evidence=[
            EvidenceItem(
                evidence_id="find:abc123def456",
                kind="finding",
                label="Fragility: 2 prior defect-linked fixes touch this area",
                text="Fragility: 2 prior defect-linked fixes touch this area (abc123, def456)",
                weight=0.0,
            )
        ],
    )

    with (
        patch("chips.mcp.server._get_conn") as mock_get_conn,
        patch("chips.mcp.server._get_embedder"),
        patch("chips.mcp.server._get_compressor"),
        patch("chips.mcp.server._get_policy_loader"),
        patch("chips.mcp.server.BriefBuilder") as mock_builder_cls,
    ):
        mock_get_conn.return_value = MagicMock()
        mock_builder = MagicMock()
        mock_builder.build_and_log.return_value = fake_brief
        mock_builder_cls.return_value = mock_builder

        from chips.mcp.server import get_context_brief

        result = get_context_brief(task="fix crash", scope="auth")

    assert result["evidence_bundle"]["bundle_id"] == str(fake_brief.evidence_bundle.bundle_id)
    assert result["evidence_bundle"]["constraints"] == []
    assert result["evidence_bundle"]["evidence"][0]["evidence_id"] == "find:abc123def456"
    assert result["evidence_bundle"]["evidence"][0]["kind"] == "finding"
    assert "Fragility" in result["evidence_bundle"]["evidence"][0]["text"]
