# Reasoning-Runtime Execution Ledger

**Status:** GOVERNING DOCUMENT. This ledger is the single authority for the **status, prerequisites, and unlock gates** of the capabilities described in the three design docs. It **governs, it does not replace** them — each design doc remains the detailed spec; this ledger says *whether each capability may be built yet*. Created in response to Codex's 2026-06-02 sign-off correction: keep the full vision, but stop treating all parts as equally ready.

**Date:** 2026-06-02 · **Branch:** `docs/tooling-research` · **Does not reorder A4** (the next product-code slice).

**Governed docs:** `02_06_contextual_bandit_design.md`, `02_06_signature_map_design.md`, `02_06_observability_analysis_architecture.md`. Review basis: `02_06_design_pressure_test.md`. Entry point: `02_06_codex_review_packet.md`.

---

## 1. Legend

**Status:**
- **active** — prerequisites met; buildable now (strict TDD).
- **spike** — time-boxed investigation to produce evidence; not production code.
- **blocked** — prerequisite state / unlock evidence does not yet exist; **do not build**.
- **dormant** — preserved vision, intentionally not scheduled; revisit on demand.

**Layer** (every capability belongs to exactly one):
- **Foundation** — logging, schemas, spans, stable IDs, raw components, deterministic rendering. Buildable without the verifier or accumulated data.
- **Activation** — first live use of a capability once its prerequisite (usually the Phase-3 verifier or a proven spike) exists.
- **Optimization** — smarter policies, richer metrics, larger surfaces, automation. Last.

**The hard rule:** a capability may not be implemented until its row is `active`. Promotion `blocked → active` requires the **Unlock evidence** to exist and be recorded here (with a date + pointer).

---

## 2. Capability registry

| Capability | Doc | Layer | Status | Prerequisite state | Unlock evidence/artifact | Test gate |
|---|---|---|---|---|---|---|
| `decision_log` | CB | Foundation | **active** | migration 008; versioned feature schema | schema review | round-trip + schema-version test |
| `span_emission` | Obs/CB | Foundation | **active** | OpenInference attr registry (`chips.*`) snapshot | attr registry doc | end-to-end **span contract test** (asserts expected span tree per brief) |
| `metrics_authority` | Obs | Foundation | **active** | `repo_metrics_v` SQL view owned by CHIPS | view defined | CI check: no dashboard aggregates raw tables |
| `metrics_surface_grafana` | Obs | Foundation→Activation | **active (over existing signals)** | Prometheus `/metrics` + `repo_metrics_v` | Grafana provisioned | dashboards reference only `repo_metrics_v` / Prometheus |
| `normalization_contract` | Sigmap | Foundation | **active** | — | conformance matrix (one construct → one canonical output) | cross-OS **env-pinned golden tests** |
| `bodyless_renderer_spike` | Sigmap | Foundation (spike) | **spike (active)** | normalization_contract | spike report: token win vs latency cost | byte-identical golden across 2 runs |
| `composite_reward` | CB | Activation | **blocked** | Phase-3 verifier emits validated labels | verifier reward shape known + N labels | reward schema test (forbids non-deterministic inputs) |
| `mastery_math` | CB | Optimization | **blocked** | `composite_reward` + data sufficiency (§6) | ≥ min-sample labelled briefs/repo | property test: monotonic, no double-decay, reproducible-on-backfill |
| `OPE` | CB | Optimization | **blocked** | reward **and** action variation (across `policy_version`) | measured action-overlap diagnostic ≥ threshold | estimator unit tests + CI bound |
| `online_bandit` | CB | Optimization | **blocked** | OPE offline confidence + verifier | §7 unlock checklist (this doc §7) fully checked | shadow-run + kill-switch drill |
| `rule_induction` | CB (own doc later) | Optimization | **blocked** | validated bad-outcome corpus (verifier-confident) | corpus ≥ min-sample, confidence-gated | induced-rule review = human-confirm gate |
| `sig_public_anchor` | Sigmap | Optimization | **blocked** | a real consumer + `normalization_contract` frozen | consumer exists (e.g. mastery churn feed) | anchor stability test across cosmetic edits |
| `staleness_feeds` | Sigmap | Optimization | **blocked** | `sig_public_anchor` + cache/trigger policy | staleness policy + latency budget | staleness-detection cost test |
| `superset` | Obs | Optimization | **blocked (dormant-ish)** | demonstrated analysis demand (multi-analyst) | stated need; Grafana insufficient | n/a until unlocked |
| `custom_chips_ui` | Obs | Optimization | **blocked** | stable review/control workflows; MCP/CLI proven insufficient | workflow evidence | n/a until unlocked |
| `tempo_trace_ui` | Obs | Activation (optional) | **dormant** | live trace-debugging need | stated need | n/a (Grafana datasource, not a surface) |

---

## 3. The three-layer split per design (at a glance)

| Design | Foundation (now) | Activation (on prerequisite) | Optimization (last) |
|---|---|---|---|
| **CB** | decision_log, raw reward components, `policy_version` hashes, span events | composite_reward (verifier exists) | mastery_math, OPE, online_bandit, rule_induction |
| **Sigmap** | normalization_contract, extractor decision, bodyless_renderer_spike | compact-context tier (spike proves value) | public anchors, staleness_feeds, mastery integration |
| **Observability** | OTel/OpenInference schema, metrics_authority (`repo_metrics_v`), one exposed surface | Grafana dashboards over real signals | Superset, custom_chips_ui |

---

## 4. Cross-design dependency graph

| Dependency | Required by | Blocking condition if absent |
|---|---|---|
| `decision_log` (+ versioned schema) | composite_reward → mastery_math / OPE / rule_induction | no learning signal can be computed or replayed |
| Phase-3 **verifier labels** | composite_reward (→ everything reward-consuming) | reward dominated by null term → metrics/OPE are theater |
| **action variation** across `policy_version` | OPE | counterfactual unidentifiable on a deterministic log |
| `normalization_contract` | bodyless_renderer → sig_public_anchor → staleness_feeds | non-deterministic projection; anchors churn on cosmetic edits |
| `metrics_authority` (`repo_metrics_v`) | Grafana / Superset / custom_ui | metric definitions fork across surfaces (gap #8) |
| `span_emission` (contract test) | tempo_trace_ui, debugging, CB decision spans | silent span gaps exactly where incidents happen |
| OpenInference `chips.*` registry | span_emission, metrics_surface | ad-hoc attribute drift |

---

## 5. Master invariant → mechanism table

Every load-bearing rule has an **executable** enforcement (Codex point 4 / pressure-test theme 2).

| Invariant | Why it matters | Enforcement mechanism | Proof |
|---|---|---|---|
| Metrics computed in CHIPS; surfaces only visualize | no UI lock-in; single definition | one CHIPS-owned `repo_metrics_v` SQL view = sole panel source | CI check fails any dashboard JSON aggregating raw tables |
| No LLM judge in the reward → decision path | determinism; non-negotiable | **reward schema forbids non-deterministic inputs in active phases** (`w_review`/`w_latency` = 0 until verifier dominates; only deterministic terms admitted) | reward-schema validation test rejects non-deterministic source fields |
| Deterministic signature projection (byte-identical) | determinism; flagship sigmap claim | normalization spec (conformance matrix) + version pinning (griffe/tree-sitter) | cross-OS env-pinned golden tests |
| Online only after offline proof | don't degrade real briefs | explicit **unlock checklist** (§7) gated in this ledger | checklist must be fully checked + recorded before `online_bandit → active` |
| Mastery is reproducible | a product metric can't be path-dependent on label latency | mastery = pure function of the ordered, fully-labelled log; backfill ⇒ recompute-in-order | replay-twice equality test |
| Sidecar boundary (no model-call interception) | architectural identity | borrowed pieces are compile/observe/record only; reward/observability never intercept | design review gate |

**Conformance gating (the two flagged violations are promotion gates, not advisories):** where an invariant has a conformance test, the dependent capability stays `blocked` until that test **exists and passes** — `composite_reward` ⟂ the **reward-schema conformance test** (rejects any non-deterministic source field, incl. `w_review`); `bodyless_renderer` ⟂ the **cross-OS byte-identical golden** (catches env-dependent griffe resolution). This is enforced via the §2 test-gate column: a failing/absent conformance test means the capability cannot be promoted to `active`.

---

## 6. Data-sufficiency policy (Codex point 6 — "the biggest missing piece")

Every metric/learning system **must** declare these, or it stays `blocked`:

- **Minimum sample size** (`N_min`) before the metric/estimator is reported as anything but "insufficient evidence."
- **Insufficient-evidence state** — an explicit value (not 0, not null-coerced) surfaced when `n < N_min`; dashboards must render it distinctly.
- **Replay / backfill rule** — late labels trigger **recompute-in-order**; the metric is defined on the fully-labelled ordered log, never on out-of-order injection.
- **Aggregation level** — each metric declares **repo-level | scope-level | tenant-level** (and is RLS-safe once gap-#6 lands).

Global defaults live here; per-capability overrides live in each doc's **Data Contract** section. **No reward-consuming capability is promoted to `active` without these four filled.**

---

## 7. Unlock checklist — `online_bandit` (the highest-risk promotion)

`online_bandit` may move `blocked → active` only when ALL are checked and recorded here with date + evidence pointer:

- [ ] Phase-3 verifier exists and emits validated reward labels.
- [ ] `composite_reward` active and normalized; non-deterministic terms excluded.
- [ ] OPE active with a **calibrated uncertainty bound** on the reward model; "headroom" exceeds that bound.
- [ ] **Action-overlap diagnostic** shows sufficient variation for offline identifiability.
- [ ] Bounded exploration scoped to **one discrete knob** (reranker on/off or source-budget), ε small.
- [ ] **Realized-reward-drop / SPRT drift monitor** implemented with a numeric kill-switch threshold (NOT "regret" — regret isn't live-computable).
- [ ] Kill-switch reverts to the frozen deterministic policy; drill passed.
- [ ] Shadow-first path validated where feasible.
- [ ] **Data-sufficiency thresholds met** — every consumed metric/estimator is past its `N_min` (none in the insufficient-evidence state, §6).
- [ ] **Versioned replayability proven** — same log + same `policy_version` ⇒ byte-identical replay (reproducible OPE; no path-dependence on label latency).

---

## 8. Global readiness exit criteria (gates between phases)

- **Foundation → Activation:** decision_log populated with versioned schema; span contract test green; `repo_metrics_v` single-source + CI-enforced; normalization golden tests pass **across OSes**; bodyless spike report shows net token win without latency regression.
- **Activation → Optimization:** Phase-3 verifier emits validated labels for **≥ N_min repos**; `composite_reward` active + schema-enforced deterministic; action variation sufficient for OPE (measured).
- **Optimization gates:** each optimization capability has its own row prerequisites (§2) + the §7 checklist for online_bandit.

---

## 9. Decision log (ledger-level)

- **Accepted:** stage everything as gated capabilities; Foundation buildable now; reward-consumers frozen on the verifier; one ledger governs three docs; invariants become mechanisms; data-sufficiency mandatory.
- **Deferred:** mastery math, OPE, online bandit, rule induction, public sig anchors, staleness feeds, Superset, custom UI.
- **Rejected:** computing metrics in the BI layer (violates "metrics in CHIPS"); building reward-consumers before the verifier; sig public anchor before a consumer; standing up 4 surfaces at once.

---

### Cross-references
Governed docs (each rewritten to Foundation→Activation→Optimization with capability map, invariant table, data contract, failure modes, exit criteria): `02_06_contextual_bandit_design.md`, `02_06_signature_map_design.md`, `02_06_observability_analysis_architecture.md`. Review: `02_06_design_pressure_test.md`. Roadmap authority: `27_05_reasoning_runtime_roadmap.md` §3/§7.
