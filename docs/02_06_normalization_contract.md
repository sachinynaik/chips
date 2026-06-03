# Normalization Contract — Conformance Matrix

**Status:** implementation complete (closed subset); **cross-OS verification
pending infra.** Governed by `02_06_signature_map_design.md` (step 1 — the matrix
is the defined GREEN for the bodyless renderer's byte-identical gate). Source of
truth: `src/chips/compiler/normalization.py`; pinned by
`tests/compiler/test_normalization.py` and
`tests/compiler/test_structural_normalization_golden.py`.

This contract canonicalises a raw extracted declaration (the signature-map
projection) into a **deterministic, environment-independent** string. It is
narrow on purpose: it closes the rules that *break determinism* across runs and
machines, and explicitly defers *semantic canonicalisation* (which is about
anchor stability, not determinism).

## Closed rules (one input construct -> one exact output)

| Concern | Rule | Input -> Output |
|---|---|---|
| Line endings | CRLF and CR collapse to LF | `a\r\nb\rc` -> `a\nb\nc` |
| Unicode form | NFC | `é` -> `é` |
| Trailing whitespace | stripped per line | `a   \nb\t` -> `a\nb` |
| Common indentation | removed (dedent) | `    a\n    b` -> `a\nb` |
| Blank edges | leading/trailing blank lines stripped | `\n\nx\n\n` -> `x` |
| Path separators | `\` -> `/` (POSIX) for ids & headers | `src\chips\x.py` -> `src/chips/x.py` |
| Idempotence | `normalize_text(normalize_text(x)) == normalize_text(x)` | — |
| Symbol order | the structural layer's deterministic BFS (input-derived); not re-sorted | — |

Path normalization is what makes the **item id and rendered header identical
across operating systems** (otherwise a Windows backslash path diverges from the
same file on Linux).

## Explicitly NOT closed (deferred — semantic canonicalisation)

These do **not** affect single-input determinism (same source -> same bytes on the
same construct); they affect *anchor stability across cosmetic edits*, which has
no consumer yet (the `sig:` public anchor is Optimization-blocked). Closing them
prematurely risks over-normalisation (dropping real signature changes).

- Internal spacing (`f(a,b)` vs `f(a, b)`) — preserved verbatim today.
- Type-annotation stance (`List` vs `list`; `from __future__` stringization).
- Decorators; `@overload` folding (one anchor vs many).
- PEP 695 generics; default-arg canonicalisation; positional-only / keyword-only markers.
- Docstring-first-line rule.

## Cross-OS verification — explicit infra gap (NOT claimed done)

The design's gate is "byte-identical golden across 2 runs **+ 2 OSes**." This
slice proves the **same-env** half: byte-identical across repeated runs on the
CI/WSL Linux runner (`test_render_is_byte_identical_across_runs`) and
line-ending/path independence by construction. The **cross-OS** half is **not
verified** — CI is Linux-only (act + the self-hosted WSL runner). 

**Unblocker:** a Windows and/or macOS CI runner executing the same golden tests.
Until then this slice is **"implementation complete, cross-OS verification
pending."** The normalization rules above are designed to be OS-independent
(LF, NFC, POSIX paths), but designed-for is not the same as verified-on.
