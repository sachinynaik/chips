# ADR-003: zap for Operator-Loop Output Compaction

**Date:** 2026-06-05
**Status:** Proposed — spike approved in principle, schedule freely (off critical path)
**Tool:** https://github.com/bitan-del/zap (Rust CLI, Apache-2.0, very young: 6 commits,
solo author, no test suite/CI as of 2026-06-05)

## Context

Operating CHIPS development burns tokens on noisy command output: WSL container test
runs, docker/service logs, act pre-push gate output, CI failure dumps. zap is a local
CLI proxy that filters/groups/deduplicates command output via per-command TOML recipes
(~60 recipes, 42+ command types) before it reaches an AI agent, claiming 60–90% savings.

## Decision

**Borrow / companion spike.** Run it on CHIPS's own noisy operator outputs and measure
token savings vs information loss. It is a *workflow companion*, not a CHIPS dependency:
wrong language (Rust) and wrong layer (output-side shell proxy) for integration into the
compiler.

## Purpose & fit

- **Purpose:** cut the operator token bill of developing/running CHIPS.
- **Fit:** thematically adjacent (CHIPS compresses input-side context; zap compresses
  output-side telemetry) but architecturally disjoint — no shared substrate.

## Scope

- **In (spike):** test-log summarization, docker/service logs, act/CI failure
  compaction; a savings-vs-loss measurement on real CHIPS sessions.
- **Out (hard rule):** any path where exact raw output is contractually required —
  golden tests, byte-identical determinism checks, normalization conformance output,
  anything feeding assertions. CHIPS's determinism expectations mean any filter must be
  explicitly allowed per command class, never default-on.

## Approach

**Borrow.** If the spike shows real savings, adopt as an opt-in operator tool (and/or
lift its recipe-driven deterministic-compaction *pattern* for future CHIPS operator
tooling). Maturity (no tests, solo, week-old) is acceptable for a dev-loop companion;
it would not be acceptable for anything load-bearing.

## Timing & gates

Anytime — it touches the operator loop only, so it can interleave with Foundation work
without violating the Foundation-first rule. Gate for *adoption* (vs spike): measured
savings with no observed information loss on the deterministic-path exclusion list.

## Consequences

- + Cheap, immediate, measurable token savings on the noisiest part of the dev loop.
- − A filter between operator and agent is a new failure mode (hidden signal); mitigated
  by the per-command allowlist and the raw-output exclusion rule.
