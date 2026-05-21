from __future__ import annotations

from datetime import datetime, timedelta, timezone

from chips.compiler.ranker import rank_signals


def _memory(id: str, similarity: float, type: str = "lesson") -> dict:
    return {"id": id, "type": type, "content": "x", "similarity": similarity}


def _file_signal(path: str, churn: float, days_old: int) -> dict:
    last_changed = datetime.now(timezone.utc) - timedelta(days=days_old)
    return {"file_path": path, "churn_score": churn, "failure_count": 0, "last_changed_at": last_changed}


def test_rank_returns_sorted_descending():
    memories = [_memory("a", 0.4), _memory("b", 0.9), _memory("c", 0.1)]
    ranked = rank_signals(memories, [])
    scores = [r.score for r in ranked]
    assert scores == sorted(scores, reverse=True)


def test_rank_score_between_0_and_1():
    memories = [_memory("a", 0.7)]
    signals = [_file_signal("foo.py", 0.5, 10)]
    for r in rank_signals(memories, signals):
        assert 0.0 <= r.score <= 1.0


def test_rank_empty_inputs():
    assert rank_signals([], []) == []


def test_rank_memory_item_type():
    ranked = rank_signals([_memory("m1", 0.8)], [])
    assert ranked[0].item_type == "memory"
    assert ranked[0].item_id == "m1"


def test_rank_file_item_type():
    ranked = rank_signals([], [_file_signal("auth.py", 0.6, 5)])
    assert ranked[0].item_type == "file"
    assert ranked[0].item_id == "auth.py"


def test_rank_signal_breakdown_present():
    ranked = rank_signals([_memory("m", 0.5)], [_file_signal("f.py", 0.3, 20)])
    for r in ranked:
        assert isinstance(r.signal_breakdown, dict)
        assert len(r.signal_breakdown) >= 1


def test_recent_file_scores_higher_than_old():
    recent = _file_signal("new.py", 0.5, 1)
    old = _file_signal("old.py", 0.5, 180)
    ranked = rank_signals([], [recent, old])
    assert ranked[0].item_id == "new.py"


# ── Diff ranking ──────────────────────────────────────────────────────────────

def _diff(sha: str, days_old: int, cochange_pairs: list | None = None) -> dict:
    committed_at = (datetime.now(timezone.utc) - timedelta(days=days_old)).isoformat()
    return {
        "sha": sha,
        "message": "commit message",
        "author": "dev",
        "committed_at": committed_at,
        "files_changed": ["src/auth/service.py"],
        "cochange_pairs": cochange_pairs or [],
    }


def test_rank_diff_item_type():
    ranked = rank_signals([], [], diffs=[_diff("abc123", days_old=1)])
    diff_items = [r for r in ranked if r.item_type == "diff"]
    assert len(diff_items) == 1
    assert diff_items[0].item_id == "abc123"


def test_rank_diff_score_between_0_and_1():
    pairs = [{"file_a": "x.py", "file_b": "y.py", "frequency": 3}]
    for r in rank_signals([], [], diffs=[_diff("abc", 5, pairs)]):
        assert 0.0 <= r.score <= 1.0


def test_rank_diff_has_recency_in_breakdown():
    ranked = rank_signals([], [], diffs=[_diff("abc", 3)])
    diff_signal = next(r for r in ranked if r.item_type == "diff")
    assert "recency" in diff_signal.signal_breakdown


def test_rank_diff_has_cochange_count_in_breakdown():
    pairs = [{"file_a": "a.py", "file_b": "b.py", "frequency": 5}]
    ranked = rank_signals([], [], diffs=[_diff("abc", 3, pairs)])
    diff_signal = next(r for r in ranked if r.item_type == "diff")
    assert "cochange_count" in diff_signal.signal_breakdown
    assert diff_signal.signal_breakdown["cochange_count"] == 1


def test_recent_diff_scores_higher_than_old_diff():
    recent = _diff("new_sha", days_old=1)
    old = _diff("old_sha", days_old=180)
    ranked = rank_signals([], [], diffs=[recent, old])
    diff_items = [r for r in ranked if r.item_type == "diff"]
    assert diff_items[0].item_id == "new_sha"


def test_rank_diffs_mixed_with_memories_and_files():
    memories = [_memory("m1", 0.9)]
    files = [_file_signal("f.py", 0.3, 5)]
    diffs = [_diff("d1", 2)]
    ranked = rank_signals(memories, files, diffs=diffs)
    types = {r.item_type for r in ranked}
    assert types == {"memory", "file", "diff"}
