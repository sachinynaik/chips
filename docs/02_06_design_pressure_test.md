# Design Pressure-Test — CB / Sigmap / Observability (2026-06-02)

**Status:** REVIEW REPORT. Three independent adversarial reviewers (one per design doc), reconciled here against CHIPS's locked constraints. **Design docs are NOT yet revised** — this report is the input to the next Codex round; revisions follow after.
**Docs under test:** `02_06_contextual_bandit_design.md`, `02_06_signature_map_design.md`, `02_06_observability_analysis_architecture.md`.
**Method:** ruthless review mandate (gaps / mistakes / risks / hidden deps / failure modes incl. SPOFs / unknowns / critical decisions; modularity-testability-efficiency-maintainability audit; can it be simplified). Findings de-duplicated, severity-ranked, each given a **disposition**.

**Disposition legend:** `[ACCEPT]` fold into the design · `[PARTIAL]` accept the concern, modify the fix (often because a locked constraint bounds it) · `[REJECT]` with reason. **Severity:** 🔴 blocking · 🟠 major · 🟡 minor.

---

## 1. Executive summary — four cross-cutting themes

The reviewers independently converged on the same meta-problems. These matter more than any single finding:

1. **Over-built ahead of the verifier and the data.** All three docs design machinery that *cannot be validated* until the Phase-3 verifier and real logs exist. The reward-dominant term is null today; the metrics, OPE, and dashboards consume it. **Fix posture: ship only the no-regret foundations now (decision log + OTel emission + bodyless renderer + Grafana over existing signals); FREEZE everything reward/metric-consuming until the verifier lands and its reward shape is known.**
2. **Unenforced invariants.** Each doc states a load-bearing invariant with *no mechanism*: CB's "regret monitor" (and metric reproducibility), sigmap's "byte-identical determinism," observability's "metrics computed in CHIPS / span coverage." An invariant with no executable check is a wish — and gap #8 (docs-drift) says wishes drift. **Every invariant needs a concrete mechanism (conformance matrix / contract test / SQL view + CI check).**
3. **Scope outran the simplicity criterion (#3).** None of the three applied simplicity as a *gate*: sigmap builds a subsystem where a `bodies=False` toggle might do; observability adopts 4 surfaces + a bespoke UI where Grafana + MCP/CLI likely do; CB ships a 4×4 metric taxonomy + a rule-inducer before any reward exists. **Each must justify against a named minimal alternative.**
4. **Two laundered constraint violations.** CB's `w_review` term can smuggle an **LLM judge into the reward → decision path** (violates "no LLM judge in the decision path"); sigmap's **griffe resolution is environment-dependent** (violates determinism). Both must be explicitly guarded, not assumed away.

---

## 2. §A — Contextual Bandit design

### Blocking
- 🔴 `[ACCEPT]` **Offline OPE is unidentifiable on a deterministic single-policy log (action ⟂ context collinearity).** With `action = f(context)`, a reward model can't separate the action's effect from context; the counterfactual is unidentifiable except across `policy_version` variation. **The doc missed this** (it argued propensity=1, but not collinearity). → Require a measured **action-overlap diagnostic** (distinct actions per context cluster) as a precondition for Phase B producing *any* signal; state explicitly that offline OPE is identifiable only across policy-version boundaries.
- 🔴 `[ACCEPT]` **Direct Method gating the go-online decision is circular.** DM extrapolates to never-taken actions (OOD); the doc lets that biased estimate be the §7 unlock trigger — "we go online because DM says there's headroom" vs "DM can't be trusted, which is why we need to go online." → DM headroom counts **only** if it exceeds r̂'s own *validated* uncertainty bound (held-out calibration on the policy-version variation that exists). No uncertainty bound → DM may not gate.
- 🔴 `[ACCEPT]` **Reward-consuming components are built against a reward that doesn't exist yet** (verifier is Phase 3). Mastery, OPE, rule-inducer all consume `composite_reward` (verifier-dominant, null now). → Collapse near-term scope to **the decision log + OTel spans only**; freeze B/C/D and the metric math until the verifier emits validated labels (theme #1).
- 🔴 `[ACCEPT]` **`w_review` may put an LLM judge in the reward → decision path** (non-negotiable violation). CHIPS has an LLM-based `/code-review`/multireview. → Set `w_review` to **deterministic-only signals or 0**; state it explicitly.

### Major
- 🟠 `[ACCEPT]` **Reward hacking pre-verifier:** with the correctness term null and `−w_latency·latency`, the optimal policy is to *starve the brief* (retrieve less, short-circuit). → `w_latency = 0` (and `w_review = 0`) until the verifier term dominates.
- 🟠 `[ACCEPT]` **Mastery double-decays.** `(1−α)·mastery_{t−1}·decay(churn)` shrinks carried mastery geometrically *and* by churn, so a perfectly-performing repo under sustained churn trends to zero → false rot alarm. → Redesign the recurrence: churn should modulate **confidence/half-life**, not multiply an already-decayed term; recovery must come from good rewards, not from churn stopping.
- 🟠 `[ACCEPT]` **"Per-decision regret monitor" (§7) contradicts §5.2** ("regret not computable live"). → Replace with a concrete **realized-reward-drop / SPRT drift monitor** vs the frozen policy's expected reward, with a numeric kill-switch threshold.
- 🟠 `[ACCEPT]` **Reward-label backfill races make mastery/OPE non-reproducible.** Late `verifier_outcome`/`downstream_success` injected out-of-order into an ordered EMA → two replays differ. → Define **recompute-in-order on backfill** (mastery is a pure function of the ordered, fully-labeled log).
- 🟠 `[ACCEPT]` **No reward normalization spec.** Binary verifier vs ms latency vs thumbs live on different scales; un-normalized weights are meaningless. → Specify per-term normalization before weighting.
- 🟠 `[PARTIAL]` **"Compute mastery in BI, not CHIPS core"** (reviewer S2). → **REJECT the location change** (non-negotiable: metrics computed in CHIPS). **ACCEPT the concern:** don't bake unvalidated decay math into core now — store **raw component rewards**; compute only the **composite** in-core via a **versioned formula**; defer derived-metric math to post-verifier.

### Minor / schema
- 🟡 `[ACCEPT]` `context_features`/`action` JSONB need a **versioned feature-vector schema** (ragged matrices break OPE).
- 🟡 `[ACCEPT]` `policy_version` must be a **content hash**, not free text (reproducible replay grouping).
- 🟡 `[ACCEPT]` Decide **async-write loss** (synchronous, or document survivorship bias).
- 🟡 `[ACCEPT]` Continuous actions (ranking weights) need a **density-based estimator**, not discrete IPS — or restrict exploration to discrete arms (the doc already starts with one discrete knob; make that explicit as the *only* v1 action).
- 🟡 `[ACCEPT]` OPE needs **confidence intervals / min-sample-size**; on "modest volume" this is the whole game.
- 🟡 `[PARTIAL]` **Rule-inducer is a second project bolted on** + can learn wrong constraints from a noisy verifier. → Split into its own doc; add a verifier-confidence threshold before induction. (Keep the shared-log idea.)

---

## 3. §B — Signature-map design

### Blocking
- 🔴 `[ACCEPT]` **The determinism guarantee (§2 "byte-identical") is unbacked; its spec (normalization, §8.2) is an open question.** A determinism-first project cannot start TDD (§7) when there is no defined GREEN. → Write the **canonical normalization grammar as a closed conformance matrix** (one input construct → one exact output) *before* code: symbol ordering, whitespace, line-endings/Unicode NFC, type-annotation stance (`List` vs `list` vs `from __future__`), default-arg handling, decorators, `@overload`, PEP 695 generics, async/varargs/positional-only, docstring-first-line.
- 🔴 `[ACCEPT]` **griffe resolution is environment-dependent** (sys.path / load order / installed deps) → non-deterministic across machines (a determinism violation). → Add an **env-pinned cross-OS golden test**; forbid env-dependent resolution (or pin the resolvable surface).
- 🔴 `[PARTIAL]` **`find:` is the wrong precedent for normalization** (it hashes raw bytes; sigmap hashes a semantic projection). → ACCEPT: don't lean on `find:` for the hard part; the conformance matrix above replaces it. (The `find:` *hashing/anchoring discipline* for IDs is still fine to reuse — just not as the normalization answer.)

### Major
- 🟠 `[ACCEPT]` **Cut hash-anchoring from v1.** §3 already makes sigmap *non-citable context*; the only consumer of a durable public anchor is the CB churn-decay, which is "optional, later." → v1 = bodyless renderer + **internal** content hash for cache/dedup only; introduce the public `sig:` anchor when a real consumer + the conformance matrix exist. (Removes the entire normalization-stability risk from v1.)
- 🟠 `[ACCEPT]` **Maybe no new subsystem at all:** evaluate a `bodies=False` toggle on the **existing** structural/compression renderer before building `signature_map.py`. Prove the toggle insufficient first.
- 🟠 `[ACCEPT]` **Dual non-citable channels** (file-signals + sigmap) can **double-count the same file** in the tiktoken budget with no precedence. → One precedence rule; sigmap = symbol-level rendering of the *same selection*, not a parallel source.
- 🟠 `[ACCEPT]` **griffe is a dev-dep being promoted to the hot path** unacknowledged (violates "refuse the dependency" posture). → Justify explicitly or avoid; pick **griffe OR tree-sitter**, not both (no tie-breaker = ambiguity = nondeterminism).
- 🟠 `[ACCEPT]` **`sig:<content-hash>` looks like the citable `find:<content-hash>` family** → provenance confusion for a *non-citable* thing. → Namespace it so it can never be mistaken for a citable ID.
- 🟠 `[ACCEPT]` **Dataclass/pydantic synthesized members are griffe-version-dependent** → hash churn on the most common modern Python. → Scope synthesized members in/out explicitly.

### Minor
- 🟡 `[ACCEPT]` Non-Python "graceful degradation" is undefined → define as **"no sigmap tier"** (explicit), not vague partial maps.
- 🟡 `[ACCEPT]` Staleness trigger + cache-invalidation policy + latency budget unspecified (griffe whole-module loads in the hot path could cost more wall-clock than the token win) — hold sigmap to the same **ranx-style "measure it"** bar the gap-map demands of retrieval.

---

## 4. §C — Observability & analysis architecture

### Blocking
- 🔴 `[ACCEPT]` **Dropping Phoenix didn't simplify — it swapped 1 service for 4 + a bespoke app**, and the simplicity criterion was never applied as a gate (every candidate got ADOPT). → Re-justify each surface against a **named minimal alternative**; see §D.
- 🔴 `[ACCEPT]` **The "metrics computed in CHIPS, surfaces only visualize" invariant has no enforcement.** Superset/Grafana make forking a metric trivial and invisible (and gap #8 says it *will* happen). → Define each repo metric as a **single CHIPS-owned SQL view (`repo_metrics_v`)** that is the *sole* source for every panel; add a **CI check** failing any dashboard JSON that aggregates over raw domain tables.

### Major
- 🟠 `[ACCEPT]` **Cardinality contradiction:** §6.7 forbids high-cardinality Prometheus labels, but §3.1/§5 promise per-repo mastery/drift/freshness/risk **trends in Grafana** — which via Prometheus = the `repo×tenant×policy_version` cardinality bomb. → Per-repo trends come from **Postgres/DuckDB via Grafana SQL**, **never** Prometheus labels. State it; fix the §2 diagram.
- 🟠 `[ACCEPT]` **Dashboards are inert until the verifier + CB metrics exist** (theme #1) — the doc reads as if metrics are available now. → State the dependency; don't build dashboards against null data.
- 🟠 `[ACCEPT]` **"Review-gate check" for span coverage is undefined** → replace with a concrete **end-to-end contract test** asserting the expected span tree per brief (manual emission → silent gaps otherwise).
- 🟠 `[ACCEPT]` **Trace retention vs durable "why".** Tempo traces are sampled/retention-bounded; the durable per-brief "why" is the **decision log (CB §2)**, not the trace. → Fix the §5 responsibility matrix: traces = live/recent debugging; decision log = durable rationale.

### Minor
- 🟡 `[ACCEPT]` AGPL (Grafana) network-use clause bites if a custom UI ever **embeds** Grafana panels — note now.
- 🟡 `[ACCEPT]` State the **operator/analyst headcount** assumption — it's the hinge for the whole Superset/custom-UI justification (almost certainly 1–few).

---

## 5. §D — Revised minimal scope (the "do now vs freeze" line)

Synthesizing all three reviews into one buildable plan that honors determinism + local-first **+ simplicity**:

**DO NOW (no-regret foundations, post-A4, each with its enforcement mechanism):**
- **CB:** the **decision log** (`cortex_decision_log`) with a **versioned feature schema** + `policy_version` as content hash; **OTel/OpenInference emission** with an **end-to-end span contract test**. *(Compute only the composite reward, versioned; store raw components. No mastery math, no OPE, no rule-inducer yet.)*
- **Sigmap:** evaluate the **`bodies=False` toggle** on the existing renderer first; if a new module is needed, **bodyless renderer + internal cache hash only** (no public anchor, no §4), Python-via-one-extractor, non-Python = "no tier." Conformance matrix is the prerequisite.
- **Observability:** **Grafana only** as the standing surface — Prometheus (ops/alerts) + Postgres `repo_metrics_v` (trends) + Tempo as an *optional datasource* (not a surface). The **`repo_metrics_v` view + CI check** is the metric-ownership mechanism.

**FREEZE until the Phase-3 verifier exists + emits validated reward labels:**
- CB mastery/drift/freshness/risk math, OPE estimators, gated-online (§7), the rule-inducer (own doc).
- Sigmap public `sig:` anchor + hash-anchoring (until a real consumer exists).
- Superset (fallback: **DuckDB CLI / notebook** — zero standing services) and the **custom CHIPS UI** (fallback: **MCP/CLI + Grafana read-only**) — both only on *demonstrated* demand.

**Net:** the only standing new service is **Grafana**; the only new core code is the decision log + span emission + (maybe) a bodyless-render toggle — all testable now, none dependent on the absent verifier.

---

## 6. What's genuinely sound (keep)

- CB: the offline-first/gate-online instinct, the verifier-gated reward, the regret-internal/mastery-surfaced *intent*, bounded action space, sidecar boundary. The doc's self-awareness about propensity=1 is real (it just stopped one step short of collinearity).
- Sigmap: the module placement (pure layer, no builder/MCP coupling), and the "compaction-mode-not-citable" *decision* (consistent with A2a) — the anchor *surface* is what contradicts it.
- Observability: the layer seams (OTel vocabulary / compute-in-CHIPS / visualize-outside) and the Phoenix-drop rationale are correct — the sizing is the problem, not the shape.

---

## 7. Next steps

1. **Codex round** on the design docs + this report (the user is driving this).
2. **Then revise the three design docs** to the §D minimal scope + the `[ACCEPT]`/`[PARTIAL]` punch list. (I have not revised them yet — pending Codex + your call.)
3. A status banner has been added to each design doc pointing here.

### Cross-references
`02_06_contextual_bandit_design.md`, `02_06_signature_map_design.md`, `02_06_observability_analysis_architecture.md`; `27_05_reasoning_runtime_roadmap.md` §3/§7; `docs/research/openinference-assessment.md`.
