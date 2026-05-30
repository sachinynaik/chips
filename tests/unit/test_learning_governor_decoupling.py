"""D3 (L8): learning adjustments influence ranking only — never the governor.

The governor's contract (``governor.evaluate`` docstring) is that it reads the
similarity/confidence scores set by ``retrieve_memories`` *before* learning
adjustments are applied. ``build()`` used to mutate ``memory["confidence"]`` by
the learning adjustment before calling the governor, which:

  (a) polluted the governor on the no-``similarity`` fallback path — learned-good
      memories could trip the short-circuit and suppress secondary evidence; and
  (b) double-counted the adjustment in the ranker, which already adds
      ``learning_adjustment`` to ``sem`` (sem falls back to the mutated confidence,
      then adds the adjustment again).

Fix: carry the adjustment only in ``memory["learning_adjustment"]``; never mutate
``confidence``. Pure (no DB) — exercises the extracted helper + governor + ranker.
"""
from __future__ import annotations

from chips.compiler.builder import _apply_learning_adjustments
from chips.compiler.governor import evaluate as governor_evaluate
from chips.compiler.ranker import rank_signals


def test_sets_learning_adjustment_field():
    memories = [{"id": "m1", "confidence": 0.5}]
    _apply_learning_adjustments(memories, {"m1": 0.2})
    assert memories[0]["learning_adjustment"] == 0.2


def test_does_not_mutate_confidence():
    memories = [{"id": "m1", "confidence": 0.5}]
    _apply_learning_adjustments(memories, {"m1": 0.2})
    assert memories[0]["confidence"] == 0.5  # raw retrieval score, untouched


def test_unknown_memory_gets_zero_adjustment():
    memories = [{"id": "m1", "confidence": 0.5}]
    _apply_learning_adjustments(memories, {"other": 0.9})
    assert memories[0]["learning_adjustment"] == 0.0
    assert memories[0]["confidence"] == 0.5


def test_governor_unaffected_by_learning_on_no_similarity_path():
    """Raw confidence below threshold + no similarity: learning must NOT trip the governor."""
    memories = [{"id": f"m{i}", "confidence": 0.5} for i in range(3)]  # 0.5 < 0.75 threshold
    # Large enough that, had they leaked into confidence, mean would exceed 0.75.
    _apply_learning_adjustments(memories, {f"m{i}": 0.5 for i in range(3)})

    decision = governor_evaluate(memories)
    assert decision.triggered is False
    assert decision.mean_confidence == 0.5  # governor saw raw confidence, not 1.0


def test_ranker_does_not_double_count_adjustment_without_similarity():
    """sem falls back to raw confidence; learning_adjustment is added exactly once."""
    memories = [{"id": "m1", "confidence": 0.4}]
    _apply_learning_adjustments(memories, {"m1": 0.3})

    ranked = rank_signals(memories, [], diffs=[])
    mem_sig = next(s for s in ranked if s.item_id == "m1")
    assert abs(mem_sig.score - 0.7) < 1e-9             # 0.4 + 0.3, not 1.0 (double-count)
    assert abs(mem_sig.signal_breakdown["semantic"] - 0.4) < 1e-9
