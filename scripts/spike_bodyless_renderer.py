#!/usr/bin/env python3
"""Signature-map spike: measure the bodies=False token win vs latency cost.

Time-boxed investigation (NOT production code) per the signature-map design
(02_06_signature_map_design.md step 3). Renders the structural layer's symbols
two ways -- full body vs signature-only -- over a real corpus and reports:

  * token win  : tiktoken tokens saved by signature-only rendering
  * latency    : wall-clock of retrieve_structural in each mode (the design's
                 risk is that a bodyless extractor costs more wall-clock than the
                 tokens it saves; here we reuse the SAME tree-sitter parse, so we
                 expect ~zero latency delta)
  * determinism: bytes-identical output across two runs in this env

Run inside the container (tree-sitter + tiktoken present):
    uv run python scripts/spike_bodyless_renderer.py
"""

from __future__ import annotations

import os
import time

import tiktoken

from chips.compiler import structural
from chips.compiler.structural import _extract_symbols, retrieve_structural

_ENC = tiktoken.get_encoding("cl100k_base")


def _corpus(root: str = "src/chips") -> list[str]:
    files: list[str] = []
    for dirpath, _dirs, names in os.walk(root):
        for n in names:
            if n.endswith(".py"):
                files.append(os.path.join(dirpath, n))
    return sorted(files)


def _tok(text: str) -> int:
    return len(_ENC.encode(text))


def main() -> None:
    if not structural._TS_AVAILABLE:
        raise SystemExit("tree-sitter unavailable; run inside the container env")

    files = _corpus()
    # Symbol-level token win over EVERY extracted symbol (selection-independent).
    body_tokens = 0
    sig_tokens = 0
    n_symbols = 0
    for fp in files:
        try:
            source = open(fp, "rb").read()
        except OSError:
            continue
        ext = os.path.splitext(fp)[1].lower()
        lang = structural._get_language(ext)
        if lang is None:
            continue
        for sym in _extract_symbols(source, fp, lang):
            n_symbols += 1
            body_tokens += _tok(sym.body_text)
            sig_tokens += _tok(sym.signature_text)

    # Entry-level latency: identical selection (huge budget), each mode timed.
    big = 10_000_000

    def _timed(bodies: bool) -> float:
        t0 = time.monotonic()
        retrieve_structural(files, token_budget=big, hop_depth=99, bodies=bodies)
        return (time.monotonic() - t0) * 1000.0

    # warm the language cache so the comparison is parse-vs-parse, not load
    retrieve_structural(files[:1], token_budget=big, bodies=True)
    lat_body = min(_timed(True) for _ in range(3))
    lat_sig = min(_timed(False) for _ in range(3))

    # Determinism: two runs, byte-identical rendered output.
    r1 = [i["text"] for i in retrieve_structural(files, token_budget=big, hop_depth=99, bodies=False)]
    r2 = [i["text"] for i in retrieve_structural(files, token_budget=big, hop_depth=99, bodies=False)]
    deterministic = r1 == r2

    win_pct = 100.0 * (body_tokens - sig_tokens) / body_tokens if body_tokens else 0.0
    lat_delta = lat_sig - lat_body

    print("=== bodyless renderer spike ===")
    print(f"files                : {len(files)}")
    print(f"symbols              : {n_symbols}")
    print(f"body tokens (total)  : {body_tokens}")
    print(f"signature tokens     : {sig_tokens}")
    print(f"TOKEN WIN            : {body_tokens - sig_tokens} tokens ({win_pct:.1f}% reduction)")
    print(f"latency bodies=True  : {lat_body:.1f} ms")
    print(f"latency bodies=False : {lat_sig:.1f} ms")
    print(f"LATENCY DELTA        : {lat_delta:+.1f} ms (negative = faster bodyless)")
    print(f"deterministic 2 runs : {deterministic}")


if __name__ == "__main__":
    main()
