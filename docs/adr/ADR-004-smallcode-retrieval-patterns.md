# ADR-004: smallcode Retrieval-Pattern Borrows

**Date:** 2026-06-05
**Status:** Accepted (borrow-only; no dependency)
**Tool:** https://github.com/Doorman11991/smallcode (Node.js coding agent for small local
LLMs; MIT; 1.8k★, 13 contributors, 27 test files, active)

## Context

smallcode is the closest external mirror of CHIPS's compiler core: hybrid BM25 + vector
code search, symbol-aware chunking (snippets around functions/classes/types with
sliding-window fallback), strict token-budgeted snippet injection, structured traces
with `trace_id`/`span_id` per LLM call, and an agentic TDD harness with snapshot/rollback
and loop detection. Its values (determinism, verification, budgets) align with CHIPS's.

## Decision

**Borrow only.** It is another agent runtime — wrong layer and language for adoption —
and its self-invented MarrowScript/BoneScript DSL stack is a maintenance liability to
stay away from. The retrieval/budget design, however, is read-before-build material.

## Purpose & fit

Concrete pattern sources, mapped to CHIPS slices:

- **Symbol-aware chunking + sliding-window fallback** → compare against CHIPS
  tree-sitter structural retrieval defaults when next touching `structural.py`.
- **"Combine scores then inject top bounded snippets"** → reference for rank/compress
  boundary tuning (`_rank_and_assemble` / `_compress`).
- **Trace-to-test and budget-surfacing operator UX** (`/trace`, `/eval`, `/budget`) →
  reference for future CHIPS operator surfaces.
- **Their hashed-vector shortcut is NOT a borrow** — CHIPS's pgvector embeddings are
  strictly stronger; borrow the structure, not the embedding shortcut.

## Scope

Read `docs/rag-harness.md` and `test/hybrid_search.test.js` in their repo when building
the related CHIPS slice. No code import, no dependency, no standalone work item.

## Timing & gates

Opportunistic — activates only when a related slice is in flight.

## Consequences

- + Free design review against a convergently-evolved system with real adoption.
- − None (no dependency taken).
