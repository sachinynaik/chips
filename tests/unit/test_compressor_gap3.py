"""Gap 3: deterministic compression pipeline — ranking, budget trimming, num_predict cap."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from chips.compiler.compressor import OllamaCompressor
from chips.compiler.models import SoftContextItem


def _mock_ollama(text: str = "summary") -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"response": text}
    return resp


def _make(soft_char_budget: int = 4000, num_predict: int = 200) -> OllamaCompressor:
    return OllamaCompressor(
        base_url="http://localhost:11434",
        model="qwen2.5-coder:1.5b",
        soft_char_budget=soft_char_budget,
        num_predict=num_predict,
    )


# ── Budget trimming ──────────────────────────────────────────────────────────

def test_trim_to_budget_keeps_first_items_when_over_budget():
    comp = _make(soft_char_budget=50)
    items = ["a" * 30, "b" * 30, "c" * 30]  # each ~34 chars including bullet
    trimmed = comp._trim_to_budget(items)
    assert len(trimmed) < len(items)
    assert trimmed[0] == items[0]


def test_trim_to_budget_keeps_all_when_under_budget():
    comp = _make(soft_char_budget=4000)
    items = ["short item 1", "short item 2", "short item 3"]
    trimmed = comp._trim_to_budget(items)
    assert trimmed == items


def test_trim_to_budget_always_keeps_at_least_one_item():
    comp = _make(soft_char_budget=1)  # impossibly small budget
    items = ["this item is definitely longer than 1 char"]
    trimmed = comp._trim_to_budget(items)
    assert len(trimmed) == 1


def test_compress_soft_sends_only_trimmed_items_to_ollama():
    comp = _make(soft_char_budget=50)
    # 3 items, each 30 chars — only first fits within budget
    items = ["a" * 30, "b" * 30, "c" * 30]
    captured = {}

    def fake_post(url, json=None, **kwargs):
        captured["prompt"] = json.get("prompt", "")
        return _mock_ollama()

    with patch("httpx.Client.post", side_effect=fake_post):
        comp.compress(hard_constraints=[], soft_items=items, task="fix it")

    # only first item should be in the prompt
    assert "a" * 30 in captured["prompt"]
    assert "b" * 30 not in captured["prompt"]


# ── num_predict cap ──────────────────────────────────────────────────────────

def test_compress_includes_num_predict_in_ollama_request():
    comp = _make(num_predict=150)
    captured = {}

    def fake_post(url, json=None, **kwargs):
        captured["body"] = json
        return _mock_ollama()

    with patch("httpx.Client.post", side_effect=fake_post):
        comp.compress(hard_constraints=[], soft_items=["some context"], task="fix it")

    assert captured["body"]["num_predict"] == 150


# ── Fallback also trims ──────────────────────────────────────────────────────

def test_fallback_on_ollama_error_uses_trimmed_items():
    comp = _make(soft_char_budget=50)
    items = ["a" * 30, "b" * 30, "c" * 30]

    with patch("httpx.Client.post", side_effect=Exception("refused")):
        result = comp.compress(hard_constraints=[], soft_items=items, task="fix it")

    assert "a" * 30 in result
    assert "b" * 30 not in result


# ── Determinism: same input → same output ────────────────────────────────────

def test_trim_is_deterministic_for_same_input():
    comp = _make(soft_char_budget=100)
    items = [f"item {i} " + "x" * 20 for i in range(10)]
    result1 = comp._trim_to_budget(items)
    result2 = comp._trim_to_budget(items)
    assert result1 == result2


def test_trim_preserves_category_coverage_when_budget_allows():
    comp = _make(soft_char_budget=90)
    items = [
        SoftContextItem(item_id="m1", category="memory", text="m" * 20, score=3.0),
        SoftContextItem(item_id="d1", category="diff", text="d" * 20, score=2.0),
        SoftContextItem(item_id="f1", category="finding", text="f" * 20, score=1.0),
    ]
    trimmed = comp._trim_to_budget(items)
    assert {item.category for item in trimmed} == {"memory", "diff", "finding"}


def test_compress_with_trace_returns_kept_and_dropped_ids():
    comp = _make(soft_char_budget=50)
    items = [
        SoftContextItem(item_id="m1", category="memory", text="a" * 30, score=2.0),
        SoftContextItem(item_id="d1", category="diff", text="b" * 30, score=1.0),
    ]

    with patch("httpx.Client.post", side_effect=Exception("refused")):
        _, trace = comp.compress_with_trace(
            hard_constraints=[],
            soft_items=items,
            task="fix it",
        )

    assert "m1" in trace["kept_item_ids"]
    assert "d1" in trace["dropped_item_ids"]
