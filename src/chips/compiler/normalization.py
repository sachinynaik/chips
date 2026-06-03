"""Normalization contract for the signature-map projection (slice 4).

The *closed* part of the contract — the rules that turn a raw extracted
declaration into a deterministic, env-independent projection. Scope is
deliberately narrow and honest (see docs/02_06_normalization_contract.md):

Closed here:
  - line endings   : CRLF / CR -> LF
  - Unicode form   : NFC
  - whitespace     : strip trailing per line; remove common leading indentation;
                     strip leading/trailing blank lines
  - paths          : separators -> '/' (POSIX), so item ids / headers are
                     identical across operating systems

Explicitly NOT closed (deferred): internal-spacing canonicalisation, annotation
stance (List vs list), decorators, @overload folding, PEP 695 generics,
default-arg canonicalisation, docstring rules. Those are semantic
canonicalisation (anchor stability), not determinism, and are out of scope until
a consumer needs them.
"""

from __future__ import annotations

import textwrap
import unicodedata


def normalize_text(text: str) -> str:
    """Canonicalise a declaration's text per the closed contract.

    Idempotent: ``normalize_text(normalize_text(x)) == normalize_text(x)``.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = unicodedata.normalize("NFC", text)
    text = textwrap.dedent(text)
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(lines).strip("\n")


def normalize_path(path: str) -> str:
    """Render a path with POSIX separators so output is OS-independent."""
    return path.replace("\\", "/")


def posix_basename(path: str) -> str:
    """Final path component, independent of the input separator."""
    return normalize_path(path).rsplit("/", 1)[-1]
