# Codex Remediation + Two-Initiative Plan (2026-05-31)

Status: **APPROVED — decisions locked**. Supersedes the open items in
`docs/28_05_v1_foundation_milestone.md` (which is now stale — see Slice A0).

## Source inputs
- **Codex review:** `Downloads/31_05_Codex findings about Chips.md` (9 findings + architecture
  assessment + 5-step plan). Reviewed a **pre-commit snapshot**; reconciled against HEAD below.
- **Research (Track C):** `docs/research/openkb-forge-assessment.md` — OpenKB/PageIndex + Forge.
- **Review harness (Track B):** `tools/multireview/` (built in worktree; multi-LLM reviewers +
  LLM-as-judge). Dev-workflow tool, zero product blast radius.

## Locked decisions
1. **Phase 1:** finish `EvidenceBundle` assembly+serialization now; **defer** the
   `cortex_submit_hypotheses` surface until Forge research is actioned (Phase 4).
2. **Experimental layers:** governor, reranker, structural retrieval → **opt-in config flags,
   OFF by default**. Core v1 default path = memories + diffs + constraints + compression.
3. **RL-readiness schema** (`weights_used`, `verification_reward`): **populate end-to-end**
   (ContextBrief model + `_persist()` + MCP wire), not remove.

---

## Reconciliation: Codex findings vs HEAD

| # | Finding | HEAD status | Note |
|---|---|---|---|
| 1a | Positional `finding:{i}` IDs | ✅ Fixed (`2e1231e`) | `_soft()`→`finding_evidence_id` (`builder.py:63,94,176`) |
| 1b | EvidenceBundle never built/surfaced | ❌ Open | Slice A1 |
| 3 | Learning adjustment double-counted | ✅ Fixed (`3b0ed7f`) | `_apply_learning_adjustments` keeps `learning_adjustment` separate; governor unbiased, ranker adds once. `test_learning_governor_decoupling.py` |
| 2 | File signals ranked but never emitted | ⚠️ Open | Slice A2a |
| 4 | Auditability half-done | ⚠️ Open | Slice A5a (populate per decision 3) |
| 5 | Structural keys symbols by bare name; arbitrary BFS anchors; own token heuristic | ⚠️ Open | De-risked by flagging OFF (A4); fix-before-re-enable (A6) |
| 6 | Reranker `top_n` unused; global cache; batch-relative scores | ⚠️ Open | De-risked by flagging OFF (A4); fix-before-re-enable (A6) |
| 7 | `retire()` always returns True | ⚠️ Open | Slice A2b |
| 8 | Feedback recompute synchronous on request path | ⚠️ Open | Slice A5b |
| 9 | Milestone docs outgrown | ⚠️ Open | Slice A0 |

---

## Organizing thesis
Codex's real diagnosis: *"the code is ahead of the plan, but behind the contracts it claims."*
`BriefBuilder.build()` is a god-method (retrieval + flag-routing + governor + policy + structural
+ rerank + compress + persist), which is why the branch drifted across phases. Fix =
**stabilize the deterministic core, demote experimental layers to opt-in, decompose the
orchestrator.** The two new initiatives are non-interfering tracks:

| Track | Touches product code | Feeds |
|---|---|---|
| A — Core stabilization | yes (critical path, strict TDD) | — |
| B — Multi-LLM review harness | no (isolated `tools/multireview/`) | becomes the review gate for A3 |
| C — Forge/OpenKB research | no (read-only) | gates re-investment in A6 + Phase 4 |

---

## Track A — sequenced TDD slices

Each slice = RED→GREEN→REFACTOR, one surgical commit (A3 is multi-commit), Codex/harness review.

### A0 · Docs truth-up + finding audit *(no behavior change)*
Fix `docs/28_05_v1_foundation_milestone.md` to reflect reality (kills Codex #9 "false sense of
completion" — the most dangerous finding because it misleads every later decision). Quick-confirm
#2,#4,#5,#6,#7,#8 still open against HEAD.

### A1 · EvidenceBundle completion (#1b) — *Phase 1 first prerequisite*
- RED: `build()` produces an `EvidenceBundle` whose evidence items carry the existing
  `find:<hash>` IDs; bundle serialized into `ContextBrief` and the MCP wire response.
- GREEN: assemble from `soft_additions` (already `(find_id, text)` pairs) → bundle → surface.
- Hypotheses submission surface **explicitly deferred** (documented in the contract doc).

### A2a · File signals: inject (#2)
File signals are retrieved + ranked but never become `SoftContextItems`. **Inject** them as
`category="file"` SoftContextItems so the paid retrieval/rank cost actually influences the brief.
(They are NOT in Codex's lean "core v1" list, so they ride behind the same plumbing but are a
legitimate signal — keep, don't discard the work.)

### A2b · `retire()` truthful (#7)
`ConstraintRepository.retire()` → check `rowcount`, match tenant, honor `superseded_by`
(column exists in migration 007). Return real success.

### A4 · Flag experimental layers OFF by default (decision 2)
Config-driven gates for governor / reranker / structural. Default path = memories + diffs +
constraints + compression. This **removes #5 and #6 from the hot path** (de-risk before fix).
Do this *before* A3 — flagged-off layers are easier to extract as adapters.

### A3 · Decompose `BriefBuilder` (architecture fix) — *plan it, not big-bang*
Extract `SourceCollector` / `PolicyAssembler` / `ContextAssembler` / `BriefPersister`. Governor,
reranker, structural become **adapters called by the collector**, not inline branches. Strangler-
fig: one boundary per sub-slice, suite stays green between each. **Review every sub-slice with the
Track B harness** (this is the riskiest work — blast radius Medium-High, debt reduction High).

### A5a · Auditability end-to-end (#4, decision 3)
Add `weights_used` + `verification_reward` to `ContextBrief`; write them in `_persist()`; widen the
MCP wire contract to also surface the already-on-model `forbidden_edits`, `allowed_edits`,
`governor_decision`, `compression_trace` (Codex: `server.py:38` drops these).

### A5b · Feedback recompute off the request path (#8)
`submit_brief_feedback()` → enqueue recompute instead of inline delete/rebuild; make it
tenant-lock aware (process-local throttle can't stop multi-worker stampede).

### A5c · One real merge gate
Full suite green, or an explicit fast vs DB-backed split. No more drift.

### A6 · Fix #5/#6 *before re-enabling* the flagged layers (informed by Track C)
- #5 structural: key symbols by `(file, name)` not bare name; relevance-driven anchors; use the
  exact token-budget path. For **doc** corpora, evaluate the PageIndex-style **offline section-tree
  as a rerank candidate source** (Track C rec) — deterministic, local, built once.
- #6 reranker: honor `top_n`; per-config instance (not global cache); stable (non-batch-relative)
  scores.

---

## Track B — multi-LLM review harness (`tools/multireview/`)
Built in worktree by background agent (review pending). Provider-agnostic `Reviewer` protocol
(Ollama local default + Claude/Codex), diversity by model × lens, LLM-as-judge convergence
(Claude/Codex final). Runs fully local with no cloud keys. **Adopt as the review gate for A3.**
Action after merge-review: confirm tests green at the 90% bar, then dogfood on the A1 slice.

## Track C — research outcomes (actionable)
- **Skip** OpenKB + PageIndex as dependencies/runtime retrievers (non-deterministic, cloud).
- **Borrow** the offline-tree idea for doc retrieval → A6.
- **Defer** Forge to Phase 4; borrow only `rescue_tool_call` (deterministic) then, after checking
  Ollama grammar-constrained decoding first.
- **New backlog item:** deterministic contradiction-flagging over structured findings (latent gap).

---

## Sequencing
```
A0 ─▶ A1 ─▶ A2a ─▶ A2b ─▶ A4 ─▶ A3 (multi-commit, reviewed by Track B) ─▶ A5a ─▶ A5b ─▶ A5c ─▶ A6
                                   ▲                                                          ▲
                          Track B merged here                              Track C gates re-investment
```
Open sub-decision (non-blocking): A2a assumes **inject** file signals; flag if you'd rather
demote them behind a config gate like the other experimental layers.
