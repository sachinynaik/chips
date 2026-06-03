# Review Wrapper & Sign-Off — Reasoning-Runtime Staged Program (2026-06-02)

**This is a thin review wrapper around the governing ledger `02_06_execution_ledger.md`.** The ledger is the **first-class authority** (control plane) for capability status and gates; this packet only (a) orients a reviewer, (b) records review status, and (c) poses sign-off questions. It **decides nothing on its own** — decisions live in the ledger and design docs and are labelled as such in §3.

**Framing (per Codex 2026-06-02): "keep full scope, execute via gated phases" — NOT a scope reduction.** Every capability stays in scope; each carries a readiness state:
- **active now** — prerequisites met, buildable (the first build tranche).
- **blocked by prerequisite** — in scope, awaiting a *named unlock artifact* (usually the Phase-3 verifier or a proven spike).
- **dormant but in scope** — preserved vision, intentionally unscheduled until demand.

**The control rule (explicit):** *no capability may move from blocked/dormant → active without a named unlock artifact AND a passing test gate, recorded in the ledger.*

**A4 is unchanged** — flag governor/reranker/structural OFF is still the next product-code slice; none of this reorders it. No product code has been written.

---

## 1. Authority & reading order

1. **`02_06_execution_ledger.md` — the control plane.** Capability registry, layer/status, prerequisites, unlock artifacts, test gates, dependency graph, invariant→mechanism table, data-sufficiency policy, unlock checklists. **Read first.**
2. `02_06_design_pressure_test.md` — the adversarial review behind the gating.
3. Design docs (gated, 13-section, Foundation→Activation→Optimization): `02_06_contextual_bandit_design.md`, `02_06_signature_map_design.md`, `02_06_observability_analysis_architecture.md`.
4. `27_05_reasoning_runtime_roadmap.md` §3/§7 — decision ledger (incl. §3.5 offline-first/gate-online).
5. Research: `research/{open-bias,re-gent,gap-tool-map,openinference}-assessment.md`.

---

## 2. Readiness snapshot (full scope, three states — authority is the ledger §2)

| Capability | State | Unlock artifact | Test gate |
|---|---|---|---|
| decision_log, span_emission, metrics_authority (`repo_metrics_v`), grafana_surface, normalization_contract, bodyless_renderer_spike | **active now** | — (foundation) | schema/round-trip · span contract test · CI dashboard check · cross-OS golden |
| composite_reward | **blocked** | Phase-3 verifier labels | reward-schema conformance test |
| mastery_math, OPE, rule_induction | **blocked** | reward + data sufficiency (+ action variation for OPE) | property/estimator tests |
| online_bandit | **blocked** | ledger §7 unlock checklist | shadow-run + kill-switch drill |
| sig_public_anchor, staleness_feeds, grafana_repo_trends | **blocked** | consumer / cache policy / CB metrics exist | anchor-stability / staleness-cost / SQL-sourced trend |
| superset, custom_chips_ui, tempo_trace_ui | **dormant but in scope** | demonstrated demand / stable workflows / trace-debug need | — until unlocked |

Nothing here is *removed* — only readiness differs.

---

## 3. Decisions (labelled — these are design choices, not neutral packet facts)

- **[DECISION]** `repo_metrics_v` is the single metric authority; surfaces only visualize (obs doc §8; ledger §5).
- **[DECISION]** Grafana is the only **standing** surface; Superset + custom UI are **dormant** until demand (obs doc §6/§11).
- **[DECISION]** The **first active build tranche** = the Foundation layer. This is an *implementation boundary*, **not** a scope cut — the rest is blocked/dormant, still in scope (ledger §3).
- **[DECISION]** Reward schema **forbids non-deterministic inputs** in active phases; `w_review`/`w_latency` = 0 until the verifier term dominates (CB §8).
- **[DECISION]** sigmap = compaction **mode**, non-citable; public anchor + hash-anchoring demoted to **Optimization** (sigmap §11).
- **[DECISION]** Phoenix dropped; OpenInference **conventions** adopted (roadmap §5/§7.3).

---

## 4. Sparse-data / insufficient-evidence (explicit, per ledger §6)

Every metric/estimator (`mastery`, `regret`, `drift`, `freshness`, `risk`, OPE values) must declare: **`N_min`**, an explicit **"insufficient evidence" state** (a distinct surfaced value, never coerced to 0/null) when `n < N_min`, **backfill = recompute-in-order**, and an **aggregation level** (repo / scope / tenant, RLS-safe). A metric below `N_min` is **never** reported as a number.

---

## 5. Sign-off questions (confirming pass)

1. Pressure-test findings (`02_06_design_pressure_test.md` §2–4): concur / downgrade / dispute?
2. Readiness staging: do you endorse the **active-now tranche** as the first build boundary, with the rest **blocked/dormant but in scope** (i.e. *not* a scope reduction)?
3. Tooling decisions (roadmap §7 + gap-map): endorse / modify?
4. Offline-first/gate-online: are the ledger §7 unlock conditions (now incl. **data-sufficiency thresholds** + **versioned replayability**) sufficient?
5. The two constraint violations (`w_review` LLM-in-reward; griffe env-dependent determinism): blocking + guards adequate (conformance tests + capability-state gating)?
6. Right thing, right way **as a staged program** (not a trimmed vision)?

---

## 6. Review log (factual, dated)

- **2026-06-02 — pressure-test:** three adversarial reviewers; findings reconciled in `02_06_design_pressure_test.md`.
- **2026-06-02 — Codex confirming pass:** conditional sign-off. Concur on pressure-test (no downgrades); endorse the active-now tranche as the first build boundary, **not** a scope cut; concur on tooling; gate-online to also require **data-sufficiency thresholds + versioned replayability**; both constraint violations blocking, guards must include **explicit conformance tests + capability-state gating**; "right thing, right way" **if treated as a staged program**. Requested packet reframing (full-scope/gated, ledger as control plane, label decisions, explicit promotion rule, sparse-data states) — **applied in this revision**.

---

### Deliverables index
- Governing ledger (control plane): `02_06_execution_ledger.md`
- Designs (gated): `02_06_contextual_bandit_design.md`, `02_06_signature_map_design.md`, `02_06_observability_analysis_architecture.md`
- Review: `02_06_design_pressure_test.md` · This wrapper: `02_06_codex_review_packet.md`
- Decision ledger: `27_05_reasoning_runtime_roadmap.md` (§3.5/§5/§7/§7.3)
- Research: `research/{open-bias,re-gent,gap-tool-map,openinference}-assessment.md`

All on branch `docs/tooling-research` (no PR). **A4 is next.**
