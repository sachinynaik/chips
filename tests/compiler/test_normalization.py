"""Normalization contract — the determinism-breaking cases (slice 4).

These pin the *closed* part of the contract: line endings, Unicode form,
whitespace (trailing + common indentation), and path separators. Internal
spacing inside a signature is deliberately NOT collapsed (that is semantic
canonicalisation / anchor-stability, explicitly deferred — see
docs/02_06_normalization_contract.md).
"""

from __future__ import annotations

from chips.compiler.normalization import (
    normalize_path,
    normalize_text,
    posix_basename,
)


def test_crlf_and_cr_become_lf():
    assert normalize_text("a\r\nb\rc") == "a\nb\nc"


def test_unicode_normalized_to_nfc():
    decomposed = "é"  # 'e' + combining acute
    assert normalize_text(decomposed) == "é"  # precomposed é


def test_trailing_whitespace_stripped_per_line():
    assert normalize_text("a   \nb\t") == "a\nb"


def test_common_indentation_removed():
    assert normalize_text("    a\n    b") == "a\nb"


def test_leading_and_trailing_blank_lines_stripped():
    assert normalize_text("\n\ndef f():\n\n") == "def f():"


def test_internal_spacing_is_preserved():
    # We are not a formatter: same source -> same bytes, but we do NOT canonicalise
    # internal spacing (that is the deferred anchor-stability concern).
    assert normalize_text("def m(self, x ) ->  int :") == "def m(self, x ) ->  int :"


def test_normalize_text_is_idempotent():
    s = "    def f(a,\r\n        b):  \n"
    once = normalize_text(s)
    assert normalize_text(once) == once


def test_normalize_path_uses_forward_slashes():
    assert normalize_path("src\\chips\\x.py") == "src/chips/x.py"
    assert normalize_path("src/chips/x.py") == "src/chips/x.py"


def test_posix_basename_is_separator_independent():
    assert posix_basename("src\\chips\\x.py") == "x.py"
    assert posix_basename("src/chips/x.py") == "x.py"
