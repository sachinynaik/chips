# CHIPS — Build Brief (v1.0, reconstructed 2026-06-17)

> **What this is.** The parent build brief that `chips-yield-and-spof-addendum.md` and
> `chips-repowise-borrow-list.md` declare themselves addenda to. A0 found it absent from the repo —
> it had only ever existed as the architecture diagram plus the design conversation. This document
> reconstructs it from the locked design, *after* A0, so it is honest about the gap between the
> design and the code rather than describing the target as if it were built.
>
> **How to read it (governed by A0).** This is a **target-lineage** document. It describes where
> CHIPS is going. What runs today is the Postgres/pgvector context-compiler foundation; the entire
> control plane below is **aspirational** per `A0-architecture-reconciliation.md` §4. Read every
> "X does Y" as "in the target, X does Y; today, see A0's mapping." A0 is the reading convention;
> this brief is the destination; the addenda are its children.

---

## 1. Thesis — is it worth building, and why

CHIPS is worth building **iff its value is dominated by the rare high-consequence event, not the
common trivial one** — and that condition holds here. ~95% of fires/edits are trivial and need no
machinery. The justification is the tail: the migration that drops a column three services deep,
the change that breaks an in-flight workflow, the destructive operation on a cold path. Those are
low-frequency, high-consequence, and invisible to any single tool — exactly the profile humans
under-defend and infrastructure is worth building for.

The cost side is unusually low **for this stack specifically**: CHIPS mostly *harvests* legibility
already produced for other reasons (typed contracts, scaffolder, schema registry, git history).
High-tail-value + near-zero-marginal-legibility-cost is what makes it worth it. If the codebase
were illegible or had no destructive events, the answer would be "build an alias file and stop."
Neither is true.

**Two consumers, ranked separately.** CHIPS serves an *internal* consumer (the gate, defect
prevention — test: does it prevent a bad fire?) and an *external* consumer (partners/customers/
due-diligence — test: does it credibly demonstrate an enterprise-grade, controlled, reliable
platform?). A signal can be low-value internally and high-value externally. The discipline that
keeps the external consumer from becoming a sprawl alibi: **an external metric is allowed only if
it is a cheap projection of data computed anyway** — never its own subsystem.

---

## 2. The honest baseline (what's built vs target)

Per A0, the folder is two lineages:

- **Built:** the Postgres/pgvector context-compiler (`BriefBuilder`/`ContextBrief`), the harvester
  (git ingestion, co-change capture, file signals), and the Foundation tranche (`decision_log`,
  span emission, `policy_version`, `repo_metrics_v`, Grafana). Real, governed by
  `02_06_execution_ledger.md`.
- **Target (this brief):** the control plane — the Signoff FSM gate, the four-memory model
  (Oxigraph/Cognee/Qdrant/Letta), Promote→Tapeout, the Yield/Fragility/SPOF code-intelligence
  layer, and command-chips. **Aspirational.** The one *partial* foothold is the harvester's
  enrichment suite, whose highest-value signals (co-change entropy, defect calibration) are the
  thinnest stubs in the codebase.

This brief does not pretend otherwise. It states the target, then gives a build order that starts
from what's built.

---

## 3. Locked architecture (the target — do not re-litigate)

These are converged. Re-opening them is what causes a rip-out; the decisions themselves are not.

### 3.1 Vocabulary
Canonical terms are locked in `chips-diagram-update-spec.md` and indexed by A0 §2. Use them; do not
reinvent. Dead terms (AGE, `trust_tier`, `surgeon`, "biomarker", Tapeout-for-execute) are retired.

### 3.2 The Signoff FSM (execution plane — "CHIPS Foundry")
`Intent → DRC → Signoff → Fabrication → Audit → Feedback`, as a **state machine, not a pipeline**.

- **Single fire path.** CLI, MCP, and every harness converge on one chokepoint. The gate sits at
  the convergence, so surfaces are gated by construction.
- **DRC (Design Rule Checks)** — two **ternary** arms, **Policy Eval** and **Blast Radius Read**,
  each returning **clean / violation / unknown**, with **UNKNOWN → ESCALATE on both arms** (an
  uncheckable rule is not a pass — fail-safe, not fail-open).
- **Signoff Tier** — routes DRC outcome to **Auto Signoff** (low risk → Execute) · **Waiver**
  (augmented → Execute, exception recorded) · **Manual Signoff** (high/unknown → Signoff Review).
  The tier is a **stored floor + computed escalation**, not a static label.
- **Signoff Review** — a **resting state** (the system can sit here indefinitely), reached only by
  Manual Signoff. Transitions: **Approve → freshness re-check → Execute or Re-escalate** ·
  **Edit & Refire → new `fire_id` → re-enters the gate** · **Reject (terminal)** · **Abandon/
  Timeout (terminal)**. Reject and Abandon never reach Execute.
- **Fabrication / Execute** — irreversible execution; reached by Auto, Waiver, or approved Manual.
- **Audit + Feedback** — complete record (intent · evidence · rules · decision · human · outcome);
  feeds Cortex Signal + Memory to close the learning loop.
- **Immutability:** a fire instance is frozen at classification; edit-refire mints a new `fire_id`
  and reruns the gate. Every `fire_id` maps to exactly one classification and one decision.

### 3.3 Memory model (four systems, strict ownership)
- **Oxigraph — Truth Memory** (facts, blast-radius graph, provenance, `g:*` named graphs).
- **Cognee — Experience Memory** (tool-use episodes, success/failure, task outcomes).
- **Qdrant — Similarity Memory** (embeddings, semantic retrieval). *pgvector is today's stand-in.*
- **Letta — Coordination State** (orchestration, long-running tasks, checkpoints).

**Ownership (locked):** Truth in Oxigraph · Experience in Cognee · Coordination in Letta ·
Similarity in Qdrant.

**Crossings (gated):**
- **Cognee → Oxigraph only via Promote → Tapeout.** Experience and truth are stored separately; the
  promote membrane is the *only* sanctioned crossing, provenance-stamped so a promoted edge is
  never indistinguishable from a structural one.
- **Letta → Dispatch only as Caller (no authority).** Letta sequences and holds state but never
  bypasses the Signoff gate; a Letta-initiated destructive fire routes through DRC → Signoff →
  (Manual) Review like any other.
- **No Signoff bypass by any orchestrator or agent.**

**Edge-confidence hierarchy** (how the gate weighs conflicting signals): enforced contracts >
empirical/observed > structural/static > associative. Associative never gates a destructive fire.

### 3.4 The Materials layer (understanding plane) — full spec in `chips-materials-layer-spec.md`
The plane that builds and maintains CHIPS' verified model of the codebase, *before* the Foundry
fabricates fires against it. Governed by the **purity law**: nothing is believed unless assayed;
impurities (LLM inferences = **doping**) are allowed but always labeled with purity score + dopant
element; **no LLM-as-judge**; a gap stays a gap. Two components: **Assay** (read-only — characterize
purity + stamp freshness; certifies, never mutates) and **Refinery** (read-write — purify via
receipt-validation, **annealing**/dopant-swap, and gap-driven interview; never self-certifies).
Three orthogonal dimensions — **purity** (composition), **decay** (perishability rate, fed by the
evolutionary signals, tunable per context), **freshness** (clock) — never collapsed. **Versioned
truth (Dolt) + projection** (cheap parameterized model, own purity, coefficients *fitted* from
projection error, hierarchically pooled). **Risk = the delta-signature** every change (incl. design)
produces across all dimensions + Fragility/blast-radius/SPOF. The improvement track (private
coefficients, hidden team average, periodic low-ceremony reflection) is a *small breather, not a
pillar*. This plane *is* the deterministic-first competitive thesis: CHIPS is the assay office that
certifies what the harnesses produce — it complements them, never competes.

### 3.5 Promote → Tapeout (the experience→truth membrane)
`Experience (Cognee) → Promote (Validate) → Tapeout → Truth (Oxigraph)`. **Tapeout is reserved for
this step only** — the rare, irreversible commitment of a confirmed experience into canonical
truth. It is never used for Execute (Execute is high-frequency; Tapeout is rare — names match
frequency and irreversibility). A `SkillOpt`-style **gated optimizer** is the candidate mechanism
for evolving `prompt`-chips through this membrane, scoped to chips whose output is checkable against
existing conformance gates (not a general "evolve everything").

### 3.6 Code intelligence — Yield / Fragility / Inspection / SPOF
Full spec in `chips-yield-and-spof-addendum.md`; borrow rationale in
`chips-repowise-borrow-list.md`. In brief:
- **Inspection suite** of **fault signatures** (structural · evolutionary · people) computes a
  **Yield score** (external/demo evidence — **never a gate input**) and a per-region **Fragility**
  scalar (**gate input** — escalates Signoff via DRC).
- **Coupling** (change-together edge, → `g:coupling`) + **Entropy** (scatter on it) are the
  highest-value evolutionary signals. *Evolution beats structure for defect prediction* — the
  stack is structure-heavy, so the evolutionary signals are the priority.
- **SPOF register** (Knowledge / **Code-Hub** / Infra / Data / Source) — declared + derived;
  Code-Hub is the *derived* spine, computed from blast-radius graph **fan-in** (many dependents).
  Bare SPOF in a fire's reach escalates Signoff.
- **Blast radius** (area reached) ≠ **Fragility** (danger of the reached territory). Distinct.

### 3.7 Principles that decide placement and naming
- **Files are truth; every index/graph is a derived, reconstructable cache.**
- **Placement:** convergence-tolerant content (prose, design) → CRDT/AFFiNE; correctness-gated
  content (configs, chips-as-files) → Git (the conflict gate is a feature).
- **Naming:** a name must match the frequency and irreversibility of the thing it represents.
- **Inspection suite is a catalog of faults, not virtues** — never add the healthy pole of an axis
  for symmetry.

---

## 4. Build order (priority) — reconciled with A0

A0 changes the pragmatic first move. The original brief led with the gate's paper artifacts because
the gate carries the rip-out risk. That's still true *for the gate track*. But A0 reveals the
harvester is **built** and the highest-value signals are **stubs** — which means the cheapest path
to real, demonstrable value needs no control plane at all. So the order is two tracks:

### Track 1 — Code-intelligence vertical (nearest; builds on what exists; no gate needed)
The harvester runs; `cochange.py` (~19 LOC) and `defect.py` (~5 LOC) are stubs. These are the
highest-value signals in the entire design and they land in the existing Postgres tables
(`cortex_cochange_pairs` exists). This is the first vertical because it's the most value for the
least new scaffolding.

- **V1.1 — make the evolutionary signals real.** Co-change pairs → **change/co-change entropy**;
  compose into a **Fragility** scalar. In Postgres, no Oxigraph required.
- **V1.2 — define "what is a defect" and make defect signals real.** The labeling rule (bug-fix
  commit? revert? hotfix tag?) is now load-bearing for **three** things — Defect history, Defect
  density, *and* the Yield-score calibration — so settle it before computing any of them. Then
  `defect.py` → Defect history (time series) + Defect density (size-normalized).
- **V1.3 — compose the Yield score** (external/demo) and wire **Fragility** as a signal (it has no
  gate to feed yet — it's computed and surfaced, ready for Track 2).
- **V1.4 — seed the Materials layer (Assay first).** The evolutionary signals above ARE the inputs
  to Assay (purity from determinism of source) and to the decay model (churn/entropy/volatility →
  extrinsic decay). So Assay (read-only purity + freshness over the existing model) is the natural
  next step on the same harvester — no gate, no Oxigraph needed. Refinery, versioned-truth (Dolt),
  and the projection/coefficient/ceremony machinery follow once Assay produces real composition data
  to refine and a baseline to diff. Start the **versioned snapshots (Dolt)** early — like the defect
  corpus, the baseline is the unrecoverable thing.
- **Capture-now imperative:** start labeling the **defect corpus** *and* taking **versioned
  score-field snapshots** immediately, even before the scorers/Assay are finished. The corpus and the
  baseline are the unrecoverable things; the consumers are not.

### Track 2 — The gate (higher rip-out risk; paper artifacts before code)
The Signoff FSM does not exist and is where the safety guarantee lives. Its design artifacts must
precede its code — these are cheaper to get right in thought than in code:

- **P0 — partial-population decision table.** {each DRC input / named graph} × {fresh / stale /
  missing / failed-write} → gate action, worst-state-across-the-reach wins. This carries the
  rip-out risk: a silently partially-populated gate is worse than none. Build first within this
  track, before any gate code.
- **P1 — the ontology contract.** The `g:*` predicate vocabulary, named-graph partition scheme, and
  **versioning** (pinned predicate semantics; what happens to edges written under refined
  semantics; version-skew as a declared-unseen-class). Needed when Oxigraph lands.
- **P2 — one end-to-end validation slice.** A single real fire through DRC → Signoff → (Manual)
  Review → Execute → Audit, exercising one of each edge class **and** a deliberately-induced stale
  subgraph to prove escalation fires. Include one **Letta-coordinated** fire to prove the
  "caller, never authority" rule (a Letta-initiated Manual-Signoff fire still routes to a human).
  This is where Track 1 and Track 2 meet — the fire's blast radius uses the real Fragility signal.

### Trigger-gated — Oxigraph migration
Moving the truth-store from Postgres/pgvector to **Oxigraph + the gate subsystem** is intended
(provenance-partitioned graph traversal Postgres can't express cleanly). **Trigger: after the first
end-to-end vertical runs on the Postgres stack.** Not before. Recorded, not scheduled (A0 §6).

---

## 5. Declared residuals (unseen classes — surface, never silently omit)

The safety argument rests on these being shown at the gate, not hidden:
- **Undrivable cold paths** (reflection, webhooks, DR) — low coverage on the reach *escalates*.
- **Uncommitted WIP** — in no index by definition; best-effort open-PR check.
- **Unknown external consumers** — beyond declared contracts; a named blind spot.
- **ORM-generated SQL** beyond migration-SQL + query-log + schema-map — declared, not built.
- **Stale calibration** (mutation/defect weights past threshold → degrade to raw signals, declared).
- **Version-skewed edges** (written under refined ontology semantics) — a declared-unseen-class.

---

## 6. Anti-goals, stop conditions, simplify checkpoints

- **Add no more code-intelligence graphs.** Structural sufficiency is reached; gaps are *off* the
  code graph (evolution, runtime, contracts).
- **Do not skip Track 2 P0.** Building gate code before the partial-population table is the rip-out.
- **Never let a demo metric become a gate input** (the Yield-score / structural-signature trap).
- **Keep one ground-truth check independent of CHIPS' own graph** — dogfooding removes the control
  group; when the shared substrate is wrong it's wrong for both CHIPS and codebase-intelligence at
  once.
- **Measure the fire distribution** before over-building the gate (what fraction is Manual-Signoff;
  how often the computed radius changes a human decision). The tail justifies the machinery — but
  *know* the shape.
- **Simplify checkpoints (post-first-vertical):** (1) Letta ↔ Cognee boundary — merge if overlap
  persists; (2) DRC / Signoff / Foundry complexity — consolidate if unnecessary; (3) inspection-
  suite scope — keep only defect-predictive signatures, drop any added for symmetry.

---

## 7. Open decisions (carried; settle before the dependent build)

1. **"What is a defect" labeling rule** — load-bearing for Defect history, Defect density, and Yield
   calibration. Settle with the corpus (Track 1, blocks V1.2).
2. **Co-change support threshold + generated-code filter** — what makes an edge real; exclude
   ORM/scaffolded files (Track 1, V1.1).
3. **Yield calibration cadence + staleness threshold** — when weights re-fit; when they degrade.
4. **SPOF register ownership** — who maintains declared rows; cadence that keeps it from rotting.
5. **Demo-vs-gate metric boundary** — the explicit list, so no vanity metric leaks into the gate.
6. **Partial-population gate actions** (Track 2 P0) — the per-cell decision table.

---

## 8. Children & related documents

- `A0-architecture-reconciliation.md` — the reading convention and built-vs-target index. **Read
  first.**
- `chips-diagram-update-spec.md` — the canonical target architecture + vocabulary lock.
- `chips-reversible-compression-note.md` — the projection-layer purity boundary for reversible
  compression; lossy on the wire, lossless for audit/assay/gate/eval.
- `chips-yield-and-spof-addendum.md` — the Yield/Fragility/Inspection/SPOF spec (child of this).
- `chips-repowise-borrow-list.md` — borrow rationale for the inspection suite (child of this).
- `CHIPS CORTEX ARCHITECTURE DIAGRAM` (v1.1) — the canonical target visual.
- *Out of scope (different repo):* `slots-contract-issue-response.md` is the SpaceMate chat backend,
  not the CHIPS sidecar — shares the files-are-truth / generated-contract / gates-that-falsify
  pattern only.

---

*Reconstruction note: this brief was rebuilt from the design conversation after A0 found it absent
from the repo. It is recorded as a target-lineage document; A0 governs how it is read against the
built Postgres foundation. Like A0, it is a hand-authored node in the decision-provenance model the
target architecture is meant to eventually maintain automatically.*
