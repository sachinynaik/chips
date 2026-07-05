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

- EvidenceBundle assembly, MCP wire serialization, and deterministic hypothesis submission/ranking are built, but the anti-regression loop is not yet verifier-driven end to end.
- Constraint memory exists with manual operator/agent surfaces, but learned write-back remains only partially operational.

**Blocked**

- Nothing reward-consuming in this layer may activate until the verifier exists.

### L2 — Harvester and first execution vertical

**Built**

- Git commit ingestion
- Co-change pair capture
- Defect-corpus capture
- File signals persistence
- Versioned file-signal snapshots
- Truth-replay rebuild path for the current derived harvester tables from `cortex_git_commits`
- Early yield / fragility / assay substrate
- GitHub issue-metadata capture (`cortex_issue_refs`, injectable-client fetcher) feeding query-time defect-label tiers T1-T4
- Revert-introduced defect credit in `DefectPredictor.predict`

  (both bullets above verified behaviorally 2026-07-05 in the WSL harness, 23/23 tests green)

**Partial**

- Many enrichment analyzers and retrieval-side enrichers now expose truthful status; the remaining audit surface is narrower and more peripheral.
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
- EvidenceBundle assembly at build time and MCP wire serialization are built
- MCP hypothesis submission now ranks hypotheses deterministically against the wire `EvidenceBundle`
- Rejected-hypothesis write-back now emits and durably queues `ConstraintCandidate` review payloads for manual promotion
- Constraint ideas and retrieval-side use are defined and partly present
- Constraint MCP/operator surface exists for inspect/add/retire flows
- Constraint-candidate review queue exists for inspect/review flows

**Partial**

- Learned anti-regression memory is not yet fully operational as the controlling verifier-backed write-back loop

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

- Verifier-linked anti-regression write-back
- Remaining harvester / enrichment reliability gaps

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
| Anti-regression loop is not yet verifier-driven end to end | ranked hypotheses can now be queued and reviewed, but the system still lacks verifier-backed automatic reinforcement/retirement semantics | Phase 1 contract, current MCP surface |
| Some enrichment contracts still need audit | the main false-clean paths are fixed, but the entire enrichment surface is not yet proven truthful end to end | `known_limitations.md` L11 |
| Learning loop blocked on verifier | prevents any honest reward/mastery/OPE claims | execution ledger |
| Gate/Foundry not built | target safety/control plane does not exist yet | A0 + design_docs |
| Target memory architecture not built | current store is still the built simplification | A0 + design_docs |
| Harvester daemon is not deployed/running anywhere on the dev machine | defect-corpus and signal baselines only accumulate where the daemon runs; SpaceMate history is an unrecoverable baseline if not captured | `design_docs/05_07/chips-defect-corpus-harvest-spec.md` Gap A |

## 6. Next slice by layer

This is the short operational queue by layer. It is intentionally concrete and sequencing-aware.

| Layer | Next slice | Why this is next | Constraint |
|---|---|---|---|
| L0 Governance | Keep this doc, A0, and the ledger aligned when layer status changes | prevents doc drift from becoming false truth | do not restate target ambition as built state |
| L1 Runtime foundation | Connect the queued hypothesis/constraint review path to verifier-backed outcomes without violating the ledger gates | the deterministic submission and durable review surfaces are now real; the remaining gap is end-to-end loop closure | must respect ledger blocked states |
| L2 Harvester / signals | Continue Track 1 signal completion and tighten the remaining enrichment/reliability surface | the main truth-vs-derived boundary and replay path are now explicit; the remaining work is narrower | stay on Postgres/pgvector until trigger conditions change |
| L3 Observability | Keep Grafana and metrics-authority surfaces honest; avoid building blocked trend consumers early | observability is useful now, but only for active signals | no reward-consumer surfaces before verifier-backed metrics exist |
| L4 Constraints / anti-regression | Connect the now-built MCP/operator + hypothesis + review-queue surfaces into the verifier-backed anti-regression loop | closes the operator-safe anti-regression loop | human-confirm invariants stay intact |
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

## 8. Recommended reading order

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

## 9. Maintenance rule

Update this document when one of these changes:

- a layer changes state: built, partial, blocked, deferred, target-only
- the current execution program changes
- a previously blocked capability is unlocked
- a gap moves from “known limitation” to resolved
- a target-only subsystem becomes partially or fully implemented

This document should stay short enough to orient an implementer quickly, and strict enough that it does not blur built code with target ambition.
