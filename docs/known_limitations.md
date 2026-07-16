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

## L6 — Source probes are synchronous and block every brief build — ✅ RESOLVED

> **Resolved** via a short-TTL probe cache on `BriefBuilder`. `_probe_cached` reuses the last
> `probe_runtime()` / `probe_workflow()` result for `_PROBE_CACHE_TTL_SECONDS` (30s) instead of
> re-probing on every `build()`, so repeated builds within the window no longer pay the probe
> timeout. A TTL cache was chosen over `asyncio.gather` deliberately: the module has no other
> async code, so wrapping two blocking calls in a thread pool for one call site adds more
> machinery than the problem warrants. Covered by `test_build_probes_runtime_and_workflow_on_first_call`,
> `test_build_does_not_reprobe_within_ttl_window`, and `test_build_reprobes_after_ttl_expires`
> in `tests/compiler/test_builder.py`. Original report below.

**Location:** `src/chips/compiler/builder.py` — `probe_runtime()` and `probe_workflow()`  
**Behavior (original):** Every `build()` call blocked on two sequential network probes.
`probe_runtime` has a 1s HTTP timeout; `probe_workflow` has a 2s connect timeout.  
**Worst case:** ~3s of additional latency per build when both sources are slow but reachable.  
**When it becomes a defect:** Any SLA on brief generation latency below ~4s.  
**Follow-up done:** Cached probe results with a short TTL (30s). Concurrency via
`asyncio.gather` was considered and rejected as heavier than needed for this one sync call site.

---

> Limitations below (L7–L10) were added on 2026-05-31 during the branch reconciliation of
> `feat/evidence-hypothesis-primitives`, after the Phase 0 substrate (`c79bd74`) and the
> feedback/health/learning batch (`ab14476`) landed. They are accepted for the foundation
> merge and tracked as follow-up slices.

---

## L7 — Finding evidence IDs are still positional (`finding:{index}`) — ✅ RESOLVED

> **Resolved** by commit `2e1231e` ("feat(builder): stable find:<content-hash> IDs for soft
> findings (Slice 0, §A)", 2026-05-31). `evidence.finding_evidence_id(finding)` now produces
> `find:<content-hash>` from the exact per-kind normalized field set locked in contract §A;
> `_extract_brief_signals` threads `(find_id, text)` pairs throughout and the old
> `SoftContextItem(item_id=f"finding:{index}")` call site no longer exists. Cross-build
> stability, order-independence, and no-collision-across-kinds are covered by
> `tests/unit/test_finding_evidence_ids_wiring.py` (53 tests across the related suite green).
> Original report below.

**Location:** `src/chips/compiler/builder.py` — `SoftContextItem(item_id=f"finding:{index}")`  
**Behavior (original):** Findings were assigned position-based IDs, not the stable
`find:<content-hash>` scheme mandated by the Phase 1 contract §A. The same finding got a
different ID across two builds whenever upstream ordering changed.  
**When it becomes a defect:** Any cross-build ID matching — write-back reinforcement, hypothesis
`cited_evidence` validation, or de-duplication — keyed on a finding ID. §A calls this fix the
mandatory prerequisite "before anything else in this phase."  
**Follow-up done:** Slice 0 (D2) — threaded the structured finding dict through
`_extract_brief_signals` and assigned `evidence.finding_evidence_id(...)` over a per-kind
normalized field set (locked in contract §A). Removes this limitation.

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

## L9 — Constraint substrate lacked an MCP surface — ✅ RESOLVED

> **Resolved.** The MCP/operator surface now exists via
> `src/chips/mcp/tools/constraints.py` and `src/chips/mcp/modules/constraints.py`,
> with bus registration in `src/chips/mcp/bus.py`. Agents can now inspect, add,
> and retire tenant-scoped constraints through `get_constraints`,
> `add_constraint`, and `retire_constraint`. The remaining work is higher-level
> write-back/review-queue plumbing, not raw operator reachability.

---

## L10 — Harvester enrichment tests assume undeclared optional analyzers — ✅ RESOLVED

> **Resolved.** `vulture` and `griffe` are now declared dependencies (commit `831b6af`), and
> `pyrefly` is declared as well (enrichment-reliability slice, `slice/enrich-reliability`). All
> three are installed via `uv sync`, so the detector tests no longer depend on ambient tooling.
> Original report below.

**Location:** `tests/harvester/enrichment/test_dead_code.py`, `test_api_surface.py`  
**Behavior (original):** The detectors degrade gracefully (`dead_code.py` returns `[]` when
`vulture` is absent; `api_surface.py` needs `griffe`), but `vulture` and `griffe` were **not
declared** in `pyproject.toml` / `uv.lock`. With the tools absent the detectors returned nothing
and 10 tests failed (`assert 'unused_a' in set()`).  
**Follow-up done:** declared the deps; additionally, the enrichment-reliability slice replaced
the silent empty-on-failure behaviour with an explicit `AnalyzerStatus` (`ok` / `not_installed`
/ `failed` / `timed_out` / `skipped`). `dead_code` / `api_surface` expose a `last_status`
property; `pyrefly`/`type_checker` add a `status` key to their result dict; the pipeline
surfaces all of these via `EnrichmentResult.analyzer_status`. A genuine clean run (`ok`,
findings empty) is now distinguishable from a non-result, upholding "Evidence > Guessing".

---

## L11 — Several enrichment analyzers swallowed failures — ✅ SUBSTANTIALLY RESOLVED

> **Resolved for the currently audited analyzers/enrichers.** `semgrep`,
> `security` (bandit), `architecture` (import-linter), `clones` (jscpd),
> `complexity` (lizard), `joern`, `api_surface` (griffe), `dead_code`
> (vulture), `coverage_reader`, `ownership`, `semble`, `graphify`,
> `scope_memories`, and `cochange` now expose truthful status and the pipeline
> propagates it through `EnrichmentResult.analyzer_status` where applicable.
> Empty results no longer automatically imply a clean run for these audited
> surfaces.
>
> **Remaining caution:** this closes the false-clean behavior for the analyzers
> named in this limitation. It does not claim every present or future analyzer in
> the repo already follows the contract without audit.

---

## L12 — Anti-regression review queue is durable, but not yet verifier-driven end to end

**Location:** `src/chips/mcp/tools/hypotheses.py`,
`src/chips/compiler/constraint_candidate_repository.py`  
**Behavior:** Rejected hypotheses now persist durable `ConstraintCandidate`
review rows and can be listed/reviewed later, but CHIPS still does not connect
that queue to verifier outcomes or automatic reinforcement/retirement logic.
Human review and manual promotion remain the controlling mechanism.  
**When it becomes a defect:** The first workflow that expects accepted/rejected
execution outcomes to automatically retire constraints, reinforce known-good
signals, or otherwise close the anti-regression loop without explicit operator
action.  
**Follow-up:** Tie queue review semantics to the eventual verifier/human-outcome
path, while preserving the invariant that no active constraint is created
without manual confirmation through `add_constraint`.

---

## L13 — Harvester incremental cursor is global, not per-repo — multi-repo needs DB isolation

**Location:** `src/chips/harvester/storage.py` — `PostgresHarvesterStore.latest_ingested_sha()`  
**Behavior:** The since-pointer is `SELECT sha FROM cortex_git_commits ORDER BY committed_at
DESC LIMIT 1` — no repo or `tenant_id` filter. `cortex_git_commits` has a `tenant_id` column
but the harvest path (`HarvesterDaemon.run_once` → `GitIngestion` → `MemoryRepository.insert`)
never sets it. So two repos harvested into the same database share one incremental cursor:
repo B's `run_once` reads repo A's newest SHA, passes it to `GitReader.commits_since` (where it
is not a valid ref in B), and the incremental math is corrupted.  
**When it becomes a defect:** The moment more than one repo is harvested into a single database.
**Workaround in use (2026-07-16):** one dedicated database per repo in `chips-prod-postgres`
(`chips_backend`, `chips_chat`, `chips_staec`, `chips_bproxy`), driven by
`scripts/ops/harvest-in-wsl-docker.sh`. Each database has exactly one repo, so the global cursor
is correct within it.  
**Follow-up:** Thread `tenant_id` (one per repo) through the harvest write path and scope
`latest_ingested_sha()` (and the retrieval-side reads) by it, so a single database can hold many
repos. Then collapse the per-repo databases into one multi-tenant store.
