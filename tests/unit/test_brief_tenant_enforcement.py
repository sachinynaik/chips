"""Contract tests: tenant_id enforcement at every public brief entrypoint."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from chips.tenant import MISSING_TENANT_MSG, REQUIRE_TENANT_ENV

_TENANT = "aaaaaaaa-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# BriefModule.get_context_brief — MCP public boundary
# ---------------------------------------------------------------------------

def _make_module():
    from chips.mcp.modules.brief import BriefModule
    return BriefModule(
        conn_factory=MagicMock(),
        embedder=MagicMock(),
        compressor=MagicMock(),
        policy_loader=MagicMock(),
    )


class TestBriefModuleTenantEnforcement:
    def test_raises_when_enforcement_on_and_no_tenant(self, monkeypatch):
        monkeypatch.setenv(REQUIRE_TENANT_ENV, "1")
        module = _make_module()
        with pytest.raises(ValueError, match=MISSING_TENANT_MSG):
            module.get_context_brief(task="fix crash")

    def test_raises_before_builder_is_called(self, monkeypatch):
        monkeypatch.setenv(REQUIRE_TENANT_ENV, "1")
        module = _make_module()
        with patch("chips.mcp.modules.brief.BriefBuilder") as mock_cls:
            with pytest.raises(ValueError):
                module.get_context_brief(task="fix crash")
            mock_cls.assert_not_called()

    def test_no_error_when_enforcement_on_and_tenant_provided(self, monkeypatch):
        import uuid
        from datetime import datetime, timezone

        monkeypatch.setenv(REQUIRE_TENANT_ENV, "1")
        module = _make_module()
        fake_brief = MagicMock()
        fake_brief.brief_id = uuid.uuid4()
        fake_brief.generated_at = datetime.now(timezone.utc)
        fake_brief.ranked_signals = []
        fake_brief.retrieved.memories = []
        fake_brief.data_sources = {}

        with patch("chips.mcp.modules.brief.BriefBuilder") as mock_cls:
            mock_cls.return_value.build.return_value = fake_brief
            result = module.get_context_brief(task="fix crash", tenant_id=_TENANT)
        assert "brief_id" in result

    def test_no_error_when_enforcement_off_and_no_tenant(self, monkeypatch):
        import uuid
        from datetime import datetime, timezone

        monkeypatch.delenv(REQUIRE_TENANT_ENV, raising=False)
        module = _make_module()
        fake_brief = MagicMock()
        fake_brief.brief_id = uuid.uuid4()
        fake_brief.generated_at = datetime.now(timezone.utc)
        fake_brief.ranked_signals = []
        fake_brief.retrieved.memories = []
        fake_brief.data_sources = {}

        with patch("chips.mcp.modules.brief.BriefBuilder") as mock_cls:
            mock_cls.return_value.build.return_value = fake_brief
            result = module.get_context_brief(task="fix crash")
        assert "brief_id" in result


# ---------------------------------------------------------------------------
# BriefBuilder.build — internal enforcement (secondary check)
# ---------------------------------------------------------------------------

class TestBriefBuilderTenantEnforcement:
    def _make_builder(self):
        from chips.compiler.builder import BriefBuilder
        return BriefBuilder(
            conn=MagicMock(),
            embedder=MagicMock(embed=MagicMock(return_value=[0.1] * 768)),
            compressor=MagicMock(
                compress=MagicMock(return_value="compressed"),
                compress_with_trace=MagicMock(return_value=("compressed", [])),
            ),
        )

    def test_raises_when_enforcement_on_and_no_tenant(self, monkeypatch):
        monkeypatch.setenv(REQUIRE_TENANT_ENV, "1")
        builder = self._make_builder()
        with pytest.raises(ValueError, match=MISSING_TENANT_MSG):
            with (
                patch("chips.compiler.builder.retrieve_memories", return_value=[]),
                patch("chips.compiler.builder.retrieve_diffs", return_value=[]),
                patch("chips.compiler.builder.retrieve_file_signals", return_value=[]),
                patch.object(builder.__class__, "_persist"),
            ):
                builder.build("fix crash")

    def test_uses_shared_error_message(self, monkeypatch):
        monkeypatch.setenv(REQUIRE_TENANT_ENV, "1")
        builder = self._make_builder()
        with pytest.raises(ValueError) as exc_info:
            with (
                patch("chips.compiler.builder.retrieve_memories", return_value=[]),
                patch("chips.compiler.builder.retrieve_diffs", return_value=[]),
                patch("chips.compiler.builder.retrieve_file_signals", return_value=[]),
                patch.object(builder.__class__, "_persist"),
            ):
                builder.build("fix crash")
        assert str(exc_info.value) == MISSING_TENANT_MSG

    def test_passes_when_enforcement_off_and_no_tenant(self, monkeypatch):
        from chips.compiler.builder import BriefBuilder
        monkeypatch.delenv(REQUIRE_TENANT_ENV, raising=False)
        builder = self._make_builder()
        with (
            patch("chips.compiler.builder.retrieve_memories", return_value=[]),
            patch("chips.compiler.builder.retrieve_diffs", return_value=[]),
            patch("chips.compiler.builder.retrieve_file_signals", return_value=[]),
            patch.object(BriefBuilder, "_persist"),
        ):
            brief = builder.build("fix crash")
        assert brief.tenant_id is None


# ---------------------------------------------------------------------------
# Shared helper is the single policy source (no divergence)
# ---------------------------------------------------------------------------

class TestTenantHelperIsSharedPolicySource:
    def test_module_uses_require_tenant_from_chips_tenant(self):
        """BriefModule must call require_tenant(), not its own inline check."""
        import chips.mcp.modules.brief as brief_mod
        import inspect
        src = inspect.getsource(brief_mod)
        assert "require_tenant" in src
        assert 'CHIPS_REQUIRE_TENANT_ID' not in src  # no inline env check

    def test_builder_uses_require_tenant_from_chips_tenant(self):
        import chips.compiler.builder as builder_mod
        import inspect
        src = inspect.getsource(builder_mod)
        assert "require_tenant" in src
        assert 'CHIPS_REQUIRE_TENANT_ID' not in src  # no inline env check
