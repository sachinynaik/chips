# CHIPS Implementation Plan

**Status:** Sequenced execution layer. Decomposes the current execution program into ordered,
TDD-buildable slices.
**Authority model:** this plan *sequences*; it does not override:

- [`docs/design_docs/18_06/chips-execution-decision-sheet.md`](./design_docs/18_06/chips-execution-decision-sheet.md) — the execution program (Track 1 / Track 2, capture-now, deferrals)
- [`docs/design_docs/18_06/chips-build-brief.md`](./design_docs/18_06/chips-build-brief.md) — the parent build brief (V1.x / P0–P2 / open decisions)
- [`docs/02_06_execution_ledger.md`](./02_06_execution_ledger.md) — capability readiness gates (the learning loop stays blocked)
- [`docs/adr/A0-architecture-reconciliation.md`](./adr/A0-architecture-reconciliation.md) — built-vs-target reading + vocabulary
- [`docs/implementation_tracking.md`](./implementation_tracking.md) — current built/partial/blocked state
- [`docs/known_limitations.md`](./known_limitations.md) — accepted debt (L1–L12)

Build discipline: **100% TDD, red-green-refactor**, isolated slices, surgical commits.

## 0. Reconciliation — what already shipped since the 18_06 docs

The build-brief frames Track 1 (V1.1–V1.4) as future work, but the repo moved.

| Build-brief item | Status now | Evidence |
|---|---|---|
| V1.1 co-change → entropy → Fragility | largely built | mig `010` cochange entropy; fragility derived from file signals + surfaced in brief findings |
| V1.2 defect labeling + history | built (raw); density TBD | mig `009` defect corpus; history surfaced; labeling rule decided (high-precision subset) |
| Capture-now (corpus + snapshots) | done | mig `009`, mig `011` signal snapshots |
| V1.3 Yield + Fragility-as-signal | partial | `yield_score.py`, `assay.py` exist; fragility wired |
| V1.4 Materials (Assay first) | substrate only | early assay; Refinery/projection/Dolt not built |
| Track 2 gate (P0/P1/P2) | untouched paper | aspirational |
| Compression contract | locked as a note | enforcement hooks unbuilt |

Frontier: **finish the Track 1 signal vertical → seed a real Assay → decide Dolt → paper-build the
gate in parallel.** Learning loop and Signoff-gate *code* stay blocked.

## 1. Workstream A — Track 1 code-intelligence vertical (active, no gate)

Internal order fixed: V1.1 → V1.2 → V1.3 → V1.4.

- **#27 — close V1.1/V1.2 remnants.** Resolve open-decision #2 (co-change support threshold +
  generated-code filter; verify vs mig `011` generated tags); finish defect density (size-normalized).
  DoD: thresholds in-code, generated code excluded from coupling, density has a test.
- **#28 — V1.3 Yield (signal-only).** Compose Yield over the fault-signature suite; confirm Fragility
  wired. Invariant: Yield is demo/external-only, never a gate input; Fragility is the gate input. Do
  not build the demo surface yet.
- **#29 — V1.4a Assay real (read-only).** Emit three independent scores — purity (determinism
  fraction + dopant), decay (intrinsic half-life × extrinsic territory signals), freshness — over
  existing signals. Never collapse; no LLM-as-judge; a gap stays a gap. Gates the Refinery.

## 2. Workstream B — Track 2, the Signoff gate (paper-first, parallel to A)

**Hard rule: no gate code before P0 exists.**

- **#31 — P0 partial-population decision table.** `{DRC input/named graph} × {fresh|stale|missing|
  failed-write} → action`, worst-state-across-the-reach wins; UNKNOWN → ESCALATE. Resolves open #6.
- **#32 — P1 ontology contract.** `g:*` predicates, named-graph partitioning, versioning; encodes the
  edge-confidence hierarchy (associative never gates a destructive fire). Needed when Oxigraph lands.
- **P2 validation slice** (build last; the Track 1 ∩ Track 2 convergence). One real fire end-to-end
  `DRC → Signoff → Manual Review → Execute → Audit`, one of each edge class + an induced stale
  subgraph + one Letta-coordinated fire ("caller, never authority").

## 3. Workstream C — Materials layer deep build (after Assay + versioned baseline)

- **#36 — Refinery + projection + fitted coefficients + ceremony.** Refinery is the only thing that
  raises purity (validate-receipt / anneal / gap-fill; every output re-Assayed, never self-certifies).
  Projection over versioned state with its own lower purity. Coefficients fitted from projection error
  with hierarchical pooling — no magic numbers. Improvement track is "a breather, not a pillar."
  Onboarding = permanent cold-start mode.

## 4. Workstream D — Dolt harvester spike (storage decision)

- **#30 — author the Dolt spike PLAN doc first** (precedes any Dolt code). Schema mapping for the 5
  harvester tables, write/query translation, dev/test workflow, rollback criteria. Split-store: Dolt
  owns harvester truth, Postgres keeps memory/briefs/constraints/decision_log/ops. GO only if all 5
  §7 criteria hold; NO-GO on any §8. Do not confuse the flaky-DB-harness motivation with the
  storage-model decision.

## 5. Workstream E — Compression contract enforcement (cross-cutting)

- **#33 — fail-closed evidence pointers.** Build the 5 hooks (pointer token shape + content-addressed
  IDs, dereference API, retention, legal brief sections, fail-closed production test). Invariant: no
  persisted decision/score/fault-signature/fragility/assay/verifier/eval result cites compressed text;
  dangling pointer = invalid, fails closed at point of use. Headroom: keep the pattern, defer the dep.

## 6. Workstream F — Tooling spikes (kill-criteria-bearing)

- **#34 — zap/RTK operator-output bake-off** (ADR-003): ~0.5 day, zero CHIPS code, anytime. Per-class
  hard gates: recoverability, exact exit-code fidelity, never hide errors near the exclusion list.
- **#35 — strict chain:** close Foundation tranche (slice 3 `repo_metrics_v` + cross-OS runner) →
  contract-lane thesis spike (fails → ADR-002/Zenith abandoned, not reworked) → Zenith spike only if
  that passes and the OTel ingestion adapter exists, judged on the locked ADR-002 rubric. Impossibility
  test before any Spike → Integrate.

## 7. Blocked / do-not-build (guardrails)

- **#38 — anti-regression loop closure (L12):** queue durable but not verifier-driven. Blocked on the
  Phase-3 verifier. Do not build composite_reward / mastery / OPE / online_bandit / rule_induction.
  Keep "no active constraint without manual `add_constraint`."
- **Oxigraph + Qdrant migration:** trigger-gated (after the first end-to-end vertical on Postgres).
  Recorded, not scheduled. Keep the Postgres boundary swap-clean.
- **Deferred-by-decision:** demo/yield surfaces; admission-time chip safety; multi-repo federation
  (single-repo until one vertical is proven).

## 8. Open decisions that gate the above (#37)

Settled: #1 defect labeling (high-precision subset), #4 SPOF ownership (lead-owned, infra-change
reviewed). Remaining: #3 yield calibration cadence/staleness · #5 demo-vs-gate boundary · #7 pgvector
scale check (could drop Qdrant) · #8 stack-role verification (Dolt/Timescale/Meilisearch/txtAI/
Redpanda) · #9 new chip-admission safety gate placement.

## 9. Recommended sequence

1. Now, parallel: **#27** ‖ #31 ‖ #34.
2. Then: **#28** → **#29** ‖ #32 ‖ #33.
3. Decision gate: **#30** (spike plan → spike → GO/NO-GO) — informs whether #36 builds on Dolt.
4. After Assay + baseline: **#36** → P2 validation slice.
5. Own track: **#35** (Foundation close → contract-lane → Zenith).
6. When the verifier exists: unblock **#38** and the L5 learning loop.

## 10. Maintenance rule

Update this plan when a slice completes, a workstream re-sequences, an open decision is settled, or a
blocked capability unlocks. Keep it a *sequence*, not a second truth doc — `implementation_tracking.md`
remains the state authority.
