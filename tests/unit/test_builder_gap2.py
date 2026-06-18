"""Gap 2: file signals contract — unit tests with fully mocked dependencies."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from chips.compiler.builder import BriefBuilder


def _make_builder():
    return BriefBuilder(
        conn=MagicMock(),
        embedder=MagicMock(embed=MagicMock(return_value=[0.1] * 768)),
        compressor=MagicMock(
            compress=MagicMock(return_value="compressed"),
            compress_with_trace=MagicMock(return_value=("compressed", [])),
        ),
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


# ── A2a: file signals injected as category="file" SoftContextItems (#2) ───────
#
# Before A2a, file signals were retrieved + ranked but dropped before the soft
# pool, so the paid retrieval/rank cost never reached the brief body. These tests
# pin that every retrieved file signal becomes a citable-in-context soft item
# handed to the compressor.

def _build_capturing_soft_items(files=None, file_signals_result=None):
    """Run build() with DB calls patched; return (brief, soft_items_passed_to_compressor)."""
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
        brief = builder.build("fix crash", files=files)
    # compress_with_trace(hard_constraints, soft_items, task) — soft_items is 2nd positional
    soft_items = builder._compressor.compress_with_trace.call_args[0][1]
    return brief, soft_items


def test_file_signal_injected_as_soft_item():
    signal = {
        "file_path": "src/auth.py",
        "churn_score": 3.0,
        "cochange_entropy": 0.4,
        "defect_history_count": 2,
        "fragility": 0.73,
        "failure_count": 2,
        "last_changed_at": None,
    }
    _brief, soft_items = _build_capturing_soft_items(
        files=["src/auth.py"], file_signals_result=[signal]
    )
    file_items = [s for s in soft_items if s.category == "file"]
    assert len(file_items) == 1
    assert file_items[0].item_id == "src/auth.py"
    assert "src/auth.py" in file_items[0].text
    assert "fragility=0.73" in file_items[0].text


def test_file_soft_item_carries_ranked_score():
    """The injected soft item reuses the ranker's score for this file_path."""
    signal = {
        "file_path": "src/auth.py",
        "churn_score": 3.0,
        "cochange_entropy": 0.4,
        "defect_history_count": 2,
        "fragility": 0.73,
        "failure_count": 2,
        "last_changed_at": None,
    }
    brief, soft_items = _build_capturing_soft_items(
        files=["src/auth.py"], file_signals_result=[signal]
    )
    file_item = next(s for s in soft_items if s.category == "file")
    ranked_score = next(
        r.score for r in brief.ranked_signals if r.item_type == "file" and r.item_id == "src/auth.py"
    )
    assert file_item.score == ranked_score


def test_multiple_file_signals_each_injected():
    signals = [
        {"file_path": "src/a.py", "churn_score": 1.0, "cochange_entropy": 0.0, "defect_history_count": 0, "fragility": 0.1, "failure_count": 0, "last_changed_at": None},
        {"file_path": "src/b.py", "churn_score": 5.0, "cochange_entropy": 0.6, "defect_history_count": 2, "fragility": 0.9, "failure_count": 3, "last_changed_at": None},
    ]
    _brief, soft_items = _build_capturing_soft_items(
        files=["src/a.py", "src/b.py"], file_signals_result=signals
    )
    file_ids = {s.item_id for s in soft_items if s.category == "file"}
    assert file_ids == {"src/a.py", "src/b.py"}


def test_no_file_soft_items_when_no_signals():
    _brief, soft_items = _build_capturing_soft_items(files=["src/auth.py"], file_signals_result=[])
    assert [s for s in soft_items if s.category == "file"] == []
