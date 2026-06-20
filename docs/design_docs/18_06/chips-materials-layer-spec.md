# CHIPS — Materials Layer Spec (v1.0, 2026-06-17)

> **What this is.** The specification of the **Materials layer** — the plane that builds and
> maintains CHIPS' verified model of the codebase, and the temporal-risk model that rides on it.
> This is the bulk of the design work that, before this doc, existed only in conversation. It is a
> **target-lineage** document (read under A0's convention); none of it is built yet.
>
> **One-line identity.** Code is raw material; CHIPS' verified understanding is *characterized*
> material; every belief is a sample of known (or explicitly unknown) composition. The Materials
> layer characterizes and refines that material so the Foundry (execution plane) can fabricate
> fires against trustworthy stock.

---

## 0. Position in the architecture

Two distinct planes, one fab pipeline — **no shared vocabulary, no collisions**:

- **Materials layer** (this doc) — *understanding*. Characterize and refine CHIPS' model of the code.
- **CHIPS Foundry** (Signoff FSM) — *execution*. Fabricate fires against the characterized model.

Pipeline: raw code → **Materials** (Assay characterizes, Refinery purifies) → trustworthy stock →
**Foundry** (DRC reads it, Signoff gates, Fabrication executes) → **Promote → Tapeout** commits
refined experience into Truth (Oxigraph).

The two planes are the **same event-measure-gate pattern applied to two domains**: the Foundry
measures and gates *work* (fires); the Materials layer measures and refines *knowledge* (beliefs).
That the core loop appears twice is the coherence signal, not duplication.

---

## 1. The purity law (the defining constraint)

> **No layer, node, edge, component, or function believes anything it has not verified through
> determinism. Impurities are permitted, but every impurity is labeled with its composition. No
> LLM-as-judge. A gap is a gap; uncertainty is labeled as such.**

Rationale: CHIPS' entire value is being deterministic-first. It **complements** coding harnesses
(Claude Code / Codex / OpenCode) — it does not compete with them. A harness is a *doping engine*:
brilliant at producing high-quality impurities (inferences) fast, and always better at that than
CHIPS. CHIPS is the **assay office** that certifies the composition of everything the harnesses and
the codebase produce. A harness *generates*; CHIPS *certifies purity*. If CHIPS ever believes
untracked impurities, it is just a worse harness. The law is the product.

Beliefs are not bad — the world runs on belief (money, contracts, intentions). The point is never
"no impurities"; impurities are often critical (as in doped silicon). The point is **always knowing
the exact composition.** An LLM-as-judge is forbidden specifically because it *hides* the doping —
it launders an inference into a verdict with no composition trail.

---

## 2. The three orthogonal dimensions

Every node/edge in the model carries three **independent** scores. They must never be collapsed into
one — collapsing them forces separately-tunable things into a muddy whole and destroys the ability
to act on each.

### 2.1 Purity — *composition* (owned by Assay; static until refined)
What a belief is made of: the **determinism fraction** + the **identity of every dopant**.
- A 100%-symbolic fact = pure. An Opus-inferred edge = doped, with `Opus` as the element.
- **Element metadata matters:** dopant identity includes the model (Fable/Opus more reliable than a
  small model), so purity is *score + element*, not one scalar. This enables targeted refinement
  (re-run a low-grade dopant with a better element, or replace it with a receipt entirely).
- Purity is **static** — it does not change unless the Refinery acts.

### 2.2 Decay — *perishability* (a modeled rate; NOT part of purity)
How fast a belief stops matching reality. Independent of purity: a pure fact about a frozen config
has near-zero decay; a pure fact about a hot module decays fast. Same purity, opposite decay —
which is exactly why decay must be separate.
- **Intrinsic decay** — half-life of the *kind* of belief (API-contract fact decays slower than an
  internal-impl fact; structural slower than behavioral).
- **Extrinsic decay** — driven by the *territory*: **churn, co-change entropy, volatility, crowding**
  — i.e. the evolutionary fault signatures feed the decay model. (Same signals feed Fragility; one
  source, two consumers.)
- **Tunable per context:** decay rates vary by team, stack, config regime, org mandate. Decay is a
  *fitted function with per-context parameters*, not a constant.

### 2.3 Freshness — *the clock* (stamped by Assay)
When the belief was last assayed, and against which code version. Decay *acts on* freshness; a
belief is trustworthy-now only if pure-enough **and** fresh-enough-given-its-decay-rate.

> Three numbers, never multiplied. *Purity* = "how much do I trust how this was derived." *Freshness*
> = "how long since I checked." *Decay* = "how fast does staleness matter here." A pure fact in a
> vacuum stays trustworthy for ages; a pure fact in a churning module needs frequent re-assay.

---

## 3. The two components

### 3.1 Assay — read-only characterization
Measures every node/edge → emits **purity** (determinism fraction + dopant element) and stamps
**freshness** (timestamp + code version). **Never mutates a belief.** The certification authority:
Assay measures composition and is forbidden to alter it. Every Refinery output is re-Assayed.

### 3.2 Refinery — read-write transformation
The only thing that *raises* purity. Operations:
- **Validate a receipt** → replace a dopant with deterministic backing (purity ↑).
- **Anneal** — re-run a low-grade dopant with a better element (swap a worse dopant for a better),
  relieving "stress" in low-purity beliefs.
- **Fill a gap** via the gap-driven, receipt-*validated* interview (§6) → convert an unknown into
  characterized material.
- Then **hand back to Assay** for re-characterization. The Refinery never self-certifies.

**Prioritization queue (the assay-vs-trust decision):** spend an expensive real assay vs. trust the
cheap projection when
`freshness-gap × decay-rate × stakes ÷ projection-track-record` is high.
This falls straight out of keeping the dimensions separate: high decay + stale + high stakes +
poor projection history → force a real assay before the gate trusts the belief.

> **Two components because two functions:** Assay measures (read-only); Refinery improves
> (read-write). One-directional trust: Refinery proposes, Assay disposes.

---

## 4. Versioned truth + projection

Two halves, both required:

- **Versioned state = the lab assay.** Real composition readings at points in time. Expensive, not
  continuous. **Immutable, shared, 100% deterministic ground truth.** Stored in **Dolt** (versioned,
  branchable, diffable, point-in-time reconstructable). The versioned state is *always* the source
  of truth.
- **Projection = the materials-behavior model.** A cheap parameterized model (simple algorithms over
  the versioned state) that projects scores *between* real assays. Per-user/team adaptable. Computed
  by the analytical engine (**DeltaX** candidate / **Timescale** fallback — both Postgres-native, so
  no new store).

**The projection has its own purity.** A projected score = `(last real assay: high purity) +
(decay model: an estimate)`, so it is *structurally lower-purity* than a versioned one, and tagged
as estimate. This dissolves anticipatory decay: pre-decaying a region on the strength of an ADR is
just a low-purity projection that the next real assay confirms or washes out. The model eats its own
dogfood.

**Coefficients are fitted, not magic numbers.** A hand-set coefficient is an untracked belief — the
forbidden thing. So the projection error *is* the calibration signal: a projection predicts score X
now; the next real assay measures Y; |X−Y| measures how good the model is for this kind of belief in
this kind of region, and the coefficients are re-fit against the team's own misprediction history.
The projection model thus has its own purity that *rises over time* (low at cold start, high once
validated). Cold-start priors are allowed — tagged low-purity until earned.

**Hierarchical pooling (required, not a nicety).** Coefficients are segmented (per team/stack/
kind/region) but **partially pooled**: a region with thin assay history inherits its team/stack/kind
rate, specializing only as it earns enough history. This is a *safety* property, not sophistication:
cold regions — exactly where the rare high-consequence event lives and where there's no local
history — get a conservative, honestly-low-purity estimate instead of a confident-wrong one
(e.g. "no churn history → decay ≈ 0 → trust this stale projection" is the failure pooling prevents).

---

## 5. Risk = the delta-signature

**Every change — including design — produces a new set of scores.** A commit, config edit, schema
migration, **ADR/design doc**, or fire is an *event that perturbs the model*. The complete way to
understand its risk is the **delta-signature** it produces:

- Δ purity (did beliefs get better- or worse-backed?)
- Δ decay (did regions start perishing faster?)
- freshness reset (what's re-verified vs newly-stale?)
- plus existing metrics: Fragility, blast radius, SPOF touch.

Design is just an *early event*: an ADR saying "we're rewriting auth" produces a high decay-Δ on
auth (beliefs now perishing), zero freshness change (no code moved), and is **itself low-purity**
(a stated intention, doped accordingly) — so a predicted change that never happens ages out harmlessly.

**Baseline requires the versioned store.** "A *new* set of scores" implies a previous set to diff
against — you cannot compute a delta-signature without reconstructing the model's state *before* the
event. This is why Dolt is essential, not optional. The score-field is **both**: a **versioned
artifact** (Dolt snapshots — fast to diff) **and** a **reconstructable projection** (simple
algorithms over versioned state — lean). The gate reads the delta-signature, not a static snapshot.

---

## 6. The improvement track (small — a breather, not a pillar)

> **Proportion first:** CHIPS is a tool for shipping better code faster by making AI-paired
> development safe and well-understood. This calibration track is a *small* improvement layer that
> rides along and occasionally helps a team get sharper. If CHIPS becomes *about* ceremonies and
> scores, it has failed. The verification is the product; the reflection is the kumbaya.

**Coefficients are private, set-and-forget.**
- Each individual sets projection coefficients privately, seeded by the onboarding interview (§7).
- **The team average is HIDDEN until the ceremony.** This is the key mechanic: a live average gets
  *watched, second-guessed, fiddled* — stealing attention from shipping. Hidden, the coefficient is
  fire-and-forget: set it honestly, forget it, ship code, rediscover it at the ceremony when reality
  has accumulated enough to be meaningful. The forgetting is a feature; a periodic reflection is
  destroyed by making it continuous.
- **Individual coefficients are 100% private — never shared, never ranked.** This makes misuse
  *structurally impossible* (no audience → no leaderboard, no blame, no gaming-for-status) rather
  than policed. The individual calibrates privately against two references: the (hidden-until-
  ceremony) team aggregate and the fitted reality.

**The unlock ceremony = a private calibration postmortem.**
- At lock-expiry, compare each person's *predicted* coefficients to the *fitted* reality. The delta
  is a private mirror of their own epistemics (optimist = under-predicted decay; etc.), offered only
  to that individual — self-knowledge, not a score.
- Scored (privately, if at all) by a **proper, symmetric** rule — penalize over- and under-prediction
  equally, so it rewards *calibration*, never *caution* (a caution-rewarding score would induce
  predict-high-everywhere → over-scrutiny).
- **Lock cadence starts long (~1 month), shortens as private calibration improves** and as CHIPS'
  understanding of the codebase grows. The lock freezes *self-serving re-editing* of the human prior;
  it never freezes the *fitted correction* from assay history, which runs continuously underneath.

**Anonymity floor:** on small teams (e.g. SpaceMate at founding size), "average + my private number"
can de-anonymize others. The aggregate must be coarsened (bands) or withheld until enough
contributors exist that it genuinely anonymizes. "Private" must hold under inference, not just by
declaration.

**Team-aggregate caveat (the last human-origin steering point):** the shared aggregate feeds the
pooling target for thin-data regions, so a collectively-optimistic team can drag everyone's cold-
region projections toward under-scrutiny — a blind-spot risk with no individual owner. Guard: the
**fitted reality overrides the aggregate** as assay history accumulates. The aggregate seeds;
reality governs. Same law as everywhere.

---

## 7. Onboarding as cold-start of a permanent layer

Onboarding is **not** a one-time event — it is the **cold-start mode of the Materials layer**, which
runs forever (continuously re-characterizing as code changes). First-run behavior:

1. **Deterministic-first audit.** Symbolic queries, dependency graphs, semantic contracts — build
   canonical understanding from structured truth, not LLM guessing. Token efficiency is *critical*
   precisely because the onboarding leans on symbolic/structured sources over expensive inference.
2. **Gap detection.** CHIPS marks what it *could not* determine deterministically — its declared
   unknowns. The interview is triggered *by* the gaps.
3. **Receipt-validated interview.** CHIPS asks *because it found a gap*; the human answers *with a
   receipt* (a pointer to a deterministic source); CHIPS **verifies the receipt against the code**
   before promoting the answer to canonical. An assertion without a validated receipt stays a
   low-purity belief — never laundered into fact. **Don't ask what you can measure:** team size,
   component maturity, stack are derivable (org graph, manifests) — measure those; interview only for
   genuinely tacit knowledge (domain risk, regulatory regime, mandates).
4. **Coefficient priors.** Interview answers about decay-driving variables (team size/structure,
   codebase maturity, domain, stack/component maturity) seed the projection coefficients — as an
   **explicitly low-purity, receipt-where-verifiable prior**, locked per §6, fitted-away-from by
   reality thereafter.

**Two success questions this layer must answer** (the dogfooding + extensibility test):
(a) how much does CHIPS help SpaceMate ship better code faster; (b) how fast can it cold-start a new
codebase. SpaceMate is the first project; CHIPS must generalize to others.

---

## 8. Tool slots (architecture-first; tools swappable)

| Slot (the requirement) | Candidate | Fallback / note |
|---|---|---|
| Versioned ground-truth state (immutable, branch/diff, point-in-time) | **Dolt** | essential, not optional — baseline for delta-signatures |
| Append-only analytical/OLAP engine (projection math + coefficient fitting) | **DeltaX** (Postgres-native columnar, Apache-2.0) | **Timescale** fallback; both Postgres-native (no new store). DeltaX is v0.1 — evaluate/watch. |
| Vector / similarity | pgvector (now) → **Qdrant** (target, with Oxigraph) | per the register's resolved decision |
| Truth graph | **Oxigraph** | AGE removed |
| Federated lexical retrieval | **Meilisearch + grep + Helix(ripgrep)** | one retrieval interface, multiple backends |

DeltaX read-only-compressed-partitions is *fine* for append-only analytical history and is exactly
why it does **not** subsume Dolt (which needs mutable branch/diff). Different needs, different stores.

---

## 9. Locked vocabulary (this layer)

**Materials layer** (the plane) · **Assay** (read-only characterize: purity + freshness) · **Refinery**
(read-write purify) · **Purity** (composition: determinism fraction + dopant element) · **Decay**
(perishability rate; intrinsic × extrinsic; tunable) · **Freshness** (last-assayed clock + version) ·
**Doping** (tracked impurity = LLM inference; carries score + element) · **Annealing** (Refinery's
purify/relieve-stress operation) · **Delta-signature** (a change's risk = Δ across all dimensions +
Fragility/blast-radius/SPOF) · **Projection** (cheap parameterized model over versioned state; own
purity; fitted coefficients; hierarchically pooled).

*Reserved (not yet locked — no referent):* Ingot, Wafer.

---

## 10. Open decisions (carried)

1. Granularity of versioned snapshots vs reconstruct-on-demand (both; tune the boundary).
2. Decay model: leading signals (ADR/mandate/open-PR as anticipatory, low-purity) vs purely reactive
   (churn-driven, lagging) — leaning both, anticipatory tagged low-purity.
3. Anonymity floor threshold for the team aggregate (contributor count / band coarseness).
4. Lock-cadence function — how calibration accuracy shortens the lock.
5. Whether private calibration couples mechanically to pooling weight (muted) or stays purely
   human-facing — leaning muted/none to avoid a metric with teeth.
6. DeltaX production-readiness gate vs Timescale fallback trigger.

---

*A target-lineage document under A0. A hand-authored node in the `g:decision` provenance model the
target is meant to maintain automatically. Vocabulary locked; tools and approach subject to `/simplify`.*
