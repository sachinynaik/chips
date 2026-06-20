# CHIPS CORTEX — Architecture Diagram Update Spec (for diagram generation)

> Purpose: regenerate the CHIPS CORTEX v1 architecture diagram with two additions integrated —
> the **Yield & Inspection layer** and the **SPOF Register** — without changing anything already
> locked. This spec is self-contained: it restates the locked architecture so the diagram is
> internally consistent, then specifies exactly what's new and where it attaches.
>
> Vocabulary is fixed. Use these exact terms. Plain-English labels with the technical metric as a
> sub-description; semiconductor framing where it matches the mechanism. Do not introduce new
> synonyms.

---

## 1. What's unchanged (restate, do not alter)

The diagram already has four planes; keep them exactly as locked:

**Surfaces (entry points):** Helix / CLI · Web UI / Signoff Console (human review) · MCP / Agents
· API / Integrations. (Zenith / Trace Cache belongs in Evidence & Telemetry Sources, READ-ONLY —
not a surface.)

**CHIPS Foundry (execution plane) — the Signoff FSM:** Intent → DRC → Signoff → Fabrication →
Audit → Feedback.
- **Single fire path** — all surfaces converge here.
- **Cortex DRC (Design Rule Checks)** — two arms: **Policy Eval** and **Blast Radius Read**, each
  ternary: **clean / violation / unknown**, with **UNKNOWN → ESCALATE on both arms**.
- **Signoff Tier** — outputs **Auto Signoff** (low risk) · **Waiver** (augmented) · **Manual
  Signoff** (high risk / unknown).
- **Signoff Review (RESTING STATE)** — reached only by Manual Signoff. Transitions: **Approve →
  freshness re-check → Execute or Re-escalate**; **Edit & Refire → new fire_id → re-enters the
  gate**; **Reject (terminal)**; **Abandon / Timeout (terminal)**. Reject and Abandon never reach
  Execute.
- **Execute (Fabrication)** — irreversible execution; reached by Auto Signoff, Waiver, and
  approved Manual Signoff.
- **Audit + Feedback** — complete record (intent · evidence · rules · decision · human · outcome);
  feeds **Cortex Signal** and **Cortex Memory** to close the learning loop.

**Cortex Core modules:** Retrieve · Signal · Sage · Signoff · Policy · Trace · Flow · Memory ·
Chronicle.

**Cognition & Memory layer (four complementary systems):** **Cognee** (Experience Memory) ·
**Oxigraph** (Truth Memory) · **Qdrant** (Similarity Memory) · **Letta** (Coordination State).

**Promote Pipeline (Experience → Truth):** Experience (Cognee) → Promote (Validate) → **Tapeout**
(rare, irreversible) → Truth (Oxigraph). Only sanctioned path; all promotions audited with
provenance.

**Locked rules banner (keep):**
- Ownership: Truth in Oxigraph · Experience in Cognee · Coordination in Letta · Similarity in
  Qdrant.
- Crossings (gated): Cognee → Oxigraph only via Promote → Tapeout · Letta → Dispatch only as
  Caller (no authority) · No signoff bypass by any orchestrator or agent.
- Guiding principle: a name should match the frequency and irreversibility of the thing it
  represents.

**Infrastructure (local-first):** Qdrant · Oxigraph · MinIO/Local FS · Ollama · Optional Postgres
· OpenTelemetry · SigNoz · Prometheus · Sentry. Context layer: Headroom · RTK · lowfat.

---

## 2. What's NEW — add these two blocks

### 2.1 Yield & Inspection layer (feeds Cortex DRC)

A new block that computes defect-predictive signals over code and emits a per-region **Fragility**
weight into the **Blast Radius Read** arm of Cortex DRC, plus a **Yield score** for the
external/dashboard consumer.

Draw it as a block feeding **into Cortex DRC's Blast Radius Read arm** (an arrow from this block to
that arm), and also feeding the dashboard/external surface (a lighter arrow, marked
"external/demo"). Internally the block contains:

- **Yield Score** (defect-validated 1–10 health score) — *labeled "external / demo evidence"*
- **Fragility** (defect-severity weight on blast radius) — *labeled "→ DRC escalation"*
- **Inspection Suite** — the fault signatures, grouped:
  - *Structural:* Complexity · Nesting depth · Bloat (function + class) · Cohesion · Duplication ·
    Vagueness
  - *Evolutionary (stronger predictors):* Coupling · Entropy · Churn · Volatility · Defect history
    · Defect density · Hotspot · Untested risk · Weak tests
  - *People & knowledge:* Crowding · Contention · Single owner · Orphaned code

Key visual relationships to show:
- This block **reads from** the Codebase Retrieval tools (Grep/Graphify/Serena/Semble) and **git
  history** — draw an input arrow from those.
- It **emits Fragility into Cortex DRC** (the important one — fragility escalates Signoff).
- **Coupling** is also a new edge subgraph in Oxigraph — show a thin link from the Inspection
  Suite's "Coupling" to Oxigraph labelled `g:coupling`.
- Mark the evolutionary signals as the gate-relevant set; mark Yield Score + structural as
  external/demo. (A small two-tone distinction is enough.)

### 2.2 SPOF Register (feeds Signoff Review)

A new block representing declared + derived single points of failure across the stack. It feeds
the **Signoff Review** (a fire whose blast radius routes through a *bare* SPOF escalates), and it
reads from deployment topology + the people signals.

Draw it as a block with an arrow into **Signoff Review** (escalation input) and an input arrow
from **Infrastructure** (topology) and from the Inspection Suite's people signals. Contents — four
categories:

- **Knowledge SPOF** — single owner, orphaned code
- **Code SPOF (Hub)** — an over-central unit, high fan-in (many dependents); the *derived*
  category, computed from the blast-radius graph
- **Infra SPOF** — Keycloak, CHIPS daemon, central Cognee, bus relays
- **Data SPOF** — Oxigraph blast-radius graph, audit log
- **Source SPOF** — the emitter (one wrong generation → all domains inherit the fault)

Each row conceptually carries: what it takes down · blast radius · mitigated vs bare. Show a small
"mitigated / bare" status indicator concept. Label the block "declared + derived · freshness-
tracked."

---

## 3. How the new blocks attach (arrows summary)

- Codebase Retrieval + Git history → **Yield & Inspection layer** (input)
- **Yield & Inspection → Cortex DRC (Blast Radius Read arm)** via **Fragility** (the load-bearing
  new arrow)
- **Yield & Inspection (Coupling) → Oxigraph** as `g:coupling` (thin edge link)
- **Yield & Inspection → Dashboard/External** via **Yield Score** (lighter "demo" arrow)
- Infrastructure topology + people signals → **SPOF Register** (input)
- **Blast-radius graph (Oxigraph fan-in) → SPOF Register** (the derived **Code-Hub** category)
- **SPOF Register → Signoff Review** (escalation input: bare SPOF in the reach → stickier manual
  signoff)

Nothing else changes. The Signoff FSM, the Promote/Tapeout pipeline, the four memory systems, the
crossing rules, and the locked banner all stay exactly as they are.

---

## 4. Vocabulary lock (use exactly; no synonyms, no biological terms)

Yield score · Fault signature · Inspection suite · Fragility · Complexity · Nesting depth ·
Bloat · Cohesion · Duplication · Vagueness · Coupling · Entropy · Churn · Volatility ·
Defect history · Defect density · Hotspot · Untested risk · Weak tests · Crowding · Contention
· Single owner · Orphaned code · SPOF register (Knowledge / Code-Hub / Infra / Data / Source).

Two distinctions the diagram must preserve:
- **Blast radius** (area a fire reaches) ≠ **Fragility** (scalar danger of the reached territory).
- **Coupling** (the change-together edge) ≠ **Entropy** (scatter score on that edge).

Consumer split to show subtly: **Fragility, Coupling/Entropy, and bare-SPOF are gate inputs**;
**Yield score and structural signatures are external/demo evidence** — never gate inputs.

---

## 5. Notes for the generator

- Keep the existing visual language (planes, the Foundry as centerpiece, the Signoff FSM as a
  branching state machine with terminal Reject/Abandon, the Promote→Tapeout pipeline).
- The two new blocks should read as *additions that feed existing nodes*, not new planes — Yield &
  Inspection feeds DRC; SPOF Register feeds Signoff Review.
- Do not reference or resemble any third-party tool; these are native CHIPS concepts.
- Preserve the frequency/irreversibility guide in the footer (High frequency: DRC, Signoff,
  Fabrication, Audit · Low frequency: Promote → Tapeout) and the KEY GUARANTEES and SIMPLIFY
  CHECKPOINTS blocks. Add to SIMPLIFY CHECKPOINTS a third item: *Inspection suite scope — keep
  only defect-predictive signatures; drop any added for symmetry.*

---

## v1.2 DELTA — add the Materials layer (for the next diagram regeneration)

> This is a delta to be folded in when the diagram is next regenerated. Full spec:
> `chips-materials-layer-spec.md`. It does not change anything locked above.

**New plane: the Materials layer** — sits *before* the CHIPS Foundry in the pipeline
(raw code → **Materials** characterizes/refines → trustworthy stock → **Foundry** fabricates fires).
Two distinct planes; no shared vocabulary (Foundry/Fabrication = execution; Materials = understanding).

Contents to draw:
- **Assay** (read-only) — characterizes each belief: emits **Purity** (determinism % + dopant
  element, incl. model name) and stamps **Freshness** (timestamp + code version). Certifies; never
  mutates.
- **Refinery** (read-write) — raises purity via receipt-validation, **annealing** (dopant swap), and
  gap-driven interview; prioritized by `freshness-gap × decay × stakes ÷ projection-track-record`;
  hands back to Assay. Never self-certifies.
- **Three dimensions** (drawn as distinct, never merged): **Purity** (composition) · **Decay**
  (perishability rate — fed by the evolutionary fault signatures) · **Freshness** (clock).
- **Versioned truth (Dolt)** → immutable ground-truth snapshots · **Projection** (DeltaX/Timescale)
  → cheap model over versioned state, *own purity*, fitted coefficients, hierarchically pooled.
- **Delta-signature** — every change (incl. design/ADRs) emits Δpurity/Δdecay/Δfreshness +
  Fragility/blast-radius/SPOF; risk = the signature. (Show ADR/design as an event that produces scores.)

Arrows:
- Evolutionary fault signatures (from the Inspection suite / harvester) → **Decay model** (extrinsic
  rate) and → **Assay** (purity inputs).
- **Assay → versioned truth (Dolt)**; **Projection** reads Dolt; **Refinery → Assay** (re-characterize).
- **Materials layer → Foundry/DRC**: the characterized, purity-scored model is what Blast Radius Read
  consumes (a fire reads *trustworthy stock*, with each belief's purity/decay/freshness available).

The improvement track (private coefficients, hidden-until-ceremony team average, periodic low-ceremony
reflection) is a small side-panel at most — **not** a central plane. Verification is the product.

**Vocabulary to add (locked):** Materials layer · Assay · Refinery · Purity · Decay · Freshness ·
Doping · Annealing · Delta-signature · Projection. *(Reserved, do not draw yet: Ingot, Wafer.)*
