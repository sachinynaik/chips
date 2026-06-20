# A0 — Architecture Reconciliation: the reading convention for `docs/`

**Date:** 2026-06-17
**Status:** Accepted — standing index. Consult this file before trusting any other doc in `docs/` or `docs/design_docs/`.
**Author:** human-directed (Sachin), hand-authored as the first node of the decision-provenance model the architecture is meant to track automatically (see §7).

---

## 0. Why this document exists

`docs/` was written across a long, evolving design process. It is **design-converged, not
implementation-validated**: much of it describes a *target* architecture that does not exist in
code today. Worse, the docs were written at different points in a moving conversation, so some use
**superseded vocabulary**, assert decisions that were **later reversed**, or omit subsystems added
late. Nothing in the folder told a reader which doc was authoritative.

A0 is that missing index. It does **not** rewrite or delete any doc — superseded docs are kept
exactly as written, because the record that the design *moved* is valuable provenance (the same
reason a superseded ADR is never deleted). A0 only tells you **how to read** the set.

The single most important fact about this folder:

> **The folder contains two distinct lineages.** A *built* lineage (the Postgres/pgvector
> context-compiler, governed by `02_06_execution_ledger.md`) and a *target* lineage (the CHIPS
> CORTEX v1 end-state — the architecture diagram + everything in `docs/design_docs/`). The target
> lineage describes where the system is going; it is **mostly not built**. Until now, no document
> bridged the two. A0 is that bridge.

---

## 1. The reading convention (read this first, every time)

1. **Every doc in `docs/design_docs/` and the architecture diagram describes the TARGET
   architecture.** When such a doc says *"X feeds the DRC arm"* or *"co-change lands in Oxigraph as
   `g:coupling`"*, read it as: *"in the target architecture X feeds DRC / lands in Oxigraph; **today**,
   here is the Postgres-stack equivalent or the stub — see the §4 mapping table."* These are
   statements of intent, not descriptions of running code.

2. **The built system is the Postgres/pgvector context-compiler**, specified by
   `CHIPS CORTEX V1 Spec.md` and governed for *build status* by `02_06_execution_ledger.md`. If you
   want to know what actually runs, start there and in `src/chips/`.

3. **The gate does not exist.** The Signoff FSM (Intent → DRC → Signoff → Fabrication → Audit) is
   **aspirational**, not partial (§4). Do not read `decision_log`, constraint-injection, or any
   existing check as "the gate, sort of." It isn't. The safety argument the design makes depends on
   that FSM existing for real, and it does not yet.

4. **Use the canonical vocabulary in §2.** Where a doc uses a dead term (AGE, `trust_tier`,
   `surgeon`, "biomarker"), §2 gives the live term and §5 flags the doc.

5. **`02_06_execution_ledger.md` remains the authority for what may be *built* next** within the
   built lineage. A0 governs *how to read the whole folder*; the ledger governs *build readiness of
   the foundation*. They do not conflict — A0 is the wider frame, the ledger is the build gate.

---

## 2. Canonical vocabulary (single source of truth)

Use these terms. Where an older doc uses the dead term, it is listed → with the live term.

### 2.1 The execution gate (target)

| Canonical term | Meaning | Dead/earlier terms (do not use) |
|---|---|---|
| **Fire / Dispatch** | One execution of a unit of work through the single fire path. | — |
| **CHIPS Foundry** | The execution plane: the Signoff FSM. | — |
| **DRC (Design Rule Checks)** | Pre-execution checks; **two ternary arms** — **Policy Eval** and **Blast Radius Read**; each returns **clean / violation / unknown**; **UNKNOWN → ESCALATE** on both. | — |
| **Signoff Tier** | DRC outcome routing: **Auto Signoff** (low risk) · **Waiver** (augmented) · **Manual Signoff** (high/unknown). | `trust_tier`; `safe` → Auto, `augmented` → Waiver, `surgeon` → Manual; "trust / triage / clearance" |
| **Signoff Review** | The **resting state**, reached only by Manual Signoff. Transitions: Approve → freshness re-check → Execute or Re-escalate · Edit & Refire → new `fire_id` → re-enters gate · Reject (terminal) · Abandon/Timeout (terminal). | — |
| **Fabrication / Execute** | Irreversible execution. Reached by Auto Signoff, Waiver, or approved Manual Signoff. | — |

### 2.2 Memory & the promotion pipeline (target)

| Canonical term | Meaning | Dead/earlier terms |
|---|---|---|
| **Oxigraph — Truth Memory** | The target truth-store; provenance-partitioned named graphs `g:*` (`g:co-change`/`g:coupling`, `g:decision`, …). | **Apache AGE — REMOVED.** Do not use AGE anywhere. |
| **Cognee — Experience Memory** | Accumulated learnings/decisions/gotchas (remember/recall/forget). | — |
| **Qdrant — Similarity Memory** | Vector/similarity retrieval (target). | pgvector is today's equivalent (not a synonym — see §4). |
| **Letta — Coordination State** | Coordination/historian (Cortex Chronicle). | — |
| **Promote** | The *only* sanctioned Experience → Truth path: Experience (Cognee) → Promote (Validate) → Tapeout → Truth (Oxigraph). | — |
| **Tapeout** | The rare, irreversible final step of **Promote** into Truth. **Reserved for Promote ONLY — never for Execute / fire.** | (misuse: "Tapeout" for execution) |

### 2.3 Code-intelligence: yield / fragility / SPOF (target)

| Canonical term | Meaning | Dead/earlier terms |
|---|---|---|
| **Fault signature** | One deterministic defect-predictive signal. | **"biomarker" — dead.** |
| **Inspection suite** | The full set of fault signatures (Structural · Evolutionary · People). | "25 biomarkers" |
| **Yield score** | Defect-validated 1–10 health score. **External/demo evidence only — never a gate input.** | — |
| **Fragility** | Defect-severity scalar weight on a fire's blast radius. **Gate input** (escalates Signoff via DRC). | — |
| **Blast radius** | The *area* a fire reaches. Distinct from Fragility (the *danger* of the reached territory). | — |
| **Coupling** | Files that change together (the edge → `g:coupling`). Distinct from Entropy. | — |
| **Entropy** | Scatter score *on* a region's coupling/changes. | — |
| **SPOF register** | Declared + derived single points of failure: **Knowledge / Code-Hub / Infra / Data / Source**. Code-Hub is the derived category (high fan-in from the blast-radius graph). | — |

**Consumer split (load-bearing):** Fragility, Coupling/Entropy, and bare-SPOF are **gate inputs**;
Yield score and structural fault signatures are **external/demo evidence** and must never silently
become gate inputs.

### 2.4 Built-lineage vocabulary (these terms describe real code)

| Term | Meaning |
|---|---|
| **Context compiler / `BriefBuilder` / `ContextBrief`** | The deterministic brief-compilation pipeline (built). |
| **EvidenceBundle / constraint / evidence / finding** | Phase-1 hypothesis contract (`27_05_phase1_evidence_hypotheses_contract.md`). `find:<content-hash>` IDs (positional IDs were reversed out). |
| **`decision_log` / `policy_version` / `composite_reward` / mastery / OPE / bandit** | The contextual-bandit learning loop. Foundation (`decision_log`, spans, `policy_version`) is **active**; reward-consumers are **blocked on the Phase-3 verifier**. |
| **`repo_metrics_v`** | The single CHIPS-owned SQL metric authority; surfaces only visualize. |
| **Chip** | Unit of executable knowledge (the command-chip product). **Aspirational** — see §4. |

> **One naming bridge to remember:** the command-chip spec's `trust_tier: safe | augmented |
> surgeon` is the **same axis** as the Signoff Tier (Auto / Waiver / Manual). It is stale wording,
> not a competing design.

---

## 3. The two lineages, at a glance

| | **Built lineage** | **Target lineage** |
|---|---|---|
| **Defines** | What runs today | The intended end-state |
| **Authority doc** | `02_06_execution_ledger.md` (build status) + `CHIPS CORTEX V1 Spec.md` (executable schema) | `chips-diagram-update-spec.md` + `CHIPS CORTEX ARCHITECTURE DIAGRAM.png` (canonical target + vocabulary lock) |
| **Truth-store** | Postgres / pgvector | Oxigraph (Truth) + Cognee + Qdrant + Letta |
| **Execution** | Compiles briefs; records `decision_log`. **No gate.** | Signoff FSM (DRC → Signoff → Fabrication) |
| **Code intel** | Harvester enrichment (some real, some stubs) | Inspection suite → Yield/Fragility; SPOF register |
| **Lives in** | `docs/*.md` (dated 27_05 → 05_06) + ADR-001..008 | `docs/design_docs/*` + the diagram |

The built lineage is internally well-governed and self-reconciled (e.g. `28_05` → `31_05`;
finding-ID churn already resolved). The target lineage had **no** governing index before A0.

---

## 4. Target → current mapping (built / partial / aspirational)

**Honesty rule applied:** a component is **aspirational** if no code implements its mechanism, even
if a loosely-similar check exists. It is **partial** only if a real, partial implementation of *that*
mechanism exists. It is **built** if it runs today.

| Target component (diagram / design_docs) | Current implementation | Status |
|---|---|---|
| **Context compiler** (`BriefBuilder`, `ContextBrief`, ranking, compression, MCP) | `src/chips/compiler/` — built & decomposed (A3) | **built** |
| **Harvester** (git ingestion, co-change capture, file signals) | `src/chips/harvester/` + `cortex_git_commits`/`cortex_cochange_pairs`/`cortex_file_signals` | **built** |
| **`decision_log` / span emission / `policy_version` / `repo_metrics_v` / Grafana** | Foundation tranche — all active | **built** (learning *consumers* remain blocked) |
| **EvidenceBundle / hypotheses contract** | Primitives committed; assembly/serialization in progress; not fully wired to MCP | **partial** |
| **Inspection suite — fault signatures** | `enrichment/`: `ownership.py`, `clones.py`, `complexity.py`, `architecture.py`, `security.py` real; `cochange.py` (~19 LOC), `defect.py` (~5 LOC), `refactoring.py` (~5 LOC) stubs | **partial** |
| **Coupling / `g:coupling`** | `cortex_cochange_pairs` (Postgres table) + `CochangeFetcher` stub. Co-change *pairs* partial; **change-entropy not computed**; no graph. | **partial** |
| **Fragility** (defect-severity scalar → DRC) | none — no composition, no defect calibration corpus | **aspirational** |
| **Yield score** (1–10 defect-validated) | none — no composed score | **aspirational** |
| **SPOF register** (incl. derived Code-Hub from fan-in) | none — no blast-radius graph, no fan-in computation | **aspirational** |
| **Blast Radius Read** (DRC arm) | none — no blast-radius traversal exists | **aspirational** |
| **Policy Eval** (DRC arm, ternary) | Build-time constraint injection into briefs exists, **but that is not a ternary gate arm** — it decorates briefs, it does not gate a fire | **aspirational** (as a DRC arm) |
| **Signoff Tier** (Auto / Waiver / Manual) | none | **aspirational** |
| **Signoff Review** (resting-state FSM) | none — no resting state, no Approve/Reject/Abandon transitions | **aspirational** |
| **Fabrication / Execute** | none — CHIPS compiles briefs; it does not execute work through a gate | **aspirational** |
| **The Signoff FSM as a whole** | **does not exist** | **aspirational** |
| **Oxigraph — Truth Memory / `g:*` named graphs** | Postgres/pgvector (`cortex_*` tables, HNSW) | **aspirational** |
| **Qdrant — Similarity Memory** | pgvector HNSW on `cortex_memories.embedding` | **aspirational** (pgvector is the current stand-in) |
| **Cognee — Experience Memory** | none integrated (`cortex_constraints` is the nearest Postgres analog, not Cognee) | **aspirational** |
| **Letta — Coordination State / Cortex Chronicle** | none | **aspirational** |
| **Promote → Tapeout → Truth** | none — no Cognee→Oxigraph promotion path | **aspirational** |
| **Command-chips** (`chip.compile/context/dispatch/promote`, trust gate, harness mirrors) | none — greenfield product | **aspirational** |
| **Context-compression layer** (Headroom / RTK / lowfat) | not integrated; companion-tool bake-off approved (ADR-003 `zap` vs `RTK`), tool roadmap open | **aspirational** (spike-gated) |
| **Zenith — contract-indexed trace cache** | not integrated; spike approved, integration undecided (ADR-002) | **aspirational** (spike-gated) |

**Headline:** the entire CORTEX-v1 *control plane* (Signoff FSM, four-memory model, Promote→Tapeout,
Yield/Fragility/SPOF) is **aspirational**. What is **built** is the Postgres context-compiler
foundation. The one real **partial** foothold for the code-intelligence vision is the harvester's
enrichment suite — and its highest-value target signals (co-change entropy, defect calibration) sit
in the thinnest stubs.

---

## 5. Per-doc status register

Tags: **current** (reflects final locked design) · **superseded-by:`<doc>`** · **target-architecture**
(intended end-state, not current code) · **stale-vocabulary** (right ideas, dead terms). Each doc
gets exactly one primary tag; cross-doc conflicts are named in the last column.

### 5.1 Built lineage — `docs/*.md` and ADRs

| Doc | Primary tag | Conflicts / notes |
|---|---|---|
| `CHIPS CORTEX.md` | **superseded-by:`CHIPS CORTEX V1 Spec.md`** (architecture) **& diagram** (end-state) | Original vision. Its *principles* (evidence>guessing, deterministic-first, local-first, compile-don't-dump) remain canonical and are still quoted. Its *component architecture* is outdated: names Qdrant + Letta but **no gate, no Oxigraph, no AGE either**. Read for philosophy only. |
| `CHIPS CORTEX V1 Spec.md` (2026-05-12) | **current** | The executable Postgres/pgvector architecture that was built (Phases 1–4). Its *end-state* is superseded by the diagram (four-memory + gate). Phase-5 OSS packaging is forward-looking. |
| `27_05_chips_generic_vs_stack_specific_roadmap.md` | **current** | Generic-core vs adapters; 7 generic evidence types. Still cited as companion. |
| `27_05_phase1_evidence_hypotheses_contract.md` | **current** | LOCKED Phase-1 contract. `find:<content-hash>` IDs. |
| `27_05_reasoning_runtime_roadmap.md` | **current** | Living roadmap / decision ledger; cited by the execution ledger as roadmap authority. |
| `28_05_v1_foundation_milestone.md` | **superseded-by:`31_05_codex_remediation_plan.md`** | Self-declares stale; open items moved to 31_05. Kept for provenance. |
| `31_05_codex_remediation_plan.md` | **current** | APPROVED; supersedes 28_05 open items; Track A slices (A0–A6). |
| `02_06_execution_ledger.md` | **current** | **GOVERNING authority for build status** of the built lineage (active/spike/blocked/dormant). |
| `02_06_codex_review_packet.md` | **current** | Sign-off wrapper around the ledger (2026-06-02 conditional pass). |
| `02_06_contextual_bandit_design.md` | **current** | Foundation active; reward-consumers blocked on Phase-3 verifier. |
| `02_06_signature_map_design.md` | **current** | Note its own churn: public `sig:` anchor moved Foundation → Optimization. |
| `02_06_observability_analysis_architecture.md` | **current** | Grafana-only standing surface; `repo_metrics_v` authority; Phoenix dropped for OpenInference. |
| `02_06_design_pressure_test.md` | **current** | Adversarial review record (2026-06-02); findings folded into the three design docs. Historical input, not contradicted. |
| `02_06_normalization_contract.md` | **current** | Closed determinism rules; cross-OS verification pending a non-Linux runner. |
| `02_06_bodyless_renderer_spike_report.md` | **current** | Spike complete (90.5% token win, ~0 latency); promotion gated on normalization + cross-OS golden. |
| `observability_chips_span_registry.md` | **current** | Live span registry (mirrors `openinference.py`); pinned by the span contract test. |
| `known_limitations.md` | **current** | Living debt register (L1–L11; L7/L8/L10 resolved). |
| `05_06_tool_adoption_roadmap.md` | **current** | Integrate bucket empty; Zenith/zap spikes; borrow/watch/reject. |
| `ADR-001-v1-architecture.md` | **superseded-by:`02_06_execution_ledger.md` + later ADRs** | Self-declared "historical baseline." pgvector-over-Qdrant decision recorded here. |
| `ADR-002 … ADR-008` | **current** | Each carries its own live status (spike / borrow / defer / reject). No churn. See the ADRs and `05_06` roadmap. |

### 5.2 Target lineage — `docs/design_docs/*` and the diagram

| Doc | Primary tag | Conflicts / notes |
|---|---|---|
| `CHIPS CORTEX ARCHITECTURE DIAGRAM.png` | **target-architecture** (canonical visual) | The locked end-state: four memory systems (Qdrant/Oxigraph/Cognee/Letta — **no AGE**), Signoff FSM, Promote→Tapeout. Postgres shown as **"Optional"** (inverse of today). |
| `chips-diagram-update-spec.md` | **target-architecture** (canonical — **vocabulary authority**) | Restates the locked architecture and contains the explicit **vocabulary lock** (§2 here derives from it). Authored as a diagram-generation prompt, but functions as the canonical target/vocab spec. |
| `chips-component-decision-register.md` | **target-architecture** (canonical — component/tool/decision index) | Companion to A0: A0 indexes docs, this indexes components, tools (with verdicts), and the locked taxonomy. Resolves Postgres/Qdrant; corrects Helix (firing surface, not harness); adds SpaceMate-as-first-project. |
| `chips-build-brief.md` | **target-architecture** (NOW PRESENT — reconstructed) | The parent the addenda referenced; was absent (see §6), now reconstructed post-A0 with the two-track build order and the Materials layer folded in. |
| `chips-yield-and-spof-addendum.md` | **target-architecture** | Canonical source for Yield/Fragility/Inspection-suite/SPOF. Uses correct "fault signature." Addendum to a `chips-build-brief.md` **not present in the repo** (see §6). |
| `chips-materials-layer-spec.md` | **target-architecture** (canonical — Materials layer) | The Assay/Refinery understanding plane: purity/decay/freshness, versioned-truth (Dolt) + projection (DeltaX/Timescale), delta-signature risk, the private-coefficient improvement track. Captures the temporal-risk subsystem that previously existed only in conversation. |
| `chips-reversible-compression-note.md` | **target-architecture** | Locks the projection-layer purity boundary for compression: lossy on the wire, lossless for audit/assay/gate/eval; pointer tokens are transport handles only; point-of-use dereference fails closed. |
| `chips-repowise-borrow-list.md` | **target-architecture** | **stale-vocabulary conflict:** uses "biomarker" / "25 biomarkers" → canonical is **fault signature** (`yield-and-spof` + diagram are later/authoritative). Borrow-list for the inspection suite. Also addendum to the absent `chips-build-brief.md`. |
| `chips-command-chip-spec.md` (v0.3) | **target-architecture** | **stale-vocabulary conflicts (two):** (a) lists **Apache AGE** as the chip-graph store (§0, §3) → **AGE is removed; Oxigraph is Truth** (diagram authoritative); (b) `trust_tier: safe/augmented/surgeon` → **Signoff Tier: Auto/Waiver/Manual**. Greenfield product; its §2.5 compression layer overlaps `05_06` tool roadmap. |
| `slots-contract-issue-response.md` | **target-architecture** (cross-system) | **Repo-boundary note:** describes the **SpaceMate chat backend** (NestJS/FastAPI/Prisma/GoRules), **not** the CHIPS Python sidecar. Included only for the shared *files-are-truth / generated-contract / gates-that-falsify* pattern. Build/plan it in the chat repo, not here. |

**Conflicts explicitly named (later doc wins):**
- **AGE vs Oxigraph:** `command-chip-spec` (June 15, AGE) ⟂ diagram + `diagram-update-spec` (June 17, Oxigraph; AGE removed). **Oxigraph authoritative.**
- **biomarker vs fault signature:** `repowise-borrow-list` (biomarker) ⟂ `yield-and-spof` + diagram (fault signature). **Fault signature authoritative.**
- **trust_tier/surgeon vs Signoff:** `command-chip-spec` ⟂ diagram. **Signoff authoritative** (same axis, renamed).
- **Tapeout scope:** diagram reserves Tapeout for **Promote → Truth only**; no doc currently misuses it for Execute — recorded here to keep it that way.

---

## 6. Missing parent & the Oxigraph migration (named, not scheduled)

**Missing parent brief.** `chips-repowise-borrow-list.md` and `chips-yield-and-spof-addendum.md`
both declare themselves addenda to **`chips-build-brief.md`**, which is **not present in this repo**.
Their "locked architecture" references (DRC arms, Signoff tiers, `g:*` graphs) therefore point at a
brief that exists only outside the repo (or only in the diagram). Until that brief is located or
reconstructed, the diagram + `chips-diagram-update-spec.md` are treated as the canonical statement
of the target they assume.

**Oxigraph migration — intended, with a trigger, not a date.** Moving the truth-store from
Postgres/pgvector to **Oxigraph + a gate subsystem** is an intended direction (it is the diagram's
end-state).

- **Why (the real reason):** the target needs **provenance-partitioned graph traversal** —
  confidence-tiered named graphs (`g:co-change`/`g:coupling`, `g:decision` with
  `supersedes`/`refines`/`conflicts_with` lineage) and fan-in/blast-radius traversal — that Postgres
  relational tables cannot express or traverse cleanly. The promotion model (Experience → Promote →
  Tapeout → Truth) and the Code-Hub SPOF (derived from graph fan-in) are graph-native operations.
- **Trigger condition:** revisit **after the first end-to-end vertical runs on the current Postgres
  stack** (a real fire path exercised end to end, even minimally). Not before — single-repo CHIPS
  must prove a vertical before taking on a truth-store migration + a gate subsystem (cf. the
  defer-federation discipline in `chips-repowise-borrow-list.md` §4.3).
- **A0 does not plan or start this migration.** It only records that it is intended, why, and when
  to reconsider it.

---

## 7. A0 as the first provenance node (dogfooding `g:decision`)

This document is the first hand-authored entry in the very decision-provenance model the target
architecture is meant to maintain automatically: `g:decision` nodes with
`supersedes` / `refines` / `conflicts_with` lineage and evidence-strength tags. The supersession
edges recorded in §5 (`28_05` → `31_05`; `ADR-001` → ledger; `CHIPS CORTEX.md` → V1 Spec/diagram)
and the conflict edges in §5.2 (AGE→Oxigraph, biomarker→fault-signature, trust_tier→Signoff) are
exactly the edges that subsystem would later track. We are dogfooding the model on the documentation
before building the machine that automates it. When `g:decision` is built, these edges are its seed.

---

## 8. What A0 deliberately does NOT do

- It does **not** rewrite, delete, or "fix" any other doc. Superseded docs stay as-is, tagged in §5.
- It does **not** produce an implementation plan or scope any build. The build/partial/aspirational
  breakdown in §4 exists to make the gaps visible *before* anything is scoped.
- It does **not** plan or start the Oxigraph migration (§6).
- It does **not** adjudicate the built lineage's internal, already-resolved churn (finding-ID scheme,
  governor/learning decoupling) beyond pointing at where it was resolved — that lineage is governed
  by `02_06_execution_ledger.md`.
