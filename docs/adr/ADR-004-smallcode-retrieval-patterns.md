# ADR-004: smallcode Retrieval-Pattern Borrows

**Date:** 2026-06-05
**Status:** Accepted (borrow-only; no dependency)
**Tool:** https://github.com/Doorman11991/smallcode (Node.js coding agent for small local
LLMs; MIT; 1.8k★, 13 contributors, 27 test files, active)

## Context

smallcode is another agent runtime — not a peer of CHIPS and not something to identify
with — that happens to contain a few well-tested retrieval mechanisms: symbol-aware
chunking (snippets around functions/classes/types with sliding-window fallback),
token-budgeted snippet injection, and trace-to-test operator UX (`/trace`, `/eval`,
`/budget`).

## Decision

**Borrow only.** It is another agent runtime — wrong layer and language for adoption —
and its self-invented MarrowScript/BoneScript DSL stack is a maintenance liability to
stay away from. The retrieval/budget design, however, is read-before-build material.

## Purpose & fit

The borrow list is **closed** — these three items and nothing else (no "borrow anything
good we see"):

1. **Symbol-aware chunking + sliding-window fallback** → compare against CHIPS
   tree-sitter structural retrieval defaults.
2. **Bounded-injection pattern** ("combine scores then inject top bounded snippets") →
   reference for rank/compress boundary tuning.
3. **Trace-to-test / operator UX ideas** (`/trace`, `/eval`, `/budget`) → reference for
   future CHIPS operator surfaces.

Explicitly not borrowed: their hashed-vector embedding shortcut (pgvector is strictly
stronger) and everything else in the runtime.

## Scope

Read `docs/rag-harness.md` and `test/hybrid_search.test.js` in their repo when building
the related CHIPS slice. No code import, no dependency, no standalone work item.
Impossibility test applies: if the compaction/chunking value is achievable without
smallcode-inspired new machinery, the borrow stays a note.

## Timing & gates

Only when touching `structural.py` or the rank/compress boundary — not "whenever."

## Consequences

- + Free design review against a convergently-evolved system with real adoption.
- − None (no dependency taken).
