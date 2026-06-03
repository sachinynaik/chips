"""Signature-map spike: the bodies=False toggle on retrieve_structural.

Asserts the toggle renders signatures (not bodies), is deterministic within an
env (the same-run half of the byte-identical gate; the cross-OS golden is slice
4 / normalization contract), and yields a token win on the same selection.
"""

from __future__ import annotations

import pytest

from chips.compiler import structural
from chips.compiler.structural import retrieve_structural

if not structural._TS_AVAILABLE:  # tree-sitter grammars absent
    pytest.skip("tree-sitter not installed", allow_module_level=True)


_SAMPLE = '''\
def alpha(a: int, b: str = "x") -> bool:
    total = a + len(b)
    helper(total)
    return total > 0


def helper(n):
    return n + 1


class Beta:
    def gamma(self, items):
        acc = 0
        for it in items:
            acc += it
        return acc
'''


@pytest.fixture
def sample_file(tmp_path):
    f = tmp_path / "sample.py"
    f.write_text(_SAMPLE, encoding="utf-8")
    return str(f)


def _texts(items):
    return "\n".join(i["text"] for i in items)


def test_bodies_true_is_unchanged_default(sample_file):
    items = retrieve_structural([sample_file], token_budget=100_000)  # default bodies=True
    joined = _texts(items)
    assert "total = a + len(b)" in joined  # body present
    assert "def alpha(a: int, b: str = \"x\") -> bool:" in joined


def test_bodies_false_renders_signature_not_body(sample_file):
    items = retrieve_structural([sample_file], token_budget=100_000, bodies=False)
    joined = _texts(items)
    # signature kept...
    assert "def alpha(a: int, b: str = \"x\") -> bool:" in joined
    # ...body dropped
    assert "total = a + len(b)" not in joined
    assert "for it in items:" not in joined


def test_bodyless_is_deterministic_within_env(sample_file):
    a = retrieve_structural([sample_file], token_budget=100_000, bodies=False)
    b = retrieve_structural([sample_file], token_budget=100_000, bodies=False)
    assert [i["text"] for i in a] == [i["text"] for i in b]


def test_bodyless_saves_tokens_on_same_selection(sample_file):
    full = retrieve_structural([sample_file], token_budget=100_000, bodies=True)
    sig = retrieve_structural([sample_file], token_budget=100_000, bodies=False)
    # Same symbols selected in both modes (selection is single-owner; only the
    # render differs) — otherwise the comparison is apples-to-oranges.
    assert {i["item_id"] for i in full} == {i["item_id"] for i in sig}
    assert sum(len(i["text"]) for i in sig) < sum(len(i["text"]) for i in full)
