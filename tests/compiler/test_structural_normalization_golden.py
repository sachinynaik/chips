"""Golden / determinism tests for the normalized bodyless render (slice 4).

This is the same-env half of the design's "byte-identical across 2 runs + 2 OSes"
gate. The 2-OS half is an explicit infra gap (Linux-only CI; see
docs/02_06_normalization_contract.md) and is NOT claimed here.
"""

from __future__ import annotations

import pytest

from chips.compiler import structural
from chips.compiler.structural import retrieve_structural

if not structural._TS_AVAILABLE:
    pytest.skip("tree-sitter not installed", allow_module_level=True)


def _sigs(path):
    items = retrieve_structural([path], token_budget=100_000, bodies=False)
    return {i["item_id"].rsplit(":", 1)[-1]: i["text"].split("\n", 1)[1] for i in items}


def test_crlf_and_lf_inputs_render_identically(tmp_path):
    code = "def f(a):\n    return a\n"
    lf = tmp_path / "lf.py"
    lf.write_bytes(code.encode("utf-8"))
    crlf = tmp_path / "crlf.py"
    crlf.write_bytes(code.replace("\n", "\r\n").encode("utf-8"))

    assert _sigs(str(lf)) == _sigs(str(crlf)) == {"f": "def f(a):"}


def test_signature_render_golden(tmp_path):
    # CRLF endings + trailing whitespace + nesting -> normalized, internal spacing kept.
    src = b"class Q:\r\n    def m(self, x ) ->  int :  \r\n        return x\r\n"
    f = tmp_path / "g.py"
    f.write_bytes(src)

    sigs = _sigs(str(f))
    assert sigs["Q"] == "class Q:"
    assert sigs["m"] == "def m(self, x ) ->  int :"


def test_render_is_byte_identical_across_runs(tmp_path):
    f = tmp_path / "r.py"
    f.write_bytes(b"def a(x):\n    return x\n\ndef b(y):\n    return a(y)\n")
    first = [i["text"] for i in retrieve_structural([str(f)], token_budget=100_000, bodies=False)]
    second = [i["text"] for i in retrieve_structural([str(f)], token_budget=100_000, bodies=False)]
    assert first == second
