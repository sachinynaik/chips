# ADR-003: Operator-Loop Output Compaction Bake-Off (`zap` vs `RTK`)

**Date:** 2026-06-05 (revised same day per Codex review)
**Status:** Companion-tooling bake-off approved — explicitly NOT on the product roadmap
critical path
**Tools:** `zap` — https://github.com/bitan-del/zap (Rust CLI, Apache-2.0, very young:
6 commits, solo author, no test suite/CI as of 2026-06-05) · `RTK` —
https://github.com/rtk-ai/rtk (Rust CLI, Apache-2.0, higher adoption, richer command
coverage, maturity to be validated by spike rather than inferred from stars)

## Context

Operating CHIPS development burns tokens on noisy command output: WSL container test
runs, docker/service logs, act pre-push gate output, CI failure dumps. `zap` and `RTK`
are both local CLI proxies that compact command output before it reaches an AI agent.
This is strictly an operator-loop concern: wrong layer for CHIPS core, but a legitimate
dev-machine efficiency slot.

The important split is not vendor A vs vendor B. It is **two command classes wearing one
label**:

1. **Interactive shell output** — latency-sensitive, conversational, frequently discarded.
2. **CI/test logs** — bulk, structured, failure-anchored, where the failing assertion and
   its context matter more than uniform compression.

A tool that is good at one may be wrong for the other. The bake-off therefore tests both
classes separately and explicitly allows **one winner, both for different classes, or
neither**.

## Decision

**Companion-tooling bake-off.** Run `zap` and `RTK` on CHIPS's own noisy operator
outputs and compare token savings vs information loss by command class. This is a
workflow companion decision, not a CHIPS dependency decision: wrong language (Rust) and
wrong layer (output-side shell proxy) for integration into the compiler.

## Purpose & fit

- **Purpose:** cut the operator token bill of developing/running CHIPS.
- **Fit:** thematically adjacent (CHIPS compresses input-side context; these tools
  compact output-side telemetry) but architecturally disjoint — no shared substrate.

## Scope

- **In (bake-off):** test-log summarization, docker/service logs, act/CI failure
  compaction; a savings-vs-loss measurement on real CHIPS sessions.
- **Out (hard rule):** any path where exact raw output is contractually required —
  golden tests, byte-identical determinism checks, normalization conformance output,
  anything feeding assertions. CHIPS's determinism expectations mean any filter must be
  explicitly allowed per command class, never default-on.

## Approach

**Borrow / compare.** If the bake-off shows real savings, adopt one tool, both tools for
different command classes, or neither. The outcome is intentionally not forced to a
single winner. Recoverability of full output and exit-code fidelity are hard gates for
both candidates.

## Timing & gates

Anytime — it touches the operator loop only, so it can interleave with Foundation work
without violating the Foundation-first rule.

**Locked bake-off rubric**

- Evaluate **interactive shell output** and **CI/test logs** separately.
- Measure three things per class:
  1. token/output reduction,
  2. recoverability of full output,
  3. exit-code fidelity.
- Hard gates for either tool:
  - **recoverability** must work for the tested class,
  - **exit-code fidelity** must hold exactly,
  - the tool must not hide needed error detail on or near the exclusion list.

**Allowed outcomes**

- `zap` wins both classes,
- `RTK` wins both classes,
- each wins a different class,
- neither is adopted.

**Kill criterion:** abandon a candidate for a class if it hides needed error detail even
once on or near the exclusion list, fails recoverability, or fails exit-code fidelity.
Time budget: 0.5 day.

## Consequences

- + Cheap, immediate, measurable token savings on the noisiest part of the dev loop.
- + The split by command class prevents optimizing the average while failing the tails.
- − A filter between operator and agent is a new failure mode (hidden signal); mitigated
  by per-class hard gates on recoverability, exit-code fidelity, and the raw-output
  exclusion rule.
