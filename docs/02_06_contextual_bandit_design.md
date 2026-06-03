# Contextual Bandit Learning Loop — Design

**Status:** STAGED PROGRAM (proposal). Governed by `02_06_execution_ledger.md`. Restructured 2026-06-02 per Codex sign-off into Foundation → Activation → Optimization, with the `02_06_design_pressure_test.md` blocking fixes folded in. **Does not touch Slice A4.**
**Readiness:** Foundation = **active**; Activation = **blocked on the Phase-3 verifier**; Optimization = **blocked**. See the capability map (§3) — nothing reward-consuming is buildable yet.

---

## 1. Purpose

Give CHIPS a deterministic, offline-first learning loop that tunes *which policy it applies* (governor/reranker/budget/ranking-weights) from logged outcomes, and exposes a per-repo **mastery** signal that makes context-rot a measured quantity. CHIPS stays a deterministic compiler — the loop tunes config, never trains a model, never reasons at prompt time, never intercepts the agent.

## 2. Scope (phase-local)

**In scope (this program):** the decision/reward log; deterministic span/event emission; a composite reward (once a reward source exists); offline policy evaluation; a per-repo mastery metric; later, gated online tuning and outcome→constraint rule induction.

**Out of scope for the current (Foundation) phase:** any reward-consuming computation (composite reward, mastery math, OPE, online exploration, rule induction). These are preserved in §6 but **blocked** (§3) until the verifier exists. Not global-forever out of scope — phase-local.

## 3. Capability map

| Capability | Layer | Status | Prerequisite | Unlock evidence | Test gate |
|---|---|---|---|---|---|
| `decision_log` | Foundation | **active** | migration 008 + versioned feature schema | — | round-trip + schema-version test |
| `span_emission` | Foundation | **active** | `chips.*` attr registry snapshot | — | span contract test |
| `policy_version` hashes | Foundation | **active** | — | — | content-hash stability test |
| `composite_reward` | Activation | **blocked** | Phase-3 verifier labels | reward shape + ≥ N_min labels | reward-schema test (forbids non-deterministic inputs) |
| `mastery_math` | Optimization | **blocked** | composite_reward + data sufficiency | ≥ N_min labelled briefs/repo | monotonic + no-double-decay + replay-reproducible |
| `OPE` | Optimization | **blocked** | reward **and** action variation | action-overlap diagnostic ≥ threshold | estimator unit + CI bound |
| `online_bandit` | Optimization | **blocked** | OPE offline confidence + verifier | ledger §7 checklist complete | shadow-run + kill-switch drill |
| `rule_induction` | Optimization (own doc) | **blocked** | validated bad-outcome corpus | corpus ≥ N_min, confidence-gated | induced-rule = human-confirm gate |

## 4. Foundations (buildable now)

These need no verifier and no accumulated data; they are the "impossible to reconstruct later" pieces.

- **`cortex_decision_log`** (migration 008), tenant-scoped — one row per brief decision. Schema + versioning in §9.
- **Span/event emission** — emit the decision + (later) reward as OpenInference-conventioned OTel spans (`chips.policy.*`, `chips.action.*`, `chips.propensity`) per `openinference-assessment.md`. Guarded by a **span contract test**.
- **`policy_version` as a content hash** of the active weight-set (not free text) — so replay grouping is reproducible.
- **Raw reward *components*** are *stored* as nullable fields now (verifier_outcome, regression, review, feedback, latency) but **not combined** until Activation.

## 5. Activation path (what turns it on)

The single prerequisite is the **Phase-3 verifier emitting validated reward labels** (roadmap §3.4: no verifier → no useful reward). On that:

- **`composite_reward`** becomes computable. It is **verifier-dominant** and **schema-constrained**: only deterministic terms admitted in active phases. Per the invariant (§8), `w_review` and `w_latency` are **0 until the verifier term dominates** — this kills both pre-verifier reward-hacking (starve-the-brief) and the LLM-judge-in-reward path. Each term is **normalized** before weighting (binary vs ms vs thumbs live on different scales).
- Mastery and OPE remain **blocked** until data sufficiency (§9, ledger §6) and action-variation (§7) preconditions are measured.

## 6. Optimization path (later, each gated)

Preserved in full; each blocked per §3.

- **`mastery_math`** — per-repo component model → derived metrics (§9.3). Computed **in CHIPS** (invariant), surfaced via Grafana/Superset.
- **`OPE`** — owned NumPy estimators (IPS/SNIPS/DR/SWITCH; reimplement obp's math, do not depend on the stale package). **Identifiable only across `policy_version` variation** — see the action-overlap precondition (§7, §10). Direct-Method first (on deterministic logs), with a **calibrated uncertainty bound**; DM headroom counts only if it exceeds r̂'s validated error.
- **`online_bandit`** — bounded ε on one discrete knob, under the ledger §7 unlock checklist (offline-first, gate-online). The online safety monitor is a **realized-reward-drop / SPRT drift monitor with a numeric kill-switch threshold** — NOT "regret" (regret is not live-computable; §9.3).
- **`rule_induction`** — deterministic greedy inducer (imodels `GreedyRuleList`/`OneR`, seeded) over **verifier-confident** bad-outcome rows → reviewable constraint candidates (human-confirmed). **Moves to its own design doc** (it is a second safety surface).

## 7. Dependency graph

| Dependency | Required by | Blocking condition if absent |
|---|---|---|
| `decision_log` + versioned schema | composite_reward → mastery / OPE / rule_induction | nothing computable or replayable |
| Phase-3 verifier labels | composite_reward (→ all optimization) | reward dominated by null term → metrics are theater |
| **action variation** across `policy_version` | OPE | counterfactual unidentifiable on deterministic log |
| calibrated uncertainty bound on r̂ | online_bandit unlock | DM headroom unfalsifiable; circular gate |
| sigmap hash-staleness (`staleness_feeds`) | mastery freshness component | freshness sub-metric unavailable |

## 8. Invariant table

| Invariant | Why | Mechanism | Proof |
|---|---|---|---|
| No LLM judge / non-deterministic input in reward (active phases) | determinism; non-negotiable | reward schema admits only deterministic source fields; `w_review`=`w_latency`=0 pre-verifier | reward-schema validation test rejects non-deterministic fields |
| Mastery is reproducible | product metric can't be path-dependent on label latency | pure function of the ordered, fully-labelled log; backfill ⇒ recompute-in-order | replay-twice equality test |
| OPE only across action variation | counterfactual validity | action-overlap diagnostic precondition gates Phase B | diagnostic ≥ threshold recorded in ledger |
| Online only after offline proof | don't degrade real briefs | ledger §7 unlock checklist | checklist complete + recorded before activation |
| Metrics computed in CHIPS | single definition, no fork | mastery in CHIPS; `repo_metrics_v` is the only surface source | CI check (observability doc) |

## 9. Data contract

### 9.1 `cortex_decision_log` (migration 008)
Keys: `id`, `brief_id` (FK), `tenant_id`, `scope/repo_id`, `created_at`. Payload: `context_features` JSONB, `action` JSONB, `propensity` float NULL (1.0 deterministic), `policy_version` **content-hash text**, `evidence_used` JSONB, `latency_ms` int, `feedback` JSONB NULL, `verifier_outcome` JSONB NULL, `downstream_success` JSONB NULL, `composite_reward` float NULL.

### 9.2 Versioning & integrity
- `context_features`/`action` carry a **`feature_schema_version`**; OPE/DM must filter to a single schema version (no ragged matrices).
- **Write path:** synchronous (or explicitly accept + document survivorship bias if async). Lossy logging biases OPE toward low-load briefs.

### 9.3 Metrics — definitions (computed in CHIPS)
- **Components** (raw, stored): retrieval-quality, task-outcome, adaptation, operational.
- **mastery(repo)** — smoothed realized performance. Churn modulates **confidence/half-life**, it does **not** multiply an already-decayed term (the double-decay bug is removed): a sustained-good repo under churn must *not* trend to zero; recovery comes from good rewards.
- **drift / freshness / risk** — derived (freshness consumes sigmap hash-staleness).
- **regret** — internal, OPE-only (hindsight baseline); **never surfaced, never "monitored live."** The online monitor is reward-drop/SPRT (§6).

### 9.4 Data sufficiency (per ledger §6)
- `N_min` per metric before it leaves the **insufficient-evidence** state (an explicit surfaced value, not 0/null).
- Backfill ⇒ recompute-in-order.
- Aggregation level: **repo-level** primary (RLS-safe once gap-#6 lands); scope/tenant rollups secondary.

## 10. Failure modes

| Failure | How it happens | Detection | Fallback |
|---|---|---|---|
| OPE unidentifiable | deterministic log, action⟂context | action-overlap diagnostic < threshold | stay in DM; do not unlock online |
| Circular online gate | trusting biased DM to justify going online | uncertainty bound check | block online until bound calibrated |
| Reward hacking | nonzero `w_latency`/`w_review` pre-verifier | reward-schema test | weights forced 0 until verifier dominates |
| Mastery false-rot | double-decay | property test on recurrence | corrected recurrence (§9.3) |
| Non-reproducible mastery | out-of-order backfill | replay-twice test | recompute-in-order |
| Learning wrong constraints | rule induction over noisy verifier | confidence gate + human review | confidence threshold; human-confirm |
| Survivorship bias | async-write loss | log-count vs brief-count audit | synchronous write |

## 11. Decision log

- **Accepted:** Foundation now (log + spans + policy hash); reward verifier-gated; mastery component model in CHIPS; regret internal-only; online gated by checklist; obp-math borrowed not depended.
- **Deferred:** composite_reward, mastery_math, OPE, online_bandit, rule_induction.
- **Rejected:** computing mastery in BI (violates metrics-in-CHIPS); building reward-consumers pre-verifier; `w_review`/`w_latency` ≠ 0 pre-verifier; continuous-action IPS without a density estimator (v1 online = one discrete knob); `policy_version` as free text.

## 12. Implementation sequence (each step ends with an artifact + test gate)

1. **Migration 008 + `decision_log` model** (versioned feature schema, `policy_version` content hash) → *artifact:* table + model; *gate:* round-trip + schema-version test.
2. **Deterministic decision-span emission** (`chips.policy/action/propensity`) → *artifact:* emission helper; *gate:* span contract test.
3. **Populate the log** with deterministic actions (propensity=1), raw components nullable → *artifact:* live logging; *gate:* log-count = brief-count audit.
4. *(Activation — blocked on verifier)* composite_reward + reward schema → *gate:* schema test rejects non-deterministic fields.
5. *(Optimization — blocked)* mastery_math; OPE (with action-overlap precondition); online_bandit (ledger §7); rule_induction (own doc).

## 13. Readiness exit criteria

- **Foundation → Activation:** steps 1–3 green; decision_log populated; span contract test passing; **Phase-3 verifier emits validated reward labels for ≥ N_min repos.**
- **Activation → Optimization:** composite_reward active + schema-enforced deterministic; **measured action variation** sufficient for offline OPE; data-sufficiency fields (§9.4) filled.
- **Optimization → online:** ledger §7 checklist fully checked and recorded.

### Cross-references
`02_06_execution_ledger.md` (authority), `02_06_design_pressure_test.md` §2 (findings folded in here), `02_06_observability_analysis_architecture.md` (surfaces mastery), `02_06_signature_map_design.md` (freshness input), roadmap §3.4/§3.5/§3.6.
