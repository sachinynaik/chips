# ADR-005: opensquilla — Borrow Hybrid Lexical/Vector Fallback Heuristics Only

**Date:** 2026-06-05 (shrunk same day per Codex review)
**Status:** Accepted (narrow borrow-only; no dependency)
**Tool:** https://github.com/opensquilla/opensquilla (Python agent runtime; Apache-2.0;
3.2k★ — partly promotional; effective bus factor ~2)

## Decision

**Borrow one thing:** the hybrid lexical (BM25) + vector recall mechanics — score
normalization and the *keyword fallback when vector confidence is low*. That fallback
heuristic is the only part with a plausible mapping to CHIPS's multi-lane retriever
(lane fusion, per-lane confidence, when one lane overrides another).

Nothing else: opensquilla is a peer agent runtime, not a dependency candidate; its
memory taxonomy is not obviously useful to CHIPS; its router is a static classifier with
no relevance to the bandit loop.

## Timing

Only when designing the multi-lane retriever slice, and only after the contract-lane
thesis spike passes. No standalone work item.
