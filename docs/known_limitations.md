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

---

> Limitations below (L7–L10) were added on 2026-05-31 during the branch reconciliation of
> `feat/evidence-hypothesis-primitives`, after the Phase 0 substrate (`c79bd74`) and the
> feedback/health/learning batch (`ab14476`) landed. They are accepted for the foundation
> merge and tracked as follow-up slices.

---

## L7 — Finding evidence IDs are still positional (`finding:{index}`)

**Location:** `src/chips/compiler/builder.py` — `SoftContextItem(item_id=f"finding:{index}")`  
**Behavior:** Findings are assigned position-based IDs, not the stable `find:<content-hash>`
scheme mandated by the Phase 1 contract §A. The same finding gets a different ID across two
builds whenever upstream ordering changes.  
**When it becomes a defect:** Any cross-build ID matching — write-back reinforcement, hypothesis
`cited_evidence` validation, or de-duplication — keyed on a finding ID. §A calls this fix the
mandatory prerequisite "before anything else in this phase."  
**Follow-up:** Slice 0 (D2) — thread the structured finding dict through `_extract_brief_signals`
and assign `evidence.finding_evidence_id(...)` over a per-kind normalized field set (locked in
contract §A). Removes this limitation.

---

## L8 — Learning adjustment can trip the governor on the confidence-fallback path — ✅ RESOLVED 2026-05-31

> **Resolved** by extracting `_apply_learning_adjustments` (sets only
> `learning_adjustment`, never mutates `confidence`). The governor now always reads the
> raw retrieval score per its contract, and the ranker no longer double-counts the
> adjustment. See `tests/unit/test_learning_governor_decoupling.py`. Original report below.


**Location:** `src/chips/compiler/builder.py` (learning applied to `memory["confidence"]`) →
`src/chips/compiler/governor.py` (mean-confidence short-circuit)  
**Behavior:** `BriefLearningService` adjusts each memory's `confidence` from outcome history.
The governor keys on `similarity` when present, but **falls back to `confidence`** when it is
absent — so on that fallback path accumulated feedback (+0.05/acceptance, up to +0.5) can push
mean confidence over the governor threshold and short-circuit secondary evidence (file_signals,
diffs, structural).  
**When it becomes a defect:** Any retrieval path that returns memories without a `similarity`
score; learned-good memories then silently suppress fresh evidence sources.  
**Follow-up:** Either always populate `similarity`, or have the governor ignore the
learning-adjusted component of confidence. The learning loop itself is sanctioned — see roadmap
§3.3. Tracked as D3.

---

## L9 — Constraint substrate has no MCP add/retire surface

**Location:** `src/chips/compiler/constraint_repository.py` (read path only)  
**Behavior:** `ConstraintRepository.for_scope` loads active `cortex_constraints` and the builder
injects them, but there is **no `cortex_add_constraint` / `get_constraints` MCP tool**.
Constraints can only enter the table via direct SQL or a migration. The Phase 0 deliverable's
"manual add/retire" capability is therefore not yet reachable by an agent.  
**When it becomes a defect:** Immediately for the Phase 1 write-back review queue, whose
invariant ("constraints created only via `cortex_add_constraint`, human-confirmed") has no sink.  
**Follow-up:** D4 — add the constraint MCP tools (add/get, tenant-scoped, dedup-safe).

---

## L10 — Harvester enrichment tests assume undeclared optional analyzers

**Location:** `tests/harvester/enrichment/test_dead_code.py`, `test_api_surface.py`  
**Behavior:** The detectors degrade gracefully (`dead_code.py` returns `[]` when `vulture` is
absent; `api_surface.py` needs `griffe`), but `vulture` and `griffe` are **not declared** in
`pyproject.toml` / `uv.lock`. With the tools absent the detectors return nothing and 10 tests
fail (`assert 'unused_a' in set()`). Pre-existing on master (detector sources untouched since
`6eef2e9`); independent of this branch.  
**When it becomes a defect:** CI green-ness depends on whichever environment happens to have the
tools installed.  
**Follow-up:** Separate test-hygiene slice off master — `pytest.skip` when the optional tool is
absent (matches the detectors' own graceful-degradation contract), or declare the deps. Not
fixed on this branch (off-topic).
