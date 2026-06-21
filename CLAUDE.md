# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What CHIPS is

CHIPS CORTEX is deterministic engineering-cognition infrastructure: a sidecar that
*compiles* a focused `ContextBrief` for a coding task out of harvested repository signals,
rather than dumping raw context at a model. It is **compile-and-observe, not a model-call
interceptor** — borrowed pieces only compile, observe, or record; they never intercept the
reward or the model call. Python 3.13, `uv`, Postgres/pgvector.

## Read these before trusting any design doc (built vs target)

The `docs/` folder is **design-converged, not uniformly implemented**. It describes two
lineages: a **BUILT** Postgres/pgvector context-compiler that actually runs, and a **TARGET**
CORTEX end-state (Signoff gate, Oxigraph/Cognee/Qdrant/Letta, Promote→Tapeout) that is mostly
*not built*. Do not read aspirational design as shipped code. The authority chain:

1. `docs/implementation_tracking.md` — **the current-state truth layer.** Layer-by-layer
   built / partial / blocked / deferred / target-only map. Start here.
2. `docs/adr/A0-architecture-reconciliation.md` — the two-lineage reading convention and the
   canonical vocabulary (single source of truth for terms).
3. `docs/02_06_execution_ledger.md` — **the readiness gate.** A capability may not be built
   until its row is `active`. Reward-consuming work (composite_reward, mastery, OPE, online
   bandit, rule induction) is **blocked on the Phase-3 verifier** — do not build it early.
4. `docs/design_docs/18_06/chips-execution-decision-sheet.md` — the current execution program.
5. `docs/known_limitations.md` — accepted debt, each with the condition under which it becomes
   a real defect.

**Vocabulary discipline (A0 §2):** the gate is "Signoff" (not trust_tier/triage/clearance);
a "fault signature" (not "biomarker"); truth memory is Oxigraph (Apache **AGE was removed**);
"Tapeout" names Promote→Truth **only**, never Execute. Some `design_docs/` still carry the dead
terms — A0 is authoritative over them. **Do not describe any existing constraint-injection or
brief validation as "the gate" — the Signoff gate does not exist yet.**

## Commands

Uses Python 3.13 + `uv`.

- `uv sync --extra dev` — install runtime + dev deps (faithful, lockfile-pinned; CI uses this).
- `uv run pytest -q` — full suite.
- `uv run pytest tests/path/test_file.py::test_name` — a single test.
- `uv run coverage run -m pytest && uv run coverage report` — coverage; **fails under 90%**.
- `uv run alembic upgrade head` — apply migrations (`migrations/versions/`).
- `uv run python -m chips.mcp.bus` — start the MCP server (the one runnable entry point).

CI lives in `.github/workflows/ci.yml` and runs locally first (pre-push `act`/`actgpu` hook)
then on the self-hosted GPU runner. Commit/push with plain `git` — the local hooks are the gate.

### Database-backed tests (a real gotcha)

`tests/conftest.py` + `src/chips/testing/db_harness.py` resolve the test DB by precedence:

- `CHIPS_TEST_DB_URL` set → **explicit** mode (fast dev loop against a persistent DB).
- else `CHIPS_TEST_DB_ROOT_URL` set + reachable → **root** mode (creates/drops a temp DB).
- else → **container** mode (testcontainers spins up `pgvector/pgvector:pg16`).

Every test gets a connection that **rolls back after the test**, so backends never leak state.
Note: some dirs (`tests/unit`, `tests/compiler`) no-op the autouse `apply_migrations` fixture
(they are mock tests but still open a real conn), so when pointing at a fresh shared DB you must
migrate it to head once up-front — CI does this explicitly. The shared WSL Docker host maps
Postgres on **port 55432, never 5432** (`:5432` is a foreign DB on the shared host — never probe it).

Runtime DB access needs `CHIPS_DB_URL`. Optional local-model env: `OLLAMA_BASE_URL`,
`OLLAMA_MODEL`, `OLLAMA_COMPRESS_MODEL`, `CHIPS_POLICY_FILE`.

## Architecture (the big picture)

Data flows **harvester → storage → compiler → MCP**, all over Postgres/pgvector:

- **`src/chips/harvester/`** — ingests git history and derives evolutionary signals. `git_ingestion`/
  `git_reader` read commits into `cortex_git_commits` (the truth table); enrichers in
  `harvester/enrichment/` (griffe API surface, lizard complexity, jscpd clones, vulture dead-code,
  bandit/semgrep security, cochange, defect, ownership, coverage, graphify, semble) produce
  signals; `signals`/`assay`/`yield_score`/`defect_corpus` compute co-change entropy, defect
  history, fragility, and yield. Derived tables are **truth-replayable from `cortex_git_commits`**.
  `daemon.py` is the periodic/hook-driven runner. **All harvester reads route through `storage.py`**
  (the storage boundary), not ad-hoc SQL.
- **`src/chips/memory/`** — finding/outcome/constraint repositories over the `cortex_*` tables.
- **`src/chips/compiler/`** — the deterministic brief builder. `builder.py` orchestrates
  `retrieve → embed → rerank → compress → rank/assemble → govern`, each an extracted phase
  (strangler-fig decomposition of `BriefBuilder.build()`). Produces a `ContextBrief` with a
  6-signal ranking, 2-stage compression, an `EvidenceBundle` (findings keyed by
  `find:<content-hash>`), constraint injection, a `governor` decision, and a `decision_log`
  record. Policy is loaded from `cortex_policy.yaml`.
- **`src/chips/mcp/`** — the MCP server. `bus.py` assembles a `FastMCP` app + `BusRegistry`;
  `modules/` are the registered modules (brief, briefs, memory, git, contracts, diffs, feedback,
  health, policy, runtime, tests_ctx, workflow, constraints, hypotheses); `tools/` are the
  callable tool implementations. Add a capability by writing a tool in `tools/`, a module in
  `modules/`, and registering it in `bus.py`.
- **`src/chips/observability/`** — OpenInference/OpenTelemetry spans + a span registry; metrics
  flow through the CHIPS-owned `repo_metrics_v` SQL view (the **metrics authority**: surfaces only
  visualize, CHIPS computes). Grafana is the standing surface. `CHIPS_REQUIRE_OTEL=1` makes span
  drift a CI failure.

Tests mirror `src/` under `tests/` (`tests/compiler`, `tests/harvester`, `tests/mcp`,
`tests/memory`, `tests/unit`, `tests/db`). Migrations are `migrations/versions/NNN_*.py`.

## Conventions and invariants

- **TDD, isolated slices, surgical commits.** Conventional-commit prefixes (`feat:`, `fix:`,
  `test:`, `docs:`, `refactor:`). Add/update tests with every behavior change; for schema work
  include a migration test or repository test that proves the path end to end.
- **Determinism is non-negotiable in the reward→decision path.** No LLM judge feeds reward; the
  reward schema forbids non-deterministic inputs in active phases. Signature/normalization
  projection must be byte-identical (cross-OS golden tests).
- **Multi-tenancy:** retrieval takes `tenant_id`; `tenant_id=None` applies no filter (known
  limitation L1). Production must set `CHIPS_REQUIRE_TENANT_ID` so `build()` rejects untenanted
  calls. Don't add a retrieval path that silently omits the tenant clause.
- **Truthful status over false-clean.** Enrichment analyzers expose an explicit `AnalyzerStatus`
  (`ok`/`not_installed`/`failed`/`timed_out`/`skipped`) surfaced through
  `EnrichmentResult.analyzer_status` — an empty result must not be read as a clean run
  ("Evidence > Guessing").
- **Respect the ledger gates.** Don't implement a `blocked` capability, don't build gate/Foundry
  code before Track 2 P0 exists, and don't rename partial/aspirational work as shipped. Keep the
  Postgres substrate swap-clean — the Oxigraph migration is trigger-gated (after the first
  end-to-end vertical), not scheduled; do not start it.
