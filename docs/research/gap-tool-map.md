# CHIPS Gap → Tool Map — What to Borrow to Close the Biggest Gaps

**Author:** Research engineering pass (Claude), synthesizing 4 web-research sweeps + Codex's gap analysis (2026-06-02)
**Scope:** Maps Codex's 8 stated gaps (top 3 existential) to concrete, **verified** external tools/patterns, each judged against CHIPS's hard criteria — **(1) determinism, (2) local-first, (3) simplicity, (4) sidecar-not-inline, (5) Python 3.13** — with the standing posture **BORROW THE PATTERN, REFUSE THE DEPENDENCY** unless a dep is small, deterministic, local, and net-positive.

Companion notes: `open-bias-assessment.md`, `re-gent-assessment.md`, `openkb-forge-assessment.md`. All tool facts below were verified against upstream repos/docs; skeptical flags are inline.

> **Sequencing guard:** Nothing here reorders the locked slice plan. **A4 (flag governor/reranker/structural OFF by default) remains the next product-code slice.** These borrows attach to A3, A5a, A6, Phase 4, and a few additive tracks — scheduled *after* A4, or in parallel as "legit additions" (the way obs-metrics/analytics/property-tests were).

---

## 0. The shortlist (what actually earns adoption/borrow)

| Borrow / Adopt | Type | Closes gap | Maps to | Determinism | Local-first |
|---|---|---|---|---|---|
| **obp OPE estimators (IPS/SNIPS/DR/SWITCH) — reimplement as ~100 LOC owned NumPy** | Borrow (don't depend; obp stale Jun-2022) | #1 closed-loop learning | Phase 4 (OPE→bandit over `weights_used`/`verification_reward`) | PASS (closed-form replay) | PASS |
| **Greedy rule induction (imodels `GreedyRuleList`/`OneR`, fixed seed) — pattern or small MIT dep** | Borrow | #1 outcome→constraint promotion | write-back review queue + locked rule-induction backlog | PASS (greedy/seeded only) | PASS |
| **Plain-Python `Protocol` stages (NOT a framework)** | Adopt (baseline) | #2 over-centralized builder.py | Slice A3 strangler-fig | PASS | PASS |
| **Prometheus + Grafana (+ optional Tempo) over EXISTING signals** | Adopt | #4 operator surface | new observability slice | PASS | PASS (self-host) |
| **Inspect (UK AISI, MIT) or promptfoo (MIT) sourcing the DuckDB export** | Adopt (one of) | #4 "did this brief help?" | eval track | PASS (deterministic scorers; LLM-judge optional) | PASS (Ollama) |
| **ranx (MIT) offline eval/fusion-selection + inline dependency-free RRF in the hot path** | Borrow + scoped-adopt | #5 retrieval quality | A4/A6 (measure before re-enabling) | PASS (inline RRF); ranx Numba flagged | PASS |
| **Postgres RLS + `SET LOCAL` + `FORCE ROW LEVEL SECURITY` + non-owner role (via Alembic)** | Adopt | #6 tenant construction-safety | new tenant-hardening slice | PASS | PASS (native PG) |
| **Hypothesis stateful testing (already in-stack)** | Adopt | #7 verification story | testing track | PASS (seeded) | PASS |
| **testcontainers-python (pin image by digest)** | Adopt | #7 DB harness reliability | testing track | PASS (pinned) | PASS (needs Docker) |
| **open-bias verdict-trace + approval-flow pattern** | Borrow | #3/#4 audit + review queue | A5a + write-back gate | PASS | PASS |
| **re_gent content-addressed step-DAG + blame pattern; ingest `rgt log --json` at Phase 4** | Borrow + companion-ingest | #1/#3 audit + reward substrate | A5a (pattern) + Phase 4 (ingest) | PASS | PASS |
| **Forge `rescue_tool_call` + validator (deterministic parsing)** | Borrow (Phase 4) | #3 hypothesis submission robustness | Phase 4 `cortex_submit_hypotheses` | PASS | PASS |

**Explicit SKIPs:** Vowpal Wabbit / River (online learning — violates offline-only), DSPy (LLM prompt-time — violates determinism + sidecar), Dagster / Prefect (require a service — violate local-first/simplicity), pipefunc (NetworkX/NumPy weight; Hamilton does it better), Langfuse (multi-service heavy), OpenLLMetry (re-instrumentation — CHIPS already emits OTel), ragas/DeepEval/TruLens (LLM-judge-first — non-deterministic), pytrec_eval (C build risk on Win/3.13), BEIR (public-benchmark, not your corpus), MultiAlchemy / sqlalchemy-tenants-as-dep (app-layer or immature security control), cosmic-ray (heavier than mutmut), Hamilton-as-dep-now (framework tax on a 4-stage chain — revisit only if it becomes a branching DAG).

---

## 1. Gap #1 — Weak closed-loop learning from verified outcomes *(top existential)*

**CHIPS need:** automatic/reviewable promotion bad-outcome → durable constraint; stronger use of verifier/reward signals; closed-loop hypothesis ranking + write-back. CHIPS already has the feedback-weighted memory adjustment and the `weights_used`/`verification_reward` columns; the roadmap commits to **offline OPE → contextual bandit, never online, never model-training**.

**Recommendation:**
- **OPE/bandit loop:** *Borrow obp's estimator math, don't depend on obp.* `Open Bandit Pipeline` (Apache-2.0, ~710★) is the canonical reference but its **last release was Jun 2022 (effectively unmaintained, pins Py 3.7)** — adopting it live fails simplicity/longevity. Its value (IPS / SNIPS / DR / SWITCH) is **closed-form NumPy (~100 LOC)**; reimplement as an owned module that replays the existing reward log to estimate outcomes under candidate weights W′. Fully deterministic, zero new service. → **Phase 4** (the roadmap's §3.5 "prove the gap with OPE before paying for RL").
- **Outcome→constraint promotion:** use a **deterministic greedy rule inducer** — `imodels` (MIT, sklearn API) `GreedyRuleListClassifier` / `OneRClassifier` (fixed seed) over a labeled table of (features → verified-bad-outcome) emits a short, human-readable decision list = **reviewable constraint candidates by construction**. Human approves before it becomes durable (`cortex_add_constraint`). **Avoid Skope-rules / Bayesian / tree-ensemble variants (RNG → non-reproducible).** Borrow the pattern or take the small MIT dep. → **write-back review queue + the locked "deterministic contradiction/rule" backlog**.
- **SKIP:** VW, River (online — explicitly deferred), DSPy (LLM-in-loop — violates determinism + sidecar).
- **Also feeds this gap:** re_gent ingestion (Phase 4 reward substrate, see re-gent note) and open-bias SHADOW (observe-without-acting outcome capture).

**Determinism:** PASS (closed-form OPE replay; greedy/seeded rule induction). **Local-first:** PASS.

---

## 2. Gap #2 — Over-centralized builder.py *(top existential; biggest maintainability risk)*

**CHIPS need:** decompose the god-object into `SourceCollector / PolicyAssembler / ContextAssembler / BriefPersister` (strangler-fig, Slice A3).

**Recommendation: plain Python composition is the right call — adopt no framework.** The four stages form an almost-linear chain (collect → assemble policy → assemble context → persist); a DAG engine's value (auto-resolving wide dependency graphs) is wasted on a 4-node chain. Define each stage behind a `typing.Protocol`, wire them in one explicit orchestrator. The testability win comes from the **decomposition itself** (Protocol-typed fakes per stage), not from any framework — a framework cannot make a 4-stage chain more testable than four Protocol objects.
- **Borrow two ideas, not deps:** sklearn's *"named, uniform-interface steps"* and Hamilton's *"function/stage = node with explicit typed inputs"* (for clean lineage).
- **Hamilton (Apache-2.0, in-process, deterministic):** genuinely fits the function-as-node model and is the *only* framework worth a second look — but it inverts control to a Driver, names nodes by function name, and pulls pandas/numpy into a project whose simplicity rule says "plain Python is the baseline to beat." **BORROW-PATTERN now; reconsider ADOPT only if the pipeline later grows into a genuinely branching DAG.**
- **SKIP:** Dagster, Prefect (require a daemon/server/worker — violate sidecar/local-first/simplicity), pipefunc (NetworkX+NumPy weight, smaller support — Hamilton does the same idea better). `graphlib.TopologicalSorter` (stdlib) is the back-pocket option only if stage ordering ever becomes data-dependent.

**Determinism:** PASS. **Local-first:** PASS. **Simplicity:** maximally honored by refusing a framework.

---

## 3. Gap #3 — Evidence/hypothesis architecture only half-productized *(top existential)*

**CHIPS need:** hypothesis submission/adjudication loop, durable candidate review queue, verifier-driven reward pipeline, complete constraint-management surface. (Much of this is CHIPS's own Phase-1 wiring; tools supply the *robustness + review* shapes.)

**Recommendation:**
- **Candidate review queue + adjudication:** *borrow open-bias's* capture → review → **approval flow** (note `open-bias-assessment.md`) for the write-back queue. Matches the locked invariant "no constraint activated without human confirm."
- **Hypothesis-submission robustness (Phase 4 `cortex_submit_hypotheses`):** *borrow Forge's* deterministic `rescue_tool_call` (regex/JSON repair, no LLM) + **ResponseValidator** schema-check+nudge (note `openkb-forge-assessment.md`) so a local small model's structured output is canonicalized/validated deterministically. Check Ollama grammar-constrained decoding first (may make rescue unnecessary).
- **Constraint-management surface:** this is the still-missing **MCP add/retire path** (D4 / L9 — constraints currently enter only via SQL/migration). Build `cortex_add_constraint` / `cortex_get_constraints` (CHIPS-native; no external tool). The truthful `retire()` (Slice A2b, done) is the substrate.
- **Audit half:** borrow re_gent's content-addressed step-DAG + blame shape for the provenance record (note `re-gent-assessment.md`).

**Determinism:** PASS (parsing/validation/approval are deterministic). **Local-first:** PASS.

---

## 4. Gap #4 — Observability is instrumentation, not an operator surface

**CHIPS need:** exposed metrics surface, dashboards, "did this brief help?" reporting. CHIPS **already emits OTel traces + Prometheus metrics + a DuckDB brief-history export** — so the win is in *consumers*, not new instrumentation.

**Recommendation:**
- **Operator surface:** **adopt Prometheus + Grafana** (optionally + **Tempo** to view existing OTel traces in the same pane). Prometheus scrapes CHIPS's existing `/metrics`; zero re-instrumentation; fully self-hostable/air-gap-friendly. Lowest-friction diagnosis of "wrong/slow/degraded."
- **"Did this brief help?" report:** this is an **offline eval** problem, not tracing. **Adopt Inspect (UK AISI, MIT, Py 3.10+, deterministic scorers, runs on local Ollama)** *or* **promptfoo (MIT, first-class deterministic YAML assertions)** — source cases from the **existing DuckDB export** (briefs + downstream outcome labels). Keep any LLM-judge scoring strictly optional.
- **If an LLM-aware trace+eval UI is later wanted:** **Arize Phoenix** as a *single* self-hosted OTLP backend (air-gap flag on; **ELv2 — source-available, not OSI-open**, acceptable for internal self-host).
- **SKIP:** Langfuse (multi-service: Clickhouse+Redis+blob — violates simplicity; EE telemetry non-disableable), OpenLLMetry (it *produces* OTel — redundant; CHIPS already instrumented), ragas/DeepEval/TruLens (LLM-judge-first — fail the determinism gate).

**Determinism:** PASS (dashboards/deterministic scorers). **Local-first:** PASS (all self-hosted/offline). → **additive observability slice** (like the prior obs-metrics-tracing addition), tied to A5a.

---

## 5. Gap #5 — Retrieval quality uneven

**CHIPS need:** measure whether each signal actually improves ranking; combine signals via a principled method instead of ad-hoc weights; decide what's worth keeping (directly informs **A4** flag-off and **A6** fix-before-re-enable).

**Recommendation:**
- **Offline eval + fusion selection:** **adopt ranx (MIT, Py ≥3.8)** as a *dev/eval-time* harness — it gives 12 IR metrics (NDCG@k, MAP, MRR, Recall…) **and** 25+ fusion algos incl. **RRF**, plus weight optimization, in one lib. Use it to quantify per-signal NDCG/MRR lift (→ *evidence* for which experimental layers to re-enable in A6) and to choose a fusion method. **Flag:** ranx depends on **Numba** (LLVM JIT) — keep it eval-time, not in the runtime hot path.
- **Runtime combination:** **inline a dependency-free Reciprocal Rank Fusion** (`score = Σ 1/(k+rank_i)`, ~10 lines, fully deterministic, no Numba). RRF is rank-based, so it sidesteps the signal score-scale mismatch that ad-hoc weights cause — directly the "more sources than confidence in how to combine" problem.
- **SKIP:** pytrec_eval (C-extension build risk on Windows + Py 3.13 wheels; ranx covers the metrics in pure Python), BEIR (public-benchmark for comparing *models*, not your signals on your corpus — borrow only its qrels/corpus/queries file format for golden judgments).

**Determinism:** PASS (inline RRF deterministic; ranx Numba flagged to eval-time). **Local-first:** PASS. → **A4 / A6** (measure → decide → re-enable with evidence).

---

## 6. Gap #6 — Tenant safety is policy-enforced, not construction-enforced

**CHIPS need:** isolation that is impossible-to-misuse, not dependent on conventions/runtime gates (`build_tenant_scope`).

**Recommendation: adopt native Postgres Row-Level Security.** `CREATE POLICY` keyed on a per-transaction session variable (`current_setting('app.tenant')`), policies shipped via Alembic migrations (`op.execute`). Keep `build_tenant_scope` as **defense-in-depth**, but RLS becomes the enforced floor — the construction boundary you want, evaluated in the engine itself. **Three must-dos (the silent holes):**
1. `ALTER TABLE … FORCE ROW LEVEL SECURITY` **and run the app as a non-owner, non-superuser role** — owners/superusers **bypass RLS by default** (the #1 hole).
2. Set the tenant via **`SET LOCAL app.tenant = …` inside a transaction** (auto-resets at COMMIT/ROLLBACK) — **not** plain `SET`, which leaks the tenant onto a pooled connection for the next checkout. (Or reset via a pool `checkin` event.)
3. Every tenant table needs the column **and** a policy — a missing policy = wide-open table.
- **Borrow, don't depend:** read `sqlalchemy-tenants`' `@with_rls` / session-manager *design*, then write the ~50 lines of glue yourself (it's ~4★, one-author — refuse-the-dependency applies hardest to a security control). **SKIP** MultiAlchemy (app-layer query rewrite = same convention-class you're escaping) and per-tenant Postgres roles (breaks pooling; role explosion).

**Determinism:** PASS. **Local-first:** PASS (native PG). → **new tenant-hardening slice** (high-leverage; pair with §7 verification).

---

## 7. Gap #7 — Test/verification weaker than design ambition

**CHIPS need:** reliable DB-backed harness; verifiable integration/MCP paths; confidence that tests actually catch regressions.

**Recommendation:**
- **Best single buy: Hypothesis stateful testing** (`RuleBasedStateMachine`) — **already in-stack** (property tests landed in `cbb1b39`), zero new dep, deterministic via seed/`derandomize`. Model-based tests of operation *sequences*: constraint retire/restore, tenant-scoping invariants, brief-history write-back.
- **Make the DB harness real: testcontainers-python (Apache-2.0)** — ephemeral real Postgres per session, **pinned by image digest** for determinism (requires a Docker daemon in CI). Kills the selective-slice/DB-reliability problem and lets you test RLS (§6) against a real engine.
- **MCP contract testing: schemathesis (MIT, Py ≥3.10)** — property/contract tests over the MCP tool JSON schemas to catch schema/handler drift (scoped to whatever is JSON-Schema-describable).
- **Hang protection: pytest-timeout (MIT, Py 3.7–3.13, v2.4.0)** — aborts hung tests; protects the DB/integration/MCP suites from wedging CI (the hang failure mode already hit this session). **Windows caveat:** the thread method (default on Windows) aborts the whole process via `os._exit()` — no teardown/XML. **ADOPT scoped:** per-test `@pytest.mark.timeout` markers on hang-prone DB/integration tests, *not* a blanket global. (added 2026-06-02)
- **Test-strength gauge: mutmut** — CI-only, **Linux-only (needs `fork()`; not native Windows — run in Linux CI, not the Windows dev box)**, periodic not per-commit. **SKIP** cosmic-ray (heavier fallback).
- **Cross-gap synergy (do this):** a single Hypothesis stateful machine asserting *"no tenant ever reads another tenant's rows"* against a **testcontainers** RLS-enabled Postgres is the strongest possible construction-vs-policy proof for §6.

**Determinism:** PASS (seeded/pinned). **Local-first:** PASS (Docker for testcontainers). → **testing track**, paired with §6. Highest-value buys: Hypothesis stateful + testcontainers; add **pytest-timeout** (scoped markers) as cheap hang-protection.

---

## 8. Gap #8 — Docs/implementation drift *(governance debt, not a tool gap)*

**CHIPS need:** stop locked plans / milestone docs / branch state diverging (a recurring pattern — see the D-series reconciliation commits and known_limitations L7–L10).

**Recommendation (process + light tooling, no product dep):**
- **The roadmap already is an ADR/decision ledger** (`27_05_reasoning_runtime_roadmap.md` §5 Rejected-Ideas) — keep using it as the single source of truth; require every locked decision to land there.
- **Make the Track-B multireview harness the merge gate** (already planned for A3) — a review step that explicitly checks "do the docs match the branch state?" before merge.
- **Light drift check:** a CI lint that fails if milestone docs reference commits/branches that don't exist; and use **`griffe`** (already a dev dep per L10) for API-drift detection between documented and actual symbols. Low-tech, deterministic.
- **No tool adoption here** — the fix is discipline: reconcile-before-merge, one source of truth, and a gate that enforces it. The research tooling above (and these notes) should be linked from the roadmap so they don't re-drift.

---

## 9. Suggested scheduling (does NOT change A4-first)

1. **A4** — flag governor/reranker/structural OFF by default *(unchanged, next)*. **§5's ranx** can be stood up in parallel as an eval harness to *generate the evidence* for what A6 should re-enable.
2. **A3** — decompose builder.py via **plain `Protocol` stages** (§2). Make the **multireview gate** (§8) the review step.
3. **A5a** — auditability, folding **open-bias verdict-trace + approval** and **re_gent's content-addressed+blame** patterns (§3/§4).
4. **Additive tracks (schedule like the prior obs/analytics additions):** **Prometheus+Grafana operator surface** (§4), **RLS tenant-hardening + the testcontainers/Hypothesis-stateful RLS proof** (§6/§7).
5. **A6** — fix structural/reranker (#5/#6) using ranx evidence before re-enabling (§5).
6. **Phase 4** — **owned OPE estimators** + **greedy rule induction** + **re_gent ingest** + **Forge rescue/validator** (§1/§3), all gated on the verifier reward log existing.

---

### Source references
- **Gap 1:** [zr-obp](https://github.com/st-tech/zr-obp) (Apache-2.0, v0.5.5 Jun-2022), [imodels](https://github.com/csinva/imodels) (MIT), [VW](https://github.com/VowpalWabbit/vowpal_wabbit), [River](https://github.com/online-ml/river), [DSPy](https://github.com/stanfordnlp/dspy), DRos estimator (arXiv 1907.09623).
- **Gap 2:** [Hamilton](https://github.com/apache/hamilton) (Apache-2.0, Py 3.10+), Dagster/Prefect (service-oriented), [pipefunc](https://github.com/pipefunc/pipefunc), [graphlib](https://docs.python.org/3/library/graphlib.html), [sklearn Pipeline](https://scikit-learn.org/stable/modules/compose.html).
- **Gap 4:** [Arize Phoenix](https://github.com/Arize-ai/phoenix) (ELv2), [Langfuse](https://github.com/langfuse/langfuse) (MIT core), [OpenLLMetry](https://github.com/traceloop/openllmetry), Grafana/Prometheus/Tempo, [Inspect](https://github.com/UKGovernmentBEIS/inspect_ai) (MIT), [promptfoo](https://github.com/promptfoo/promptfoo) (MIT).
- **Gap 5:** [ranx](https://github.com/AmenRa/ranx) (MIT), [pytrec_eval](https://github.com/cvangysel/pytrec_eval), [BEIR](https://github.com/beir-cellar/beir).
- **Gap 6:** Postgres RLS ([Crunchy Data](https://www.crunchydata.com/blog/row-level-security-for-tenants-in-postgres), [AWS](https://aws.amazon.com/blogs/database/multi-tenant-data-isolation-with-postgresql-row-level-security/)), [sqlalchemy-tenants](https://github.com/Telemaco019/sqlalchemy-tenants), [MultiAlchemy](https://github.com/mwhite/MultiAlchemy).
- **Gap 7:** [testcontainers-python](https://github.com/testcontainers/testcontainers-python) (Apache-2.0), [Hypothesis stateful](https://hypothesis.readthedocs.io/en/latest/stateful.html), [schemathesis](https://github.com/schemathesis/schemathesis) (MIT), [mutmut](https://github.com/boxed/mutmut), [cosmic-ray](https://cosmic-ray.readthedocs.io/).
- **CHIPS internal:** `open-bias-assessment.md`, `re-gent-assessment.md`, `openkb-forge-assessment.md`, `27_05_reasoning_runtime_roadmap.md`, `31_05_codex_remediation_plan.md`.
