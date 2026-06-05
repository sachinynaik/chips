# ADR-008: HRM-Text — Reject the Vehicle, Keep the Ambition

**Date:** 2026-06-05
**Status:** Rejected (ambition deferred; new ADR required when picked up)
**Tool:** https://github.com/sapientinc/HRM-Text (1B-param hierarchical-recurrent LM
pretraining framework; Apache-2.0; ~1.1k★; checkpoint: `sapientinc/HRM-Text-1B`)

## Context

Proposal: train HRM-Text on the CHIPS codebase and use it as a small local copilot.

Findings (verified 2026-06-05):

- HRM-Text-1B was pretrained on **40B tokens of general English text, not code**; the
  model card states weak coding performance is expected. The only code-SFT results are
  third-party and unreleased.
- Reference training is 8–16× H100 with FlashAttention-3 (Hopper-class); the available
  GPU is a single 16GB RTX 4070 Ti SUPER (Ada) — neither the scale nor the kernel path
  fits.
- A ~15k-LOC repo is ~150–400k tokens: roughly five orders of magnitude below the
  architecture's pretraining recipe. Fine-tuning the code-naive checkpoint on it would
  memorize, not generalize.
- The ARC Prize ablations (arcprize.org/blog/hrm-analysis) found HRM's hierarchy itself
  contributes little (a plain transformer comes within ~5pp); gains came from the outer
  refinement loop and per-task training. No published evidence exists of HRM at
  copilot-grade code generation.

All three independent evaluations (this assessment, Claude chat, Codex) converged on
reject — Codex's framing: CHIPS's bottleneck is evidence quality, enforcement, and
learning loops, not "we lack our own model."

## Decision

**Reject HRM-Text as the vehicle.** This ADR is a rejection record, not a design for a
replacement. The underlying ambition — a small *local* model that knows the codebase —
is deferred; the candidate direction noted for the trail is a small pretrained code
model fed by CHIPS-as-RAG. Vehicle choice, serving stack, and evaluation design belong
to a **future ADR if and when the ambition is picked up** — nothing here authorizes
work on it.

## Timing & gates

Deferred indefinitely; requires its own ADR when picked up.

## Consequences

- + No spend on pretraining-scale infrastructure for a code-naive architecture.
- + The ambition's trail is preserved without smuggling speculative architecture into a
  rejection record.
