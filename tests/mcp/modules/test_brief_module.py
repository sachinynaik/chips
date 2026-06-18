"""RED: BriefModule tests."""
from unittest.mock import MagicMock, patch


def _make_module():
    from chips.mcp.modules.brief import BriefModule
    return BriefModule(
        conn_factory=MagicMock(),
        embedder=MagicMock(),
        compressor=MagicMock(),
        policy_loader=MagicMock(),
    )


def test_brief_module_name():
    assert _make_module().name == "brief"


def test_get_context_brief_builds_and_returns_dict():
    from chips.mcp.modules.brief import BriefModule
    from unittest.mock import MagicMock
    import uuid
    from datetime import datetime, timezone

    fake_brief = MagicMock()
    fake_brief.brief_id = uuid.uuid4()
    fake_brief.task = "fix login"
    fake_brief.task_kind = "bugfix"
    fake_brief.scope = "auth"
    fake_brief.generated_at = datetime.now(timezone.utc)
    fake_brief.latency_ms = 42
    fake_brief.hard_constraints = ["never bypass auth"]
    fake_brief.compressed_context = "auth service overview"
    fake_brief.ranked_signals = []
    fake_brief.retrieved.memories = []
    fake_brief.forbidden_edits = []
    fake_brief.allowed_edits = []

    with patch("chips.mcp.modules.brief.BriefBuilder") as mock_builder_cls:
        mock_builder = MagicMock()
        mock_builder.build_and_log.return_value = fake_brief
        mock_builder_cls.return_value = mock_builder

        module = _make_module()
        result = module.get_context_brief(task="fix login", scope="auth")

    assert result["task"] == "fix login"
    assert result["scope"] == "auth"
    assert "brief_id" in result
    assert "hard_constraints" in result
    assert "compressed_context" in result
    assert "ranked_signals" in result


def test_get_context_brief_passes_task_and_scope_to_builder():
    from chips.mcp.modules.brief import BriefModule
    import uuid
    from datetime import datetime, timezone

    fake_brief = MagicMock()
    fake_brief.brief_id = uuid.uuid4()
    fake_brief.generated_at = datetime.now(timezone.utc)
    fake_brief.ranked_signals = []
    fake_brief.retrieved.memories = []

    with patch("chips.mcp.modules.brief.BriefBuilder") as mock_builder_cls:
        mock_builder = MagicMock()
        mock_builder.build_and_log.return_value = fake_brief
        mock_builder_cls.return_value = mock_builder

        module = _make_module()
        module.get_context_brief(task="add feature X", scope="payments")

    mock_builder.build_and_log.assert_called_once_with(
        "add feature X", scope="payments", files=None, tenant_id=None
    )


# ── Gap 5: tenant_id threading ────────────────────────────────────────────────

_TENANT = "aaaaaaaa-0000-0000-0000-000000000001"


def test_get_context_brief_threads_tenant_id_to_builder():
    import uuid
    from datetime import datetime, timezone

    fake_brief = MagicMock()
    fake_brief.brief_id = uuid.uuid4()
    fake_brief.generated_at = datetime.now(timezone.utc)
    fake_brief.ranked_signals = []
    fake_brief.retrieved.memories = []

    with patch("chips.mcp.modules.brief.BriefBuilder") as mock_builder_cls:
        mock_builder = MagicMock()
        mock_builder.build_and_log.return_value = fake_brief
        mock_builder_cls.return_value = mock_builder

        module = _make_module()
        module.get_context_brief(task="fix crash", scope="auth", tenant_id=_TENANT)

    mock_builder.build_and_log.assert_called_once_with(
        "fix crash", scope="auth", files=None, tenant_id=_TENANT
    )


def test_brief_module_register_adds_tool_to_app():
    from mcp.server.fastmcp import FastMCP
    app = FastMCP("test")
    _make_module().register(app)
    assert "get_context_brief" in list(app._tool_manager._tools.keys())


# ── data_sources wire contract ────────────────────────────────────────────────

def test_get_context_brief_serializes_data_sources_to_dict():
    """data_sources must appear in the MCP response as {key: {status, detail}}."""
    import uuid
    from datetime import datetime, timezone
    from chips.compiler.models import SourceStatus

    fake_brief = MagicMock()
    fake_brief.brief_id = uuid.uuid4()
    fake_brief.generated_at = datetime.now(timezone.utc)
    fake_brief.ranked_signals = []
    fake_brief.retrieved.memories = []
    fake_brief.data_sources = {
        "runtime": SourceStatus(status="not_configured"),
        "workflow": SourceStatus(status="error", detail="refused"),
        "file_signals": SourceStatus(status="available"),
    }

    with patch("chips.mcp.modules.brief.BriefBuilder") as mock_builder_cls:
        mock_builder = MagicMock()
        mock_builder.build_and_log.return_value = fake_brief
        mock_builder_cls.return_value = mock_builder
        result = _make_module().get_context_brief(task="fix crash")

    assert "data_sources" in result
    assert result["data_sources"]["runtime"] == {"status": "not_configured", "detail": "", "checked_at": None}
    assert result["data_sources"]["workflow"] == {"status": "error", "detail": "refused", "checked_at": None}
    assert result["data_sources"]["file_signals"] == {"status": "available", "detail": "", "checked_at": None}


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
    fake_brief.ranked_signals = []
    fake_brief.retrieved.memories = []
    fake_brief.forbidden_edits = []
    fake_brief.allowed_edits = []
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

    with patch("chips.mcp.modules.brief.BriefBuilder") as mock_builder_cls:
        mock_builder = MagicMock()
        mock_builder.build_and_log.return_value = fake_brief
        mock_builder_cls.return_value = mock_builder
        result = _make_module().get_context_brief(task="fix crash", scope="auth")

    assert result["evidence_bundle"]["bundle_id"] == str(fake_brief.evidence_bundle.bundle_id)
    assert result["evidence_bundle"]["constraints"] == []
    assert result["evidence_bundle"]["evidence"][0]["evidence_id"] == "find:abc123def456"
    assert result["evidence_bundle"]["evidence"][0]["kind"] == "finding"
    assert "Fragility" in result["evidence_bundle"]["evidence"][0]["text"]
