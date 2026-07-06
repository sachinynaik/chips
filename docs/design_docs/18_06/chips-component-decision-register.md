# CHIPS — Component & Decision Register (v1.0, 2026-06-17)

> **What this is.** The canonical capture of (1) the **locked taxonomy** — the language seeded now,
> changeable in approach but fixed in vocabulary; (2) **every component** in the architecture, its
> purpose, status, and the decision behind it; (3) **every tool evaluated**, the evaluation reason,
> and the verdict. It is the companion to A0: **A0 indexes the docs; this indexes the components and
> decisions.** Both are hand-authored seeds of the `g:decision` provenance model the target is meant
> to maintain automatically.
>
> **Reconstruction note.** Built from the design conversation. Decisions and rationales are
> faithful; specific versions/counts marked *(verify)* should be confirmed against source before
> being treated as fact. Approach and components may change via `/simplify`; **the vocabulary is
> locked now** so the language stops drifting.

---

## 0. How to read this against the other docs

- `A0-architecture-reconciliation.md` — reading convention + built-vs-target doc index. **Read first.**
- `chips-build-brief.md` — the target build plan + build order.
- `chips-materials-layer-spec.md` — the Materials layer (Assay + Refinery), purity/decay/freshness,
  versioned-truth + projection, delta-signature risk, the improvement track.
- **This register** — the component dictionary + tool-decision log + taxonomy.
- Status tags throughout: **built** (runs today) · **partial** (real partial impl) · **aspirational**
  (target, no mechanism yet) — consistent with A0 §4.

> **Helix correction (was mis-tagged):** Helix is **not an agent harness** — it is a CLI-based rapid
> chip-firing surface (one summon-palette key → ranked fuzzy search → fire). It belongs with the
> firing surfaces, never with Claude Code / Codex / OpenCode (which run agent loops).

---

## 1. RESOLVED: Postgres vs Qdrant vs pgvector

**Decision:** pgvector **now**; Qdrant **in the target, migrated with Oxigraph**; Postgres **survives
demoted** to relational/ops.

| Phase | Vector store | Truth/graph | Relational/ops | Rationale |
|---|---|---|---|---|
| **Today (built)** | **pgvector** (HNSW on `cortex_memories.embedding`) | Postgres tables | Postgres | Co-location: vectors live transactionally with their source rows; one store; works. Don't rip out. |
| **Target** | **Qdrant** | **Oxigraph** | Postgres (Optional) | Once truth moves to Oxigraph, Postgres co-location benefit evaporates anyway — so Qdrant's wins become free. |

**Why Qdrant in the target (not pgvector forever):** quantization (scalar/binary/product) for
memory-efficiency on the on-prem GPU box; integrated payload filtering (filter by
`tenant_id`/`building_id` *then* vector search — the multi-tenant building-intelligence pattern);
faster filtered-ANN latency at scale; single Rust binary, local-first.

**Why the timing is coupled to Oxigraph (the key point):** pgvector's original advantage was
co-location with relational truth. The Oxigraph migration removes truth from Postgres, so
co-location disappears regardless — making that the correct, free moment to also move vectors to
Qdrant. Migrating vectors *before* Oxigraph would discard co-location for no gain.

**This is not "both forever."** It is a temporal migration (pgvector → Qdrant) under the Oxigraph
trigger, with Postgres surviving in a *narrower* role (relational/ops/audit: `decision_log`,
`repo_metrics_v`, workflow state). Target store set: Oxigraph + Qdrant + Cognee + Letta + optional
Postgres — each with a distinct job.

**Trigger:** the Qdrant migration rides the **Oxigraph migration trigger** (after the first
end-to-end vertical). Until then, pgvector. *(Open: confirm pgvector cannot meet target scale —
if it can, revisit at the simplify checkpoint, since "keep pgvector, drop Qdrant" is the fewer-
moving-parts fallback.)*

---

## 2. THE LOCKED TAXONOMY (language seeded — do not reinvent)

Organized by plane. Tags: **[gate]** = gate input · **[ext]** = external/demo only · **[built/partial/asp]**.
Frequency where relevant: **high** (per-fire) vs **low** (rare/irreversible).

### 2.1 Execution gate — "CHIPS Foundry" / the Signoff FSM  *(high frequency)*

| Term | Meaning | Status |
|---|---|---|
| **Fire / Dispatch** | one execution of a unit of work through the single fire path | asp |
| **Single fire path** | the one chokepoint all surfaces (CLI/MCP/harness) converge on | asp |
| **CHIPS Foundry** | the execution plane = the Signoff FSM | asp |
| **DRC (Design Rule Checks)** | pre-execution checks; two ternary arms | asp |
| **Policy Eval** | DRC arm: rule/constraint check; **clean / violation / unknown** | asp |
| **Blast Radius Read** | DRC arm: what the fire reaches + how fragile; **clean / violation / unknown** | asp |
| **UNKNOWN → ESCALATE** | uncheckable on either arm escalates (fail-safe, not fail-open) | asp |
| **Signoff Tier** | routes DRC outcome; stored floor + computed escalation | asp |
| **Auto Signoff** | low risk → Execute (high freq) | asp |
| **Waiver** | augmented → Execute, exception recorded | asp |
| **Manual Signoff** | high/unknown → Signoff Review | asp |
| **Signoff Review** | **resting state**; reached only by Manual Signoff | asp |
| **Approve / Reject / Edit & Refire / Abandon-Timeout** | Review transitions; Reject & Abandon terminal | asp |
| **Freshness re-check** | on Approve; if evidence changed materially → Re-escalate | asp |
| **Fabrication / Execute** | irreversible execution (high freq) | asp |
| **Audit + Feedback** | complete record; feeds Signal + Memory | partial (decision_log built) |
| **fire_id / immutability** | fire frozen at classification; refire mints new fire_id | asp |

### 2.2 Memory & promotion

| Term | Meaning | Status |
|---|---|---|
| **Oxigraph — Truth Memory** | facts, blast-radius graph, provenance, `g:*` named graphs | asp |
| **Cognee — Experience Memory** | tool-use episodes, success/failure, task outcomes | asp |
| **Qdrant — Similarity Memory** | embeddings/semantic retrieval (pgvector = today's stand-in) | asp (pgvector built) |
| **Letta — Coordination State** | orchestration, long-running tasks, checkpoints (Cortex Chronicle) | asp |
| **Promote** | the *only* sanctioned Experience → Truth path | asp |
| **Tapeout** | rare, irreversible final step of Promote into Truth. **Promote ONLY — never Execute.** (low freq) | asp |
| **`g:*` named graphs** | provenance-partitioned subgraphs: `g:coupling`, `g:decision`, … | asp |

**Ownership (locked):** Truth=Oxigraph · Experience=Cognee · Coordination=Letta · Similarity=Qdrant.
**Crossings (gated):** Cognee→Oxigraph only via Promote→Tapeout · Letta→Dispatch only as Caller
(no authority) · no Signoff bypass.
**Edge-confidence hierarchy:** enforced contracts > empirical/observed > structural/static >
associative (never gates a destructive fire).

### 2.3 Code intelligence — yield / fragility / inspection / SPOF

| Term | Meaning | Tag | Status |
|---|---|---|---|
| **Yield score** | defect-validated 1–10 health score | [ext] | asp |
| **Fault signature** | one deterministic defect-predictive signal | — | partial |
| **Inspection suite** | full set of fault signatures (structural · evolutionary · people) | — | partial |
| **Fragility** | defect-severity scalar weight on blast radius | [gate] | asp |
| **Blast radius** | the *area* a fire reaches (≠ Fragility, the danger of it) | [gate] | asp |
| **Coupling** | files that change together (edge → `g:coupling`) | [gate] | partial (stub) |
| **Entropy** | scatter score *on* a region's coupling/changes | [gate] | asp (not computed) |

**Fault signatures (the inspection suite contents):**

- *Structural [ext]:* **Complexity** (cyclomatic/McCabe) · **Nesting depth** · **Bloat** (too much
  in one unit — function + class) · **Cohesion** (LCOM-family; low = fault) · **Duplication**
  (clones) · **Vagueness** (primitive obsession — code imprecise about its meaning).
- *Evolutionary [gate]:* **Coupling** · **Entropy** · **Churn** (change frequency) · **Volatility**
  (code-age instability) · **Defect history** (temporal fix pattern) · **Defect density**
  (size-normalized) · **Hotspot** (churn × complexity) · **Untested risk** (coverage gaps on active
  code) · **Weak tests** (test-quality smells; execute-but-don't-catch).
- *People [gate]:* **Crowding** (authorship dispersion — too many hands over time) · **Contention**
  (concurrent competition for same region — bus-contention analogy) · **Single owner** (bus
  factor = 1) · **Orphaned code** (authors gone).

**SPOF register** (declared + derived; mitigated/partial/bare status; freshness-tracked):

| Category | What | Derivation |
|---|---|---|
| **Knowledge SPOF** | single owner, orphaned code | from people signals |
| **Code-Hub SPOF** | over-central unit, high **fan-in** (many dependents) | **derived** from blast-radius graph (self-refreshing spine) |
| **Infra SPOF** | single-instance service everything depends on (Keycloak, daemon, central Cognee) | declared + topology |
| **Data SPOF** | single source of truth, no fallback (Oxigraph graph, audit log) | declared |
| **Source SPOF** | single upstream producer whose fault propagates (the emitter) | declared |

### 2.4 Cortex Core modules (the capability surface, owned by Cortex Signoff)

Retrieve (what exists) · Signal (what matters / ranking) · Sage (assemble / context compiler) ·
Signoff (decide oversight = DRC + Signoff Tier) · Policy (what's allowed) · Trace (what happened) ·
Flow (what to do) · Memory (persistence) · Chronicle (persistence layer / Letta).

### 2.5 Locked principles (the reasoning vocabulary)

- **Files are truth; every index/graph is a derived, reconstructable cache.**
- **Placement:** convergence-tolerant content → CRDT/AFFiNE; correctness-gated → Git.
- **Naming:** a name matches the frequency and irreversibility of the thing it represents.
- **Inspection suite catalogs faults, not virtues** — never add the healthy pole for symmetry.
- **Two consumers:** internal (gate) vs external (demo); external metrics must be cheap projections.
- **Evolution beats structure** for defect prediction (so evolutionary signals are priority).
- **Capture-now:** the corpus/dataset is the unrecoverable thing; capture before the consumer exists.
- **Dogfooding removes the control group** — keep one ground-truth check independent of CHIPS' graph.
- **Purity law (Materials layer):** nothing is believed unless assayed; impurities allowed but always
  labeled (purity score + dopant element); no LLM-as-judge; a gap stays a gap.
- **Structural constraint beats policy:** make misuse impossible by construction (private coefficients,
  immutable versioned truth, files-are-truth) rather than discouraged by rules.
- **Proportion:** CHIPS ships better code faster by making AI-paired dev safe; the improvement/ceremony
  track is a small breather, not a pillar. Verification is the product.

---

## 2.6 SpaceMate as the first project (the dogfooding charter)

CHIPS is being built **for** SpaceMate but must be **extensible to other projects**. SpaceMate is the
guinea pig: CHIPS must become useful on it **with zero explanatory prompting from engineers** — start
from a code audit, build its own canonical understanding deterministically, find its own gaps,
interview for the rest (with receipts). This serves both SpaceMate (better code, faster) and CHIPS
(proves the product). It must answer **two success questions:**

1. **How much does CHIPS help SpaceMate ship better code faster?**
2. **How fast can CHIPS cold-start on a new codebase?** (the extensibility test)

The onboarding-by-interview *is* the product's first-run experience (see Materials layer §7): token-
efficient, symbolic/structured/contract-first, deterministic over LLM guessing.

---

## 3. COMPONENT REGISTER (purpose · status · decision)

### 3.0 Materials layer (NEW — understanding plane; full spec in materials-layer doc)
| Component | Purpose | Status | Decision/notes |
|---|---|---|---|
| **Materials layer** | build + maintain CHIPS' verified model of the codebase (the plane) | asp | sits *before* the Foundry: characterize/refine stock, then fabricate fires against it. |
| **Assay** | read-only characterize: purity (determinism % + dopant element) + freshness stamp | asp | certifies; never mutates; every Refinery output re-assayed. |
| **Refinery** | read-write purify: validate receipts, anneal (swap dopant), fill gaps via interview | asp | prioritized by `freshness-gap × decay × stakes ÷ projection-track-record`; never self-certifies. |
| Purity / Decay / Freshness | three orthogonal dimensions (composition / perishability / clock) | asp | never collapsed into one number. |
| Projection model | cheap parameterized model over versioned state; own purity; fitted coefficients | asp | per-user/team; hierarchically pooled; coefficients fitted from projection error, not hand-set. |
| Delta-signature | risk = Δ(purity/decay/freshness) + Fragility/blast-radius/SPOF per change (incl. design) | asp | requires the versioned baseline to diff against. |

### 3.1 Surfaces
| Component | Purpose | Status | Decision/notes |
|---|---|---|---|
| Helix / CLI | human **rapid chip-firing surface** (NOT a harness); summon-palette key + ranked fuzzy search | asp | firing surface + edit surface only; not hacked (Steel plugin watch-not-depend). |
| Web UI / Signoff Console | human review surface for Manual Signoff, promote queue, audit browsing | asp | Required for surgeon-tier review (rich blast-radius render, not a terminal y/n). |
| MCP / Agents | agents call `chips.search` / `chips.dispatch` over MCP | asp | Harness-agnostic by construction (one daemon serves Claude Code, Codex, …). |
| API / Integrations | programmatic entry | asp | — |
| Evidence & Telemetry Sources (READ-ONLY) | Code repos, CI/CD, IDE/LSP events, runtime logs, user actions, **Zenith** | mixed | Zenith is a read-source here, **not** a surface. |

### 3.2 Execution plane (CHIPS Foundry / Signoff FSM)
Entire plane **aspirational** (A0). The single fire path, DRC arms, Signoff Tier, Signoff Review,
Fabrication are the *control plane* — none built. Current code has constraint-injection that
**decorates briefs**, which is explicitly **not** a gate arm (A0 §4). Build via Track 2 of the
build brief (P0 decision table → P1 ontology → P2 validation slice).

### 3.3 Cognition & Memory
| Component | Purpose | Status | Decision |
|---|---|---|---|
| Oxigraph | Truth Memory; `g:*` named graphs; blast-radius traversal; SPARQL property paths | asp | **Chosen over Apache AGE** (AGE removed from CHIPS). RDF-native fit; named graphs = provenance tiering; property paths = transitive blast radius. |
| Cognee | Experience Memory; learned episodes | asp | Central instance (shared across engineers → governance + promotion gate). |
| Qdrant | Similarity Memory | asp | Target vector store; migrates with Oxigraph (§1). |
| Letta | Coordination State / Chronicle | asp | Caller of dispatch, never authority. **Simplify-checkpoint:** merge with Cognee if overlap persists. |
| pgvector | current vector store | built | Stays until Qdrant migration (§1). |

### 3.4 Code-intelligence layer
| Component | Purpose | Status | Decision |
|---|---|---|---|
| Harvester | git ingestion, co-change capture, file signals | **built** | The foothold; Track 1 builds on it. |
| Inspection suite (`enrichment/`) | fault signatures → Yield + Fragility | partial | ownership/clones/complexity/architecture/security real; **cochange ~19 LOC, defect ~5 LOC stubs** (the highest-value, thinnest). |
| Coupling / `g:coupling` | change-together edges | partial | `cortex_cochange_pairs` table exists; entropy not computed; no graph yet. |
| Fragility / Yield / SPOF register | severity weight / demo score / failure register | asp | Spec in yield-and-spof addendum. |

### 3.5 Promote pipeline
Experience (Cognee) → Promote (Validate) → Tapeout → Truth (Oxigraph). **Aspirational.** Candidate
optimizer for prompt-chip evolution: SkillOpt (§4), gated by existing conformance.

### 3.6 Infrastructure
| Component | Purpose | Status |
|---|---|---|
| Postgres | today: everything; target: optional relational/ops | built |
| MinIO / Local FS | objects, logs, traces, artifacts, snapshots | built/target |
| Ollama | local LLMs (summarize/tag/extract/compress) | target |
| OpenTelemetry / SigNoz / Prometheus / Sentry / Grafana | observability; `repo_metrics_v` is the single SQL metric authority; Grafana the standing surface | built (Foundation) |

---

## 4. TOOL EVALUATION REGISTER (what · why evaluated · decision)

Verdict legend: **adopt** (in the stack) · **borrow** (concept, build native) · **absorb** (fold into
existing) · **defer** (later/trigger-gated) · **reject** (overlap or wrong fit) · **watch** (spike-gated).

### 4.1 Agent harnesses
| Tool | What | Decision | Reason |
|---|---|---|---|
| Claude Code | primary agentic harness | **adopt** | primary; Opus superior for large complex tasks; parallel agents + worktrees as velocity multiplier. |
| Codex | alt harness | adopt (alt) | comparison surface; Opus preferred for big tasks. |
| ForgeCode | open Rust multi-provider harness; `:`-shell palette | **reject** (as harness) / borrow idea | wrong layer for chips; `:` palette inspired discoverable command palette; zsh-only → WSL caveat on Windows. |
| aidermacs | Emacs/Aider harness | reject | wrong category; transient-menu inspired command palette. |
| Pi (earendil-works) | self-extensible coding-agent harness | note only | **corrected**: it's a harness, not compression. Recorded role only: a **possible second CHIPS-brief consumer** after the first vertical proves the agent-agnostic claim. No ADR yet. |
| Helix | modal editor | **adopt** (surface) | edit/trigger surface; stable on Windows; Steel plugin = watch-not-depend. |

### 4.2 Context compression (the projection layer)
| Tool | What | Decision | Reason |
|---|---|---|---|
| Headroom | umbrella context-compression (tool output/logs/RAG/files); reversible CCR; KV-cache align; `headroom learn` | **borrow pattern / defer dependency** | Keep the **CCR / reversible dereference pattern** now; defer Headroom-as-library until a concrete brief-size failure proves current CHIPS compression insufficient. Proxy mode is wrong for CHIPS briefs. |
| RTK | mature CLI-output compressor, 100+ cmds, tee-on-failure | **evaluate in ADR-003 bake-off** | Companion-tool candidate for operator-loop compaction only. Evaluate separately for interactive shell output and CI/test logs; outcome may be RTK, zap, both by class, or neither. |
| lowfat | composable per-command CLI reducer + secret redaction | borrow/watch | hand-tunable per-command compaction + redaction pattern; no current adoption decision. |
| lean-ctx | CLI + MCP + editor-rules context tool | borrow-only footnote | Borrow only three ideas: quality-gated lossy compression, stub-and-expand, benchmark harness. No dependency, no standalone ADR. |

> Compression principle (locked): **compress for the agent, keep the original for audit.**
> See `chips-reversible-compression-note.md`: compression is a projection-layer optimization,
> never a truth-layer primitive; pointers are transport handles, not evidence identities.
> Status: aspirational/spike-gated; operator-loop companion tooling governed by ADR-003.

### 4.3 Code intelligence
| Tool | What | Decision | Reason |
|---|---|---|---|
| Graphify | AST/structure graph | **adopt** | current code structure (derived, ephemeral). |
| Serena | LSP/symbolic | adopt | symbolic search. |
| Semble | semantic search | adopt | semantic retrieval. |
| Glean (facebookincubator) | cross-language fact DB | adopt | cross-lang structural facts. |
| Semgrep | pattern/taint rules | adopt | string-coupling + security patterns; OSS intrafile (interfile is Pro). |
| repowise (concepts only) | codebase-intelligence MCP (AGPL) | **borrow (concepts), reject (tool)** | AGPL + heavy overlap; borrow co-change entropy, defect-calibrated severity, ADR-mining lineage, evolutionary>structural finding. Build native. |

### 4.4 Skill / chip evolution & safety
| Tool | What | Decision | Reason |
|---|---|---|---|
| SkillOpt (microsoft) | validation-gated skill optimizer; offline consolidate→gate→adopt | **borrow (scoped)** | mechanism for prompt-chip / domain-specialist evolution; gate against your own conformance stack (functional, not exact-match); held-out = shipped production scaffolding. Watch (v0.1). Scope: artifact-checkable outputs only; edge-promotion out of scope. |
| shadcn/improve (MIT) | agent-skill: capable model audits codebase → writes self-contained plans for cheaper models to execute; never implements itself | **borrow (concept), reject (tool)** | It's an **LLM-auditor** — would compete with and *dope* the deterministic-first Materials layer (it's the kind of harness-side tool CHIPS *certifies*, not contains). **Borrow:** the commit-stamped plan + mechanical drift-check pattern = CHIPS' freshness/decay mechanism applied to a work order (a plan is a belief stamped with the version it was true against, re-checked before execution). Convergence-validates fire-immutability + freshness-re-check. |
| NVIDIA/SkillSpector (Apache-2.0) | deterministic-first security scanner for agent skills/MCP tools: 64 patterns/16 categories (taint, AST, YARA, MCP poisoning, least-privilege) + live OSV.dev CVE lookup; static-first, LLM-refine second | **evaluate / watch (scoped)** | **Not** for securing SpaceMate's code (Semgrep + stack own that). Strong candidate for the *unfilled* job: **assay a command-chip/skill for safety BEFORE it enters the chip library** (admission-time gate, distinct from fire-time gate). Its static-first-then-LLM ordering matches the purity law; its MCP-poisoning/least-privilege checks match the chip-as-installable-MCP-unit attack surface. v0.1, very new — watch, don't depend; the *requirement* (chip-admission safety assay) is real. |

### 4.5 Trace / telemetry
| Tool | What | Decision | Reason |
|---|---|---|---|
| OTel + W3C baggage | tracing; `building_id`/`tenant_id` in baggage; UUIDv7 correlation | **adopt** | propagation source of truth. |
| SigNoz / Prometheus / Grafana / Sentry | observability surfaces | adopt (built) | Grafana standing surface; `repo_metrics_v` authority. |
| Tempo / Jaeger | prod trace store / dev tag-indexed search | adopt | Tempo prod, Jaeger dev. |
| Zenith | contract-indexed trace cache (FTS+vector over telemetry) | **watch** (spike) | promotion source; gap = no built-in retention/eviction; ADR-002 integration undecided. |
| Zap | token-efficient Claude/Codex hook output | evaluate in ADR-003 bake-off | Companion-tool candidate for operator-loop compaction only; compare against RTK by command class, with recoverability + exit-code fidelity as hard gates. |

### 4.6 Memory / knowledge & wiki surfaces
| Tool | Decision | Reason |
|---|---|---|
| Cognee | **adopt** | Experience Memory; fed via Claude Code plugin; central + governed. |
| Letta | adopt (caretaker) | Coordination State; simplify-checkpoint vs Cognee. |
| AFFiNE | **conditional** | good human team wiki / whiteboard; **parallel surface, not in the git-markdown pipeline**; CRDT for convergence-tolerant content only. |
| Outline | alt | governance-first alternative to AFFiNE (BSL, no whiteboard). |
| AppFlowy / Docmost / Anytype | reject (for this) | full workspace / weak team collab; not the pipeline. |
| SilverBullet / Reor / Foam / TriliumNext / Khoj | reject | notes/wiki landscape surveyed; wrong layer (knowledge, not executable). |
| The Curator / ContextSlice / FrameCode / link / matryca-plumber | borrow ideas | mined for: compile-conversation→page, multi-signal budget-packing, lifecycle states, provenance/confidence, single mutation plane. Most build on Karpathy "LLM Wiki"; chips' wedge is the *executable* layer none have. |

### 4.7 Stores
| Tool | Decision | Reason |
|---|---|---|
| Postgres | **adopt** | today everything; target optional relational/ops (§1). |
| pgvector | adopt (now) | current vector store; migrates to Qdrant with Oxigraph. |
| Qdrant | **adopt (target)** | target vectors; quantization + payload filtering + local-first (§1). |
| Oxigraph | **adopt (target)** | Truth Memory; chosen over AGE. |
| Apache AGE | **REJECT / REMOVED** | property-graph + traversal + blast radius now sit in Oxigraph; one store/one query language for traversal. (May survive elsewhere in SpaceMate.) |
| **Dolt** | **adopt (target) — role RESOLVED** | **versioned ground-truth state** for the Materials layer: immutable, branchable, diffable, point-in-time reconstructable score-field snapshots (the baseline for delta-signatures). NOT subsumed by DeltaX (which is read-only append-only). |
| **DeltaX** (xataio) | **evaluate / watch** | Postgres-native columnar OLAP (Apache-2.0); runs projection math + coefficient fitting over versioned state. Candidate for the analytical/OLAP slot; **Timescale = mature fallback** for the same slot. v0.1 (May 2026) — young; lock the *requirement*, keep the *tool* swappable. |
| Timescale | fallback | mature fallback for the OLAP/time-series slot if DeltaX isn't production-ready. |
| Meilisearch | **adopt** — role CONFIRMED (owner, 2026-07-06, A13) | ranked FTS; federated with grep + Helix(ripgrep) under Cortex Retrieve lexical. CHIPS keeps its claimed role; the running instance is machine-shared substrate (today serving the unified chat/search architecture) that CHIPS points at when the Retrieve lane is built. |
| ~~txtAI~~ | **REJECT / REMOVED (owner, 2026-07-06, A13)** | removed from the whole stack — superseded by the unified chat/search architecture (shared retrieval core: Meili/BM25 + Qdrant + Arroy/ColBERT + Postgres + Oxigraph/AGE + Dolt store plane; also serves video-analytics text embeddings). |
| MinIO / NATS JetStream (was Redpanda+RisingWave) | adopt (stack, target-only, gated) | objects / streaming. **Redpanda replaced by NATS JetStream (owner, 2026-07-06, A13)**; event-bus work is target vocabulary gated on real eventing need — nothing runs for CHIPS today. |

### 4.8 Validation / contracts (cross-cutting; some SpaceMate-chat-side)
| Tool | Decision | Reason |
|---|---|---|
| sqllineage | **adopt (concept)** | static SQL column lineage from migrations; Prisma path = migration-SQL + query-log + schema-map. |
| ~~Redpanda Schema Registry~~ + buf | adopt (buf); registry slot OPEN | event-schema compatibility; `buf breaking` = synchronous gate predicate (catches in-flight version skew). **Redpanda replaced by NATS JetStream (owner, 2026-07-06, A13); NATS has no Redpanda-style schema registry — the registry half of this row is an open row until the eventing design lands. buf gating stands on its own.** |
| Pact | adopt | consumer-driven contracts; reverse-radius (you breaking a consumer). |
| Stryker / mutmut | adopt | mutation testing — "is it *meaningfully* tested"; nightly clock. |
| Hypothesis / Schemathesis | adopt | property-based + schema fuzzing; manufacture executions over cold paths. |
| OpenLineage / DataHub | **keep (governance), don't depend** | data-governance lineage; CHIPS reads lineage as triples into Oxigraph instead of depending on DataHub. |
| GoRules (ZEN) | adopt | decision tables; runs in NestJS (chat side), not in the chat server. |

---

## 5. REVERSED / SUPERSEDED DECISIONS (the provenance)

The record that the design *moved* — kept, not erased (the `g:decision` `supersedes`/`conflicts_with`
seed, mirroring A0 §5/§7).

| Decision | From → To | Why |
|---|---|---|
| Truth-store graph engine | Apache AGE → **Oxigraph** | RDF-native triples; named-graph provenance; SPARQL property paths; one store/language for traversal. |
| Vector store (target) | pgvector → **Qdrant** (with Oxigraph) | co-location benefit evaporates once truth leaves Postgres; quantization + payload filtering + local-first. |
| The gate node name | Trust Tier → Triage → Clearance → **Signoff** | name the act (oversight classification), not the permission; semiconductor-native; symmetric across all 3 tiers. |
| Gate arms name | (Policy/Blast checks) → **Cortex DRC** | semiconductor-native; ternary clean/violation/unknown. |
| Tapeout scope | Execute **and** Promote → **Promote only** | frequency rule: Execute is high-freq, Tapeout is rare/irreversible; reserve the word for the rare commit. |
| Memory model | single memory → **four** (Truth/Experience/Similarity/Coordination) | distinct jobs; ownership + gated crossings. |
| Code-health term | "biomarker" → **fault signature** | semiconductor framing; de-biologized. |
| Code-health score | (health score) → **Yield score**; severity → **Fragility** | yield = native fab quality metric; fragility = scalar danger ≠ blast-radius area. |
| Overloaded/Oversized → | **Bloat** (function + class) | "overloaded" collides with a legitimate language feature. |
| Bus factor → | **Single owner** (+ Code-Hub SPOF) | plain; centralization fault moved to SPOF register as derived fan-in. |
| FSM framing | pipeline → **state machine** | resting states + terminal Reject/Abandon can't be a pipeline. |
| Letta vs Cognee | "either/or" → **both, gated** | distinct jobs (coordination vs experience); simplify-checkpoint if overlap persists. |

---

## 6. OPEN DECISIONS (carried)

1. **"What is a defect" labeling rule** — numerator for Defect history, Defect density, *and* Yield
   calibration; blocks Track 1 V1.2.
2. **Co-change support threshold + generated-code filter.**
3. **Yield calibration cadence + staleness threshold.**
4. **SPOF register ownership** — who maintains; cadence against rot.
5. **Demo-vs-gate metric boundary** — explicit list; no vanity metric leaks to the gate.
6. **Partial-population gate decision table** (build-brief Track 2 P0).
7. **pgvector scale check** — confirm pgvector can't meet target scale; if it can, "drop Qdrant" is
   the fewer-moving-parts fallback (revisit at simplify checkpoint).
8. **Stack-role verification** — confirm current roles of Dolt/Timescale/Meilisearch/txtAI/Redpanda
   against the built lineage (A0); some may be SpaceMate-wide, not CHIPS-specific.
9. **Chip-admission safety gate (NEW — surfaced by SkillSpector).** CHIPS gates chips at *fire*
   time, but never specified gating them at *admission* time — a malicious/vulnerable command-chip
   or skill entering the library is an unguarded attack surface (esp. MCP-exposed chips). Decide:
   is there a deterministic-first safety assay before a chip joins the library (SkillSpector-style
   static taint/AST/least-privilege/MCP-poisoning + optional LLM refine), and does it sit in the
   Materials layer (assay-before-admission) or as a distinct registration gate?

---

*Like A0 and the build brief, this register is a hand-authored node in the decision-provenance model
the target architecture is meant to maintain automatically. Vocabulary is locked; approach and
components remain subject to `/simplify`.*
