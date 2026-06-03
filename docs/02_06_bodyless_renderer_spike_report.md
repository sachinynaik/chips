# Bodyless Renderer Spike — Report

**Status:** spike complete (2026-06-03). **Result: net token win without latency
regression — recommend promoting `compact_context_tier`, gated on the
normalization contract (slice 4).** Governed by `02_06_signature_map_design.md`
(step 3) and `02_06_execution_ledger.md` (`bodyless_renderer_spike`).

## Question

Does rendering the structural layer's selected symbols as **signatures only**
(`bodies=False`) instead of full bodies give a *net token win without a latency
regression*? The design flagged the risk that a bodyless extractor (e.g. griffe
whole-module loads) could cost more wall-clock than the tokens it saves.

## Method

- **Toggle, not a new subsystem** (per design): added `bodies: bool = True` to
  `retrieve_structural`. When `False` it renders `StructuralSymbol.signature_text`
  (the declaration up to the AST body-block boundary) instead of `body_text`.
  Default `True` preserves existing behaviour exactly. **No new parser** — it
  reuses the tree-sitter pass already run for structural retrieval.
- **Corpus:** CHIPS's own `src/chips` (92 Python files, 346 extracted symbols).
- **Token win:** tiktoken `cl100k_base` tokens, summed over *every* extracted
  symbol (selection-independent), body vs signature.
- **Latency:** `retrieve_structural` over all files, huge budget so the selection
  is identical in both modes; min of 3 runs after a cache warm.
- **Determinism:** two full renders compared byte-for-byte in one env.
- Reproduce: `bash scripts/_spike_run.sh` (or `uv run python
  scripts/spike_bodyless_renderer.py` inside the container).

## Results

| metric | value |
|---|---|
| files / symbols | 92 / 346 |
| body tokens (total) | 69,064 |
| signature tokens (total) | 6,569 |
| **token win** | **62,495 tokens (90.5% reduction)** |
| latency `bodies=True` | 356.5 ms |
| latency `bodies=False` | 353.6 ms |
| **latency delta** | **−2.9 ms (bodyless marginally faster)** |
| deterministic across 2 runs (same env) | **True** |

## Conclusion

A **90.5% token reduction at zero latency cost** (in fact marginally faster — less
text to render, same parse). The design's "extractor costs more than it saves"
risk does not apply to the toggle approach because it reuses the existing
tree-sitter parse. The spike **proves net value**: promote `compact_context_tier`
to Activation.

## Gates before promotion (not satisfied by this spike)

1. **Cross-OS byte-identical golden — blocked on slice 4 (normalization
   contract).** This spike proves *same-env* determinism only. The signature
   extraction here is a spike heuristic (AST body-child boundary, trailing
   whitespace stripped); it is **not** the closed normalization contract
   (line-endings + NFC, annotation stance, decorators, `@overload`, PEP 695,
   etc.). Per the design, "no [production] rendering code before the matrix
   exists." Additionally our CI is Linux-only — the *cross-OS* half of the gate
   cannot be exercised until a non-Linux runner exists.
2. **Budget precedence rule** — sigmap (symbol-level) and file-signals
   (file-level) must never double-count the same file. Required before wiring the
   tier into the tiktoken budget.
3. **Selection stays single-owner** — the tier renders the *same* selection the
   structural/graph layer already produced; it must not become a new retrieval
   source.

## Caveats

- Numbers are CHIPS's own Python corpus; other repos/languages will differ in
  ratio but the mechanism (drop the body, keep the signature) is corpus-agnostic.
- 90.5% reflects that bodies dominate token cost; signatures are short. Real
  brief budgets select a subset, but the *per-symbol* ratio is what scales.
