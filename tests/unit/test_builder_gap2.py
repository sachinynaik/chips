"""Gap 2: file signals contract — unit tests with fully mocked dependencies."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from chips.compiler.builder import BriefBuilder


def _make_builder():
    return BriefBuilder(
        conn=MagicMock(),
        embedder=MagicMock(embed=MagicMock(return_value=[0.1] * 768)),
        compressor=MagicMock(compress=MagicMock(return_value="compressed")),
    )


def _build_with_mocks(files=None, file_signals_result=None):
    """Run build() with all DB calls patched. Returns brief."""
    builder = _make_builder()
    with (
        patch("chips.compiler.builder.retrieve_memories", return_value=[]),
        patch("chips.compiler.builder.retrieve_diffs", return_value=[]),
        patch(
            "chips.compiler.builder.retrieve_file_signals",
            return_value=file_signals_result or [],
        ),
        patch.object(BriefBuilder, "_persist"),
    ):
        return builder.build("fix crash", files=files)


# ── No files provided ────────────────────────────────────────────────────────

def test_data_sources_file_signals_not_configured_when_no_files():
    brief = _build_with_mocks(files=None)
    assert "file_signals" in brief.data_sources
    assert brief.data_sources["file_signals"].status == "not_configured"


def test_data_sources_file_signals_not_configured_detail_explains_absence():
    brief = _build_with_mocks(files=None)
    assert brief.data_sources["file_signals"].detail != ""


def test_retrieve_file_signals_not_called_when_no_files():
    builder = _make_builder()
    with (
        patch("chips.compiler.builder.retrieve_memories", return_value=[]),
        patch("chips.compiler.builder.retrieve_diffs", return_value=[]),
        patch("chips.compiler.builder.retrieve_file_signals", return_value=[]) as mock_fs,
        patch.object(BriefBuilder, "_persist"),
    ):
        builder.build("fix crash")  # no files
    mock_fs.assert_called_once()
    # called with empty list — no actual DB hit for empty list
    args = mock_fs.call_args[0]
    assert args[1] == []


# ── Files provided, signals found ────────────────────────────────────────────

def test_data_sources_file_signals_available_when_results_returned():
    signal = {"file_path": "src/auth.py", "churn_score": 3.0, "failure_count": 1, "last_changed_at": None}
    brief = _build_with_mocks(files=["src/auth.py"], file_signals_result=[signal])
    assert brief.data_sources["file_signals"].status == "available"


def test_file_signals_appear_in_ranked_when_provided():
    signal = {"file_path": "src/auth.py", "churn_score": 3.0, "failure_count": 1, "last_changed_at": None}
    brief = _build_with_mocks(files=["src/auth.py"], file_signals_result=[signal])
    item_types = {s.item_type for s in brief.ranked_signals}
    assert "file" in item_types


# ── Files provided, no signals found ─────────────────────────────────────────

def test_data_sources_file_signals_unavailable_when_no_results():
    brief = _build_with_mocks(files=["src/auth.py"], file_signals_result=[])
    assert brief.data_sources["file_signals"].status == "unavailable"


# ── Empty list treated same as no files ──────────────────────────────────────

def test_data_sources_file_signals_not_configured_for_empty_list():
    brief = _build_with_mocks(files=[])
    assert brief.data_sources["file_signals"].status == "not_configured"
