# CHIPS Cortex — v1 Foundation Milestone

**Date:** 2026-05-28  
**Branch:** `feat/evidence-hypothesis-primitives`  
**Status:** Foundation shipped, staged batch pending review

---

## What Shipped

### Gaps 1–5 (core compiler pipeline)

| Gap | Capability | Key files |
|-----|-----------|-----------|
| Gap 1 | Feedback loop — `cortex_brief_outcomes` table and repository | `memory/outcome_repository.py`, migration 001 |
| Gap 2 | Explicit file-signal contract in `BriefBuilder` | `compiler/builder.py` |
| Gap 3 | Deterministic compression — rank, trim, cap | `compiler/compressor.py`, `compiler/ranker.py` |
| Gap 4 | Synchronous source-availability probes (runtime, workflow) | `mcp/tools/runtime.py`, `mcp/tools/workflow.py` |
| Gap 5 | `tenant_id` threaded through `BriefBuilder` and all retrieval paths | `compiler/retrieval.py`, `compiler/builder.py` |

### Agent A release bar (audit and hardening)

All four release gates closed before merge:

1. **Tenant isolation tests at every public entrypoint** — `BriefModule.get_context_brief`, `server.get_context_brief`, and `server.submit_brief_feedback` all covered.
2. **Explicit error message stability** — `ValueError` text is asserted to contain both `"tenant_id"` and `"CHIPS_REQUIRE_TENANT_ID"`.
3. **`data_sources` wire contract snapshot-tested** — shape (keys + vocabulary), known source keys (`runtime`, `workflow`, `file_signals`), and status values (`not_configured | available | unavailable | error`) all locked.
4. **Accepted risks written into `docs/known_limitations.md`** as tracked managed debt with explicit defect conditions.

### Evidence bundle + hypothesis contract (`86caf4d`)

Pure-layer primitives for the reasoning runtime:

- `compiler/models.py`: `EvidenceItem`, `EvidenceBundle`, `Hypothesis`, `ConstraintCandidate`
- `compiler/evidence.py`: stable evidence IDs including `find:<content-hash>` (guarded `make_evidence_id`)
- `compiler/hypothesis.py`: deterministic coverage/contradiction/corroboration ranking with tie-breaks
- Docs: locked Phase 1 contract (`27_05_phase1_evidence_hypotheses_contract.md`) and reasoning-runtime roadmap
- 38 unit tests, 100% coverage on new modules

---

## Six Managed Debts (from `docs/known_limitations.md`)

These are accepted risks for v1, each with a stated defect condition:

| ID | Location | Risk | Defect condition |
|----|----------|------|-----------------|
| L1 | `retrieval.py` | `tenant_id=None` permits cross-tenant reads | Any production entrypoint missing `CHIPS_REQUIRE_TENANT_ID` |
| L2 | `retrieval.py` | Tenant predicate duplicated across 4 retrieval functions | First edit that changes one function but not the others |
| L3 | `builder.py` | `not_configured` overloaded for caller omission (`file_signals`) | Any consumer branching on status without reading `detail` |
| L4 | migrations | No FK from `cortex_brief_outcomes` to `cortex_briefs` | First aggregation using outcome counts as a confidence signal |
| L5 | `outcome_repository.py` | `record()` permits duplicate submissions (no idempotency key required) | Any aggregation that doesn't deduplicate |
| L6 | `builder.py` | Source probes synchronous — block every `build()` call | Any SLA on brief generation below ~4s |

L5 is partially addressed in the staged batch (idempotency key is now optional, not missing — see below).

---

## In-Flight: Staged Batch (pending commit)

The following is staged but not yet committed. It builds on the Gaps 1–5 foundation without reopening any of those gaps:

**Feedback + health surface:**
- `mcp/modules/feedback.py`, `mcp/modules/health.py` — new MCP modules
- `mcp/tools/health.py`, `mcp/tools/health_tracker.py` — source health aggregation
- `mcp/test_feedback_tool.py`, `mcp/modules/test_feedback_module.py`, `mcp/modules/test_health_module.py`

**Learning service:**
- `compiler/learning.py` — `BriefLearningService`: loads per-item score adjustments from outcome history and applies them to memory retrieval scores. Triggered after each feedback submission.
- Migration 006: `learning_score`, `compression_trace` columns

**Outcome repository hardening:**
- `memory/outcome_repository.py` — added `idempotency_key` param (addresses L5 partially), tenant validation, `record_with_ack()` returning a typed `OutcomeAck`
- Migration 005: `idempotency_key`, `attribution` columns

**Tenant helper:**
- `compiler/tenant.py` → `chips/tenant.py` — `require_tenant()` extracted from `builder.py` inline check, reused at all entrypoints

**Wire contract:**
- `mcp/modules/brief.py`, `mcp/server.py` — `data_sources` serialized with `checked_at` field
- `mcp/tools/diffs.py` — tenant filtering

---

## Next Work Order

Work should proceed in this order, treating each as an independent slice:

### 1. Anti-regression constraint substrate (Phase 0 — pure layer)

**What:** Durable `cortex_constraints` table as the policy store injected into `hard_constraints` at build time.

**Scope:** `compiler/constraints.py` (pure helpers), `compiler/constraint_repository.py` (DB queries), `compiler/governor.py` (short-circuit retrieval on high-confidence memory), `compiler/reranker.py` (flashrank cross-encoder re-scoring), `compiler/structural.py` (structural context items), migration 007.

**Why first:** Everything downstream (MCP constraint tools, hypothesis ranking at build time) depends on having a queryable, dedup-safe constraint store. This is the load-bearing layer.

**Contract:** Locked in `27_05_phase1_evidence_hypotheses_contract.md §H`. Pure layer only — no builder wiring until Phase 1.

### 2. MCP constraint tools (Phase 0 — wire)

**What:** `get_constraints` tool registered on the MCP bus. Queried by scope, returns active constraints filtered by tenant. Enables Claude Code to inspect the current constraint set.

**Scope:** `mcp/tools/constraints.py`, `mcp/modules/constraints.py`, bus registration, tests.

### 3. Constraint injection at build time (Phase 1 — builder wiring)

**What:** `BriefBuilder.build()` loads active constraints via `ConstraintRepository`, passes them through `assemble_hard_constraints()` and `assemble_forbidden_edits()`, and stores `compression_trace` + `governor_decision` on the brief.

**Scope:** `compiler/builder.py` wiring, `compiler/governor.py` integration, updated `ContextBrief` model, migration to add `governor_decision` column.

**Dependency:** Requires constraint substrate (1) and the staged-batch learning service to be landed.

### 4. Stack-aware adapters (Phase 2 — external sources)

**What:** OTel/SigNoz span ingestion, DBOS workflow state, GoRules decision outcomes as evidence sources for the hypothesis layer.

**Scope:** New evidence extractors per source, `EvidenceBundle` population at build time, hypothesis ranking wired into `ContextBrief.ranked_signals`.

**Dependency:** Requires hypothesis contract (already committed) and constraint injection (3).

---

## Decision Ledger

Decisions made during the v1 build that should not be relitigated without new information:

| Decision | Rationale |
|----------|-----------|
| `tenant_id=None` is allowed in dev mode | Forcing tenant in all paths would break single-tenant local installs. `CHIPS_REQUIRE_TENANT_ID` is the production gate. |
| Source probes are synchronous | Async would require migrating `BriefBuilder` to `async def build()`, breaking all callers. Sync + 2s timeout is acceptable for v1 SLA. |
| `not_configured` used for missing `files` arg | Caller-supplied inputs use the same vocabulary as infra misconfiguration. `detail` field disambiguates. Tracked as L3. |
| No FK on `cortex_brief_outcomes` | Brief deletion is not a supported operation in v1. FK constraint deferred until deletion semantics are defined. |
| `flashrank` reranker is optional, not required | Cross-encoder adds quality but must not block brief generation. Graceful degradation to original order if unavailable. |
| `BriefLearningService` triggers synchronously after feedback | Async recompute would require a task queue. Synchronous trigger is safe for v1 traffic; extract to background job when latency becomes an issue. |
