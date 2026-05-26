# Known Limitations and Deferred Design Debt

Recorded as part of the Gap 1–5 implementation review (2026-05-26).
These are accepted risks, not oversights. Each has a stated condition under which it becomes a defect.

---

## L1 — tenant_id=None permits cross-tenant reads

**Location:** `src/chips/compiler/retrieval.py` — all four retrieval functions  
**Behavior:** `tenant_id=None` applies no tenant filter. Any caller that omits the parameter
receives results across all tenants.  
**Production gate:** `CHIPS_REQUIRE_TENANT_ID` environment variable forces a `ValueError` at
`BriefBuilder.build()` entry. All production deployments must set this variable.  
**When it becomes a defect:** Any production entrypoint that does not enforce
`CHIPS_REQUIRE_TENANT_ID`, or any internal path (scheduled jobs, backfill scripts) that
calls `build()` directly without the env var set.  
**Follow-up:** Consider a shared `_apply_tenant_clause(conditions, params, tenant_id)` helper
and a `@require_tenant` decorator for public entrypoints.

---

## L2 — Tenant predicate logic is duplicated across four retrieval functions

**Location:** `retrieve_memories`, `retrieve_file_signals`, `retrieve_diffs`,
`retrieve_cochanges` in `src/chips/compiler/retrieval.py`  
**Behavior:** Each function hand-rolls the same three-line conditions/params pattern.  
**When it becomes a defect:** The first edit that changes one function but not the others.
One missed `tenant_id` clause reopens the L1 exposure silently.  
**Follow-up:** Extract a `_tenant_clause(tenant_id) -> tuple[str, list]` helper. v2 refactor.

---

## L3 — not_configured overloaded for missing caller input (file_signals)

**Location:** `src/chips/compiler/builder.py` — `file_signals_status` assignment  
**Behavior:** `not_configured` is used when no `files` argument is passed to `build()`. The
same vocabulary is also used for missing env vars (`SIGNOZ_API_URL`, `DBOS_DB_URL`).
The `detail` field disambiguates (`"no files provided to build()"`), but the status term
itself implies infrastructure misconfiguration rather than caller omission.  
**When it becomes a defect:** Any consumer that branches on `status == "not_configured"` and
treats all cases identically.  
**Follow-up:** Introduce `"not_provided"` as a distinct status value for caller-supplied
inputs in a future schema version (increment `schema_version`).

---

## L4 — cortex_brief_outcomes has no foreign key to cortex_briefs

**Location:** `migrations/versions/004_add_brief_outcomes_table.py`  
**Behavior:** Outcome rows reference `brief_id` by value with no FK constraint. Outcomes for
deleted or non-existent briefs are retained.  
**When it becomes a defect:** The first feature that uses outcome counts or ratios as a
confidence signal. Orphan rows inflate denominators or introduce phantom confidence.  
**Follow-up:** Add FK constraint (with `ON DELETE SET NULL` or `ON DELETE CASCADE`) when
brief deletion becomes a supported operation. Add a background cleanup job or view that
excludes orphan outcomes.

---

## L5 — BriefOutcomeRepository.record() permits duplicate submissions

**Location:** `src/chips/memory/outcome_repository.py`  
**Behavior:** No `UNIQUE` constraint exists on `(brief_id, outcome)` or any compound key.
Callers can submit the same outcome for the same brief multiple times.  
**When it becomes a defect:** Any aggregation over outcomes (acceptance rate, confidence
score) that does not deduplicate by caller or timestamp.  
**Follow-up:** Add a unique constraint or explicit deduplication query at the first
aggregation consumer. Alternatively, add `actor_id` to the outcomes table and unique-index
on `(brief_id, actor_id)` if per-actor idempotency is the right model.

---

## L6 — Source probes are synchronous and block every brief build

**Location:** `src/chips/compiler/builder.py` — `probe_runtime()` and `probe_workflow()`  
**Behavior:** Every `build()` call blocks on two sequential network probes. `probe_runtime`
has a 1s HTTP timeout; `probe_workflow` has a 2s connect timeout.  
**Worst case:** ~3s of additional latency per build when both sources are slow but reachable.  
**When it becomes a defect:** Any SLA on brief generation latency below ~4s.  
**Follow-up:** Cache probe results with a short TTL (e.g. 30s) or run probes concurrently
with retrieval using `asyncio.gather`. v2 enhancement.
