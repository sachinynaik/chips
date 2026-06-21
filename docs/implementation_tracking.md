# CHIPS Implementation Tracking

**Status:** Current-state truth layer for implementers.  
**Purpose:** one entry point for what is built, partial, blocked, deferred, and target-only across the CHIPS stack.  
**Authority model:** this document summarizes; it does not override:

- [`docs/adr/A0-architecture-reconciliation.md`](./adr/A0-architecture-reconciliation.md) for built-vs-target reading
- [`docs/02_06_execution_ledger.md`](./02_06_execution_ledger.md) for capability readiness and unlock gates
- [`docs/design_docs/18_06/chips-execution-decision-sheet.md`](./design_docs/18_06/chips-execution-decision-sheet.md) for the current execution program
- [`docs/known_limitations.md`](./known_limitations.md) for accepted debt and unresolved defects

## 1. How to read this document

This doc answers four questions fast:

1. What layers exist in the architecture?
2. Which of those layers are actually implemented today?
3. What is still partial, blocked, or deferred?
4. What should be built next without violating the current sequencing rules?

It is deliberately implementation-facing. If a capability is not in code, this doc says so plainly even if the target design is well-developed.

## 2. Layer map

| Layer | What it is | Current state | Primary authority |
|---|---|---|---|
| L0 | Document governance and vocabulary control | **built** | `adr/A0-architecture-reconciliation.md` |
| L1 | Built runtime foundation: context compiler, MCP, memory retrieval, decision log, spans, metrics authority | **built / partial** | `02_06_execution_ledger.md`, `CHIPS CORTEX V1 Spec.md` |
| L2 | Harvester and evolutionary signals: git history, co-change, defect corpus, file signals, snapshots, yield/fragility/assay substrate | **built / partial** | `design_docs/18_06/chips-execution-decision-sheet.md` |
| L3 | Foundation observability and analysis surfaces | **built / blocked** | `02_06_observability_analysis_architecture.md` |
| L4 | Evidence-ranked hypotheses and anti-regression constraint memory | **partial** | `27_05_phase1_evidence_hypotheses_contract.md`, `31_05_codex_remediation_plan.md` |
| L5 | Activation and optimization learning loop: composite reward, mastery, OPE, online bandit, rule induction | **blocked** | `02_06_contextual_bandit_design.md`, `02_06_execution_ledger.md` |
| L6 | Compact context / signature-map progression | **foundation built, activation blocked** | `02_06_signature_map_design.md`, `02_06_normalization_contract.md` |
| L7 | Target execution gate: DRC, Signoff, Fabrication, Audit | **target-only** | `design_docs/18_06/*`, `adr/A0-architecture-reconciliation.md` |
| L8 | Target multi-memory architecture: Oxigraph, Cognee, Qdrant, Letta, Promote/Tapeout | **target-only** | `design_docs/18_06/*`, diagram, A0 |
| L9 | Tooling spikes and companion tooling | **spike / borrow / reject mix** | `05_06_tool_adoption_roadmap.md`, ADR-002..ADR-008 |

## 3. What is implemented now

### L0 — Governance and reading order

**Built**

- A0 defines the two-lineage model: the built Postgres/pgvector system vs the target CORTEX end-state.
- The execution ledger is the readiness authority for what may be built next.
- The 18_06 decision sheet is the current execution-facing decision register.

**Why this matters**

- The repo no longer depends on tribal memory to know whether a doc is current, stale, target-only, or superseded.

### L1 — Built runtime foundation

**Built**

- Deterministic context compiler under `src/chips/compiler/`
- MCP server/tool surface under `src/chips/mcp/`
- Postgres/pgvector-backed memory retrieval
- Decision-log foundation
- Span emission and span registry
- `repo_metrics_v` / metrics-authority foundation
- Multi-tenant retrieval and policy wiring foundation

**Partial**

- EvidenceBundle / hypothesis contract is defined and partly implemented, but not fully assembled and wired end-to-end through MCP.
- Constraint memory exists in part, but manual operator/agent surfaces are incomplete.

**Blocked**

- Nothing reward-consuming in this layer may activate until the verifier exists.

### L2 — Harvester and first execution vertical

**Built**

- Git commit ingestion
- Co-change pair capture
- Defect-corpus capture
- File signals persistence
- Versioned file-signal snapshots
- Early yield / fragility / assay substrate

**Partial**

- Some enrichment analyzers are real; several still degrade to false-clean empty output on failure.
- Co-change exists as pair capture and downstream signals, but not as the target graph-native coupling model.
- The first vertical exists as a signal pipeline, not as the full end-state fire/gate system.

**Current sequencing rule**

- Track 1 is the active code path.
- Track 2 P0/P1 remain design artifacts first; do not build gate code before P0.

### L3 — Observability

**Built**

- OpenInference/OpenTelemetry span emission foundation
- Span contract and registry
- Grafana as the standing surface
- Metrics-authority discipline: surfaces visualize, CHIPS computes

**Blocked or incomplete**

- Trend surfaces that depend on contextual-bandit metrics remain blocked.
- Cross-OS normalization verification is still pending non-Linux CI/runners where required by the contract.

### L4 — Evidence, constraints, and anti-regression memory

**Built**

- Phase 1 evidence and hypothesis contract is locked
- Primitive evidence/hypothesis data types and scoring substrate exist
- Constraint ideas and retrieval-side use are defined and partly present

**Partial**

- Full EvidenceBundle assembly and submission/write-back loop are not yet fully wired
- Constraint MCP add/retire surface is still a gap
- Learned anti-regression memory is not yet fully operational as the controlling write-back loop

### L5 — Learning loop

**Built foundation only**

- Decision log
- Policy-versioning / versioned decision substrate
- Span/metrics foundations needed for later learning

**Blocked**

- Composite reward
- Mastery math
- OPE
- Online bandit
- Rule induction

**Blocking dependency**

- Phase-3 verifier labels

### L6 — Compact context and signature map

**Built**

- Normalization contract
- Bodyless renderer spike and measured token win

**Blocked**

- Promotion to active compact-context tier
- Public signature anchors
- Staleness feeds

**Blocking dependency**

- Contracted promotion gates from the execution ledger and signature-map design

### L7 — Target execution gate

**Not built**

- DRC Policy Eval arm
- DRC Blast Radius Read arm
- Signoff tier routing
- Signoff Review resting state
- Fabrication/Execute through the gate
- Audit as a real end-state execution loop

Any existing constraint injection or brief validation must not be described as “the gate.” A0 is explicit that the gate does not exist yet.

### L8 — Target memory architecture

**Not built**

- Oxigraph as truth memory
- Cognee as experience memory
- Qdrant as target similarity memory
- Letta as coordination state
- Promote -> Tapeout -> Truth flow

**Current reality**

- Postgres/pgvector remains the built substrate.
- These target stores are vocabulary and architectural destination, not yet committed implementation.

### L9 — Tooling and research spikes

**Current posture**

- Integrate bucket is intentionally sparse or empty.
- Some tools are approved only as spikes.
- Some are borrow-only pattern sources.
- Some are rejected or explicitly deferred.

Use `05_06_tool_adoption_roadmap.md` and ADR-002..ADR-008 rather than treating research notes as implied implementation commitments.

## 4. Pending work by layer

### Active now

- Continue Track 1 on the existing harvester substrate.
- Keep capture-now artifacts current: raw defect capture and versioned score snapshots.
- Close committed foundation and vertical gaps without jumping ahead into gate code or reward consumers.

### Partial and should be completed

- EvidenceBundle end-to-end wiring
- Constraint MCP surfaces and write-back path
- Remaining harvester / enrichment reliability gaps
- Rebuildability and truth-vs-derived enforcement on the harvester side

### Blocked by explicit prerequisites

- Composite reward and everything above it in the learning loop
- Public signature anchors and staleness feeds
- Online bandit
- Superset / custom CHIPS UI
- The Signoff gate and Foundry execution plane

### Deferred intentionally

- Demo/external yield surfaces before internal signal proof
- Admission-time chip safety
- Multi-repo federation before one vertical is proven
- Truth-store migration before its trigger conditions are met

## 5. High-signal current gaps

This section is the short list of load-bearing unfinished work, not an exhaustive backlog.

| Gap | Why it matters | Current source |
|---|---|---|
| EvidenceBundle not fully wired | blocks ranked hypotheses from becoming an operational loop | `31_05_codex_remediation_plan.md`, Phase 1 contract |
| Constraint MCP surface missing | anti-regression memory cannot close the loop safely | `known_limitations.md` L9 |
| Some analyzers still fail false-clean | weakens evidence quality silently | `known_limitations.md` L11 |
| Learning loop blocked on verifier | prevents any honest reward/mastery/OPE claims | execution ledger |
| Gate/Foundry not built | target safety/control plane does not exist yet | A0 + design_docs |
| Target memory architecture not built | current store is still the built simplification | A0 + design_docs |

## 6. Next slice by layer

This is the short operational queue by layer. It is intentionally concrete and sequencing-aware.

| Layer | Next slice | Why this is next | Constraint |
|---|---|---|---|
| L0 Governance | Keep this doc, A0, and the ledger aligned when layer status changes | prevents doc drift from becoming false truth | do not restate target ambition as built state |
| L1 Runtime foundation | Finish EvidenceBundle / hypothesis wiring and close remaining runtime integration seams | this turns the contract into a live compiler path | must respect ledger blocked states |
| L2 Harvester / signals | Enforce rebuildability and derived-vs-truth boundaries; continue Track 1 signal completion | this is the active vertical and highest-value code path | stay on Postgres/pgvector until trigger conditions change |
| L3 Observability | Keep Grafana and metrics-authority surfaces honest; avoid building blocked trend consumers early | observability is useful now, but only for active signals | no reward-consumer surfaces before verifier-backed metrics exist |
| L4 Constraints / anti-regression | Add the constraint MCP add/retire surface and finish write-back plumbing | closes the operator-safe anti-regression loop | human-confirm invariants stay intact |
| L5 Learning loop | Do not code reward/mastery/OPE/online-bandit until verifier unlocks them | avoids theater metrics and fake adaptivity | execution ledger is the gate |
| L6 Compact context | Only promote compact-context behavior after its explicit gates pass | measured token win alone is not enough | honor normalization and promotion gates |
| L7 Target gate | Keep as paper design until Track 2 P0 exists | protects against building the wrong gate too early | no gate code before P0 |
| L8 Target memory architecture | Keep current boundary clean so future store migration is a swap, not a rewrite | preserves optionality without paying migration cost early | do not deepen lock-in unnecessarily |
| L9 Tooling spikes | Run only spike-approved evaluations with explicit kill criteria | prevents tool-adoption gravity | no “interesting repo” becomes implied implementation |

## 7. Sequencing rules that still apply

- Do not build gate code before Track 2 P0 exists.
- Stay single-repo until one vertical is proven.
- Do not treat target design docs as built runtime descriptions.
- Do not activate blocked ledger capabilities early.
- Keep the current substrate simplifiable; avoid deepening lock-in unnecessarily.
- A gap stays a gap: do not rename partial or aspirational work as shipped.

## 7. Recommended reading order

For a new implementation session:

1. [`docs/adr/A0-architecture-reconciliation.md`](./adr/A0-architecture-reconciliation.md)
2. [`docs/design_docs/18_06/chips-execution-decision-sheet.md`](./design_docs/18_06/chips-execution-decision-sheet.md)
3. [`docs/02_06_execution_ledger.md`](./02_06_execution_ledger.md)
4. [`docs/known_limitations.md`](./known_limitations.md)

Then branch by concern:

- runtime/compiler: `CHIPS CORTEX V1 Spec.md`
- learning loop: `02_06_contextual_bandit_design.md`
- compact context: `02_06_signature_map_design.md`
- observability: `02_06_observability_analysis_architecture.md`
- tools and spikes: `05_06_tool_adoption_roadmap.md`

## 8. Maintenance rule

Update this document when one of these changes:

- a layer changes state: built, partial, blocked, deferred, target-only
- the current execution program changes
- a previously blocked capability is unlocked
- a gap moves from “known limitation” to resolved
- a target-only subsystem becomes partially or fully implemented

This document should stay short enough to orient an implementer quickly, and strict enough that it does not blur built code with target ambition.
