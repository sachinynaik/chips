# ADR-001: CHIPS CORTEX V1 Architecture Decisions

**Date:** 2026-05-12
**Status:** Accepted — **historical baseline** (marked 2026-06-05)
**Scope:** V1 — Spacemate internal dogfood → open source

> **Note (2026-06-05):** This ADR reflects the system as decided on 2026-05-12 and is
> kept as the historical baseline. Parts are stale: single-tenant language predates the
> later tenant work; observability assumptions have evolved (OpenInference span
> registry, Prometheus metrics, Grafana consumer); and the Foundation tranche decisions
> (decision log, policy_version, evidence architecture) live outside it. **Current
> active authority:** `docs/02_06_execution_ledger.md` and later ADRs
> (`ADR-002` onward).

---

## Context

CHIPS CORTEX originated as an ambitious architecture specification for an AI engineering cognition system. Before any implementation began, a full architectural critique was conducted against the original spec (`docs/CHIPS CORTEX.md`).

The critique identified a gap between the original framing:

> "ambitious AI architecture"

and the required framing for v1:

> "shippable engineering cognition infrastructure"

This ADR records every decision made, the alternatives that were rejected, and the reasoning behind each. It exists so that future contributors — and future versions of this team — understand why the system is built the way it is.

**Existing infrastructure at time of decision:**
- G2S2 retrieval layer (grep → graphify → semble → serena) — operational as Claude Code skill
- OpenTelemetry — instrumented across the spacemate stack
- SigNoz — trace/log exploration, self-hosted
- Postgres — primary canonical storage for spacemate

---

## Decisions

---

### Decision 1: Replace Letta with `cortex-harvester`

**Decided:** Replace the Letta Coordinator Agent with a lightweight Python daemon (`cortex-harvester`).

**Original proposal:** Use Letta (formerly MemGPT) as a persistent engineer coordinator agent that observes diffs, extracts memories, maintains a capability registry, and routes to specialist agents.

**Why Letta was rejected:**

Letta is a full agent framework with its own server, database, runtime, and memory management layer. For v1 of a solo-team tool embedded in spacemate, it adds:
- A new service to run and monitor
- Letta's own storage alongside Postgres (duplicates canonical storage)
- A complex programming model (Letta agents) for what is fundamentally a daemon loop
- Vendor alignment risk for open-source adoption — Letta has a cloud product, which creates friction for self-hosted OSS users

The core insight: **the persistent state Letta manages is already in Postgres.** Letta would be wrapping state that already exists. The coordinator behavior is: read git diff → extract lessons → write memory records. That is a daemon, not an agent framework.

**What `cortex-harvester` does instead:**

```
Observe:
  - git commits and diffs
  - failed tests
  - OTel traces (via SigNoz API)
  - Sentry exceptions
  - PR comments (optional, Phase 2+)

Extract:
  - candidate memory records (invariant, pitfall, lesson, decision, contract)
  - co-change clusters
  - unstable file signals
  - hot trace patterns

Store:
  - memory records → Postgres
  - embeddings → pgvector

Precompute:
  - retrieval signal rankings
  - co-change frequency
  - file churn scores
```

**Trigger model:**
- Spacemate internal: DBOS scheduled workflow, polling every 60 seconds. Retryable, durable, already visible in SigNoz.
- OSS default: git post-commit hook. Zero infrastructure dependency.
- Optional extensions (Phase 2+): file watcher (watchdog), GitHub webhook for PR events.

**When Letta might be reconsidered:**
Phase 5 or later, if multi-agent coordination at scale requires a persistent agent runtime. At that point, the harvester's memory records become the state that a Letta agent manages — the two are not mutually exclusive, just correctly sequenced.

---

### Decision 2: Replace Qdrant (for memory) with pgvector

**Decided:** Use pgvector on existing Postgres for all engineering memory vectors. Keep Qdrant only for the video analytics pipeline.

**Original proposal:** Use Qdrant as the vector store for all embeddings, including engineering memory records.

**Why Qdrant was rejected for engineering memory:**

Engineering memory (lessons, invariants, contracts, decisions, pitfalls) is a small dataset:
- Volume: 10K–500K records at most
- Write throughput: a few records per commit, low frequency
- Query pattern: semantic similarity search with simple metadata filters

pgvector on existing Postgres handles this trivially. Using Qdrant for this use case adds:
- Another Docker service to run, monitor, patch, back up
- Another thing to page at 2am
- Another credential to rotate
- Another dependency for OSS adopters to install and operate

**Where Qdrant stays:**

The video analytics edge pipeline (BM1684X → AI Gateway → NestJS) already uses Qdrant in production for:
- High-throughput clip embedding writes from the edge
- Payload filtering co-located with vector similarity (camera_id + timestamp + event_type)
- Per-tenant index isolation at scale

That use case justifies Qdrant. Engineering memory does not.

**The rule:** pgvector is the default for application-level vectors. Qdrant is justified when payload filtering + high write throughput + index isolation are all required simultaneously. Do not conflate the two use cases.

---

### Decision 3: Remove `decay_score` from V1 memory schema

**Decided:** Remove `decay_score` from the memory schema for v1.

**Original proposal:** Memory schema included a `decay_score` field for decaying relevance of old memories over time.

**Why removed:**

Memory decay requires a background scheduler to run periodically and update scores. This creates an invisible operational dependency — the system appears to work but silently degrades if the scheduler stops running.

At v1 memory volumes (likely hundreds to low thousands of records), decay adds tuning complexity with no meaningful benefit. Engineers don't yet have enough data to set decay parameters correctly.

**What replaces it:**

- `timestamp` is sufficient for recency-based ranking in v1
- retrieval ranking already incorporates recency as a weighted signal
- manual archival via `archived_at` field if records need to be suppressed

Decay can be reintroduced in a later version once memory volume justifies it and the ranking system has been validated.

---

### Decision 4: G2S2 must be extracted from Claude Code for open-source

**Decided:** G2S2 retrieval layer must be refactored into a standalone package and MCP server before open-source release.

**Current state:** G2S2 runs as a Claude Code skill (`~/.claude/skills/g2s2/SKILL.md`). It is tightly coupled to Claude Code's skill execution model.

**The problem:** If CHIPS CORTEX is open-sourced as a system that requires Claude Code to function, it is not truly open-source-portable. Any agent that speaks MCP should be able to use CHIPS.

**Target structure:**

```
g2s2-core/        standalone Python package
  retrieval/      grep layer
  graph/          graphify layer
  semantic/       semble layer
  symbolic/       serena layer

g2s2-mcp/         MCP server wrapping g2s2-core
  server.py
  tools/

cortex/           CHIPS CORTEX MCP server
  compiler/       context compiler
  memory/         memory bus
  governance/     policy layer
  harvester/      cortex-harvester
```

**Timeline:** Phase 5 (before open-source release). V1 can use G2S2 as a Claude Code skill for internal dogfood.

---

### Decision 5: Deterministic pruning first, LLM compression second

**Decided:** The context compiler compresses in two stages — deterministic pruning, then LLM-assisted synthesis.

**Rejected approach:** Use an LLM call as the primary compression mechanism.

**Why rejected:** LLM-first compression is expensive (token cost), slow (adds latency), and opaque (hard to debug). It also risks summarizing away constraints that must not be removed.

**The two-stage approach:**

Stage 1 — Deterministic pruning (< 500ms):
- Interface-only extraction via serena (signatures, not implementations)
- AST reduction (strip function bodies, keep headers)
- Diff slicing (lines changed, not full file)
- Top-k retrieval cutoff
- Symbolic reduction (symbol names, not full definitions)

Stage 2 — LLM-assisted synthesis (< 1.5s, Qwen2.5-Coder via Ollama):
- Synthesize the pruned set into a coherent brief
- Generate `recommended_actions`
- Only runs on `soft_context`, never on `hard_constraints`

**Compression drift prevention (logged for future):**

As the LLM compression layer matures, there is a risk that important constraints get summarized away. To prevent this, the brief output separates:

```yaml
hard_constraints:         # never compressed — injected verbatim
  - DBOS owns workflow state
  - dashboard is projection-only
soft_context:             # compressible
  - related traces
  - historical notes
  - similar implementations
```

This split is not enforced in v1 but the schema supports it from day one.

---

### Decision 6: Normalized ranking signals

**Decided:** Every ranking signal must be normalized to [0,1] before weighting. Per-signal contribution stored for explainability.

**The ranking formula:**

```python
score = (
    w_recency   * normalize_recency(timestamp_delta) +
    w_runtime   * trace_relevance_score +           # cosine [0,1]
    w_graph     * normalize_hops(topological_dist) +
    w_semantic  * embedding_similarity +             # cosine [0,1]
    w_failure   * normalize_failure(test_proximity) +
    w_cochange  * normalize_cochange(frequency)
)
```

**Normalization functions:**

| Signal | Raw form | Normalization |
|---|---|---|
| `recency` | timestamp delta (seconds) | exponential decay: `exp(-delta / half_life)` where half_life = 7 days |
| `topological_distance` | hop count (integer) | inverse sigmoid: `1 / (1 + hops)` |
| `cochange_frequency` | count | log-normalized: `log(1 + count) / log(1 + max_count)` |
| `test_proximity` | binary or distance | binary: `1.0` if in failing test, `0.0` otherwise (extend later) |
| `trace_relevance` | cosine similarity | already [0,1] |
| `embedding_similarity` | cosine similarity | already [0,1] |

**Initial weights (starting point, tune manually):**

```python
w_recency   = 0.25
w_runtime   = 0.25
w_failure   = 0.20
w_semantic  = 0.15
w_graph     = 0.10
w_cochange  = 0.05
```

**Important:** Weights are tuned manually based on observed brief quality. No automatic weight adjustment in v1. Feedback is captured (see Decision 8) but weight changes require a human decision.

---

### Decision 7: Multi-tenancy deferred, schema prepared

**Decided:** V1 is single-tenant. Schema includes `tenant_id UUID NULL` to enable future multi-tenancy without a breaking migration.

**Rationale:** Spacemate internal use is single-team. Designing full tenant isolation now would add complexity with no immediate return. Adding `tenant_id UUID NULL` costs one column and costs nothing operationally.

---

### Decision 8: Compiler observability from day one

**Decided:** Every generated brief gets a `brief_id`. Inputs, retrieved items, ranking scores, and post-task outcomes are persisted.

**Rationale:** The compiler is the product. Without observability, you cannot know if briefs are any good, why a brief changed, or which retrieval signals are actually predictive of task success.

**What is captured:**

```
On brief generation:
  - brief_id (UUID)
  - task description
  - scope
  - generated_at timestamp
  - latency_ms
  - every retrieved item (with score and signal_breakdown)
  - final compressed_context

After task completion:
  - agent-edited files (diff vs brief's retrieved files)
  - retrieval_overlap_score = |edited ∩ retrieved| / |edited|
  - test outcome (pass / fail / unknown)
  - post_task_outcome recorded against brief_id
```

**What is NOT automated:** Weight adjustment. Feedback is captured and queryable, but ranking weight tuning is done manually by a human reviewing brief quality reports. This remains manual until sufficient data exists to justify a tuning pipeline.

---

## Rejected Approaches — Summary

| Approach | Rejected Because |
|---|---|
| Letta as coordinator | Over-engineered for v1; adds operational complexity without value over a daemon |
| Qdrant for engineering memory | Unjustified for the volume and access pattern; pgvector on existing Postgres is sufficient |
| Memory decay scoring | Invisible operational dependency; not justified at v1 memory volumes |
| LLM-first compression | Expensive, slow, opaque; deterministic pruning must come first |
| Auto-adjusting ranking weights | Not enough data in v1; manual tuning until signal quality is understood |
| Qdrant for all vectors | Wrong abstraction — conflates video analytics (Qdrant-appropriate) with engineering memory (pgvector-appropriate) |
| Letta cloud product | OSS friction; self-hosted requirement is non-negotiable |

---

## Future Concerns (Logged — Not V1)

### Compression drift
As the LLM compression layer is used more heavily, there is risk that important constraints get summarized away. The `hard_constraints` / `soft_context` schema split is the mitigation. Enforce it in a later phase.

### Context diffing
"Why did Brief B differ from Brief A?" — needed for explainability when ranking changes, memories evolve, or engineers lose trust in the system. Requires storing brief snapshots and a diff mechanism. Phase 4+ concern.

### Letta reintroduction
If multi-agent coordination at scale becomes a real requirement, Letta may be the right abstraction then. At that point, the harvester's Postgres memory records are the state Letta manages. The two are not mutually exclusive — just correctly sequenced.

### Decay scoring
Reintroduce when memory volume exceeds ~50K records and ranking quality degrades due to old high-confidence memories dominating retrieval.
