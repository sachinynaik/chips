# ADR-005: opensquilla Hybrid-Recall Borrow

**Date:** 2026-06-05
**Status:** Accepted (borrow-only; no dependency)
**Tool:** https://github.com/opensquilla/opensquilla (Python agent runtime; Apache-2.0;
3.2k★ — partly promotional star-campaign; effective bus factor ~2; real test suite)

## Context

opensquilla is a full agent runtime (peer product, not a dependency candidate), but its
memory recall is a worked example of multi-lane retrieval: hybrid **BM25 (SQLite FTS) +
vector (sqlite-vec)** with normalized scores and a **keyword fallback when vector
confidence is low**, over a four-tier memory taxonomy (working/episodic/semantic/raw).

This matters because CHIPS's retrieval is going multi-lane (locked 2026-06-05): a
semantic lane (embeddings + structural) AND/OR a contract lane (exact
`domain_action_entity_parameter` token match), selected per codebase instrumentation.
The contract lane is the deterministic extreme of lexical retrieval; opensquilla's
lane-combination and fallback logic is the nearest worked reference for *how lanes
compose and when one overrides another*.

## Decision

**Borrow only** — the lane-fusion/fallback design and tiered-memory taxonomy as
references for the multi-lane retriever slice. Its router is a static LightGBM/ONNX
classifier — nothing for CHIPS's contextual-bandit loop, which remains ahead of
anything surveyed.

## Scope

Read their hybrid-recall implementation and score-normalization choices when designing
the CHIPS multi-lane retriever (lane fusion, fallback thresholds, per-lane confidence).
No code import, no dependency.

## Timing & gates

Activates with the multi-lane retriever slice (post-Foundation, after the contract-lane
thesis spike).

## Consequences

- + A tested lane-fusion reference instead of designing fusion from scratch.
- − None (no dependency taken).
