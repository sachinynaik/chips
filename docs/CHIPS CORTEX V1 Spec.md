# CHIPS CORTEX V1 — Executable Specification

**Version:** 1.0
**Date:** 2026-05-12
**Status:** Approved for Phase 1 implementation

This document is the executable architecture for CHIPS CORTEX V1. It contains schemas, interfaces, latency budgets, ranking logic, and the Phase 1 implementation plan.

For vision and philosophy: `docs/CHIPS CORTEX.md`
For decision history and rejected alternatives: `docs/adr/ADR-001-v1-architecture.md`

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  G2S2 Retrieval Layer  (already operational)                    │
│  grep → graphify → semble → serena                             │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│  Runtime Evidence Layer  (already operational)                  │
│  OTel · SigNoz · Prometheus · Sentry                           │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│  cortex-harvester  (Phase 1)                                    │
│  git watcher · memory extractor · trace summarizer             │
│  Trigger: DBOS workflow/60s (spacemate) · git hook (OSS)       │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│  Memory Bus  (Phase 1)                                          │
│  Postgres + pgvector · 5 memory types · HNSW index             │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│  cortex-sage  (Phase 3)                                         │
│  task classify · retrieval fusion · rank · prune · compress     │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│  Governance Layer  (Phase 4)                                    │
│  policy YAML · constraint injection · edit boundaries           │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│  MCP Interface                                                   │
│  /context/brief · /context/memory · /git/recent                 │
│  /workflow/state · /context/runtime                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. Memory Schema

### 1.1 Memory Records Table

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE cortex_memories (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NULL,                          -- deferred, nullable for v1
    type            TEXT NOT NULL                       -- see types below
                    CHECK (type IN ('invariant','decision','pitfall','contract','lesson')),
    scope           TEXT NOT NULL,                      -- e.g. 'valet.checkout', 'auth.keycloak'
    content         TEXT NOT NULL,
    tags            TEXT[]          DEFAULT '{}',
    evidence_refs   JSONB           DEFAULT '[]',       -- trace IDs, commit SHAs, test IDs
    confidence      FLOAT           DEFAULT 0.8         CHECK (confidence BETWEEN 0 AND 1),
    source          TEXT,                               -- 'git', 'trace', 'manual', 'test'
    author          TEXT,
    created_at      TIMESTAMPTZ     DEFAULT now(),
    updated_at      TIMESTAMPTZ     DEFAULT now(),
    archived_at     TIMESTAMPTZ     NULL,               -- soft delete / manual suppression
    embedding       vector(768)                         -- BGE-M3 output dim
);

CREATE INDEX cortex_memories_hnsw
    ON cortex_memories USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX cortex_memories_scope ON cortex_memories (scope);
CREATE INDEX cortex_memories_type  ON cortex_memories (type);
CREATE INDEX cortex_memories_tags  ON cortex_memories USING gin (tags);
```

### 1.2 Memory Types

| Type | Purpose | Example |
|---|---|---|
| `invariant` | Non-negotiable system rules | "DBOS owns all workflow state" |
| `decision` | Architectural choices and rationale | "Dashboard is projection-only" |
| `pitfall` | Failure patterns and bugs encountered | "Checkout skipped vehicle validation — 2025-11 incident" |
| `contract` | Capability boundaries and interface contracts | "valet.checkout requires active vehicle before orchestration" |
| `lesson` | Agent-learned implementation lessons | "MiniZinc solutions should be cached in Redis with 5min TTL" |

---

## 2. Git Ingestion Schema

```sql
CREATE TABLE cortex_git_commits (
    sha             TEXT PRIMARY KEY,
    author          TEXT,
    committed_at    TIMESTAMPTZ,
    message         TEXT,
    files_changed   TEXT[]          DEFAULT '{}',
    summary         TEXT,           -- LLM-generated summary (Phase 2)
    ingested_at     TIMESTAMPTZ     DEFAULT now()
);

CREATE TABLE cortex_cochange_pairs (
    file_a          TEXT NOT NULL,
    file_b          TEXT NOT NULL,
    frequency       INT  NOT NULL DEFAULT 1,
    last_seen_at    TIMESTAMPTZ    DEFAULT now(),
    PRIMARY KEY (file_a, file_b)
);

CREATE TABLE cortex_file_signals (
    file_path       TEXT PRIMARY KEY,
    churn_score     FLOAT DEFAULT 0,    -- normalized [0,1]
    failure_count   INT   DEFAULT 0,
    last_changed_at TIMESTAMPTZ,
    updated_at      TIMESTAMPTZ DEFAULT now()
);
```

---

## 3. Observability Schema

```sql
CREATE TABLE cortex_briefs (
    brief_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task                TEXT NOT NULL,
    scope               TEXT,
    generated_at        TIMESTAMPTZ DEFAULT now(),
    latency_ms          INT,
    mode                TEXT CHECK (mode IN ('interactive','background','autocomplete')),

    -- Compiler inputs (persisted for replayability)
    compiler_inputs     JSONB,              -- task, scope, retrieval query, mode

    -- Retrieved items with scores
    retrieved_memories  JSONB DEFAULT '[]', -- [{id, score, signal_breakdown}, ...]
    retrieved_files     JSONB DEFAULT '[]',
    retrieved_symbols   JSONB DEFAULT '[]',
    retrieved_traces    JSONB DEFAULT '[]',
    retrieved_tests     JSONB DEFAULT '[]',
    retrieved_diffs     JSONB DEFAULT '[]',

    -- Output
    compressed_context  TEXT,
    hard_constraints    JSONB DEFAULT '[]', -- never compressed
    soft_context        TEXT,               -- compressible portion

    -- Post-task observability (populated after agent completes)
    agent_edited_files      TEXT[]  DEFAULT '{}',
    retrieval_overlap_score FLOAT,          -- |edited ∩ retrieved| / |edited|
    test_outcome            TEXT    CHECK (test_outcome IN ('pass','fail','unknown','skipped')),
    post_task_outcome       TEXT,           -- free text, manually recorded or inferred
    outcome_recorded_at     TIMESTAMPTZ
);
```

**Replay:** Given a `brief_id`, `compiler_inputs` contains everything needed to reproduce the retrieval and compilation run. Replay function re-runs all stages and compares output.

---

## 4. Context Compiler Interface

### 4.1 Primary Interface

```python
def compile_context(
    task: str,
    scope: str | None = None,
    max_tokens: int = 2000,
    mode: Literal["interactive", "background", "autocomplete"] = "interactive",
) -> ContextBrief:
    ...
```

### 4.2 ContextBrief Schema

```yaml
brief_id: uuid
task: str
scope: str | null
generated_at: ISO8601
latency_ms: int
goal: str
constraints:
  hard_constraints:     # injected verbatim, never compressed
    - str
  allowed_edits:
    - str
  forbidden_edits:
    - str
retrieved:
  memories:
    - id: uuid
      type: str
      content: str
      score: float
      signal_breakdown:
        recency: float
        semantic: float
        graph: float
        failure: float
        cochange: float
  files:
    - path: str
      score: float
      signal_breakdown: {...}
  symbols:
    - name: str
      file: str
      score: float
  traces:
    - trace_id: str
      summary: str
      score: float
  tests:
    - test_id: str
      status: str
      score: float
  diffs:
    - file: str
      summary: str
      score: float
compressed_context: str   # soft_context compressed
recommended_actions:
  - str
observability:
  retrieval_overlap_score: float | null   # populated post-task
  post_task_outcome: str | null           # populated post-task
```

### 4.3 Latency Budgets

| Mode | Budget | Notes |
|---|---|---|
| `autocomplete` | < 500ms | Memory + git signals only. No LLM compression. |
| `interactive` | < 2s | Full pipeline. Most common use case. |
| `background` | < 10s | Deep compile. Pre-computed for complex tasks. |
| Harvester extraction | async | No latency constraint. |

---

## 5. Ranking System

### 5.1 Normalized Signals

Every signal is normalized to [0,1] before weighting:

| Signal | Raw form | Normalization function |
|---|---|---|
| `recency` | seconds since last modified | `exp(-delta / 604800)` (7-day half-life) |
| `semantic` | cosine similarity | already [0,1] |
| `trace_relevance` | cosine similarity | already [0,1] |
| `topological_distance` | hop count | `1 / (1 + hops)` |
| `cochange_frequency` | count | `log(1 + count) / log(1 + max_observed)` |
| `failure_proximity` | binary (in failing test path) | `1.0` if yes, `0.0` if no |

### 5.2 Weighted Score Formula

```python
score = (
    0.25 * recency_score +
    0.25 * trace_relevance_score +
    0.20 * failure_proximity_score +
    0.15 * semantic_score +
    0.10 * topological_score +
    0.05 * cochange_score
)
```

**Starting weights.** Tune manually. No automatic adjustment in v1.

### 5.3 Per-Signal Contribution Storage

Every retrieved item stores `signal_breakdown` (each signal's individual contribution before weighting). This enables:
- Debugging "why was X retrieved?"
- Detecting which signals dominate in practice
- Informing future weight adjustments

---

## 6. Compression Pipeline

### Stage 1 — Deterministic Pruning (target: < 300ms)

Applied to all retrieved items before LLM:

1. **Interface extraction** — serena: signatures only, no function bodies
2. **Diff slicing** — changed lines only, ±3 lines context
3. **Top-k cutoff** — hard cap per category (memories: 5, files: 5, symbols: 10, traces: 3, tests: 5, diffs: 5)
4. **Deduplication** — remove items with cosine similarity > 0.95 to a higher-ranked item
5. **Hard constraint extraction** — pull `invariant` and `contract` memory types out as `hard_constraints`

### Stage 2 — LLM Synthesis (target: < 1.5s, autocomplete mode: skip)

- Model: Qwen2.5-Coder via Ollama (local)
- Input: pruned set from Stage 1 (estimated 5-15K tokens)
- Output: `compressed_context` string (target 800-1500 tokens) + `recommended_actions`
- Constraint: `hard_constraints` are injected verbatim into the final brief, never passed through LLM compression

---

## 7. cortex-harvester

### 7.1 Responsibilities

```
Observe:
  - new git commits (every 60s poll)
  - test failure events (from CI/test runner output)
  - OTel trace anomalies (query SigNoz API)
  - Sentry exceptions (optional, Phase 2)

Extract:
  - candidate memory records from commit messages and diffs
  - co-change pairs from files modified in same commit
  - file churn scores from commit frequency
  - failing test to file associations

Embed:
  - generate BGE-M3 embedding for each memory record content
  - store in cortex_memories.embedding

Store:
  - commit metadata → cortex_git_commits
  - co-change pairs → cortex_cochange_pairs (upsert, increment frequency)
  - file signals → cortex_file_signals
  - memory records → cortex_memories
```

### 7.2 Trigger Model

**Spacemate internal:**
```python
# DBOS scheduled workflow — retryable, visible in SigNoz
@dbos.scheduled_workflow(cron="*/1 * * * *")  # every 60 seconds
async def cortex_harvest_workflow():
    last_harvested = await get_last_harvest_timestamp()
    new_commits = await git_log_since(last_harvested)
    for commit in new_commits:
        await extract_and_store(commit)
    await update_harvest_timestamp()
```

**OSS default:**
```bash
# .git/hooks/post-commit
#!/bin/sh
cortex-harvester harvest --commit HEAD
```

**Optional extensions (Phase 2+):**
- File watcher (watchdog) for real-time local signals
- GitHub webhook for PR comment extraction

---

## 8. MCP Interface

### 8.1 Endpoints — Phase 1

| Endpoint | Description | Mode |
|---|---|---|
| `GET /context/memory` | Semantic search over memory records | query param: `q`, `scope`, `type`, `limit` |
| `GET /git/recent` | Recent commits, changed files, co-change pairs | query param: `since`, `limit` |

### 8.2 Endpoints — Phase 3

| Endpoint | Description |
|---|---|
| `POST /context/brief` | Full compiler pipeline. Body: `{task, scope, max_tokens, mode}` |
| `GET /context/runtime` | Live traces and anomalies from SigNoz |
| `GET /workflow/state` | DBOS workflow state for given scope |

### 8.3 Endpoints — Phase 4

| Endpoint | Description |
|---|---|
| `GET /context/invariants` | All invariant and contract memories for a scope |
| `GET /context/policy` | Governance policy for a scope (forbidden/required ops) |

---

## 9. Governance Layer (Phase 4)

### Policy Format

```yaml
# policies/valet.yaml
scope: valet.checkout
forbidden:
  - direct projection edits
  - manual dashboard persistence
  - workflow state bypass
required:
  - workflow state via DBOS
  - projections derived from events
  - active vehicle check before checkout
```

Policies are loaded from YAML files and injected into `hard_constraints` of every brief for the matching scope.

---

## 10. Implementation Phases

### Phase 1 — Memory Foundation (target: 1-2 weeks)

Deliverables:
1. `CREATE EXTENSION vector` on spacemate Postgres
2. `cortex_memories` table + HNSW index
3. `cortex_git_commits`, `cortex_cochange_pairs`, `cortex_file_signals` tables
4. `cortex_briefs` observability table (populated from Phase 3, schema created now)
5. `cortex-harvester` DBOS scheduled workflow (git ingestion only, no LLM in Phase 1)
6. MCP endpoint: `GET /context/memory` (semantic search)
7. MCP endpoint: `GET /git/recent`

Validation:
- Harvester runs every 60s, commits appearing in `cortex_git_commits` within 90s
- `/context/memory?q=checkout+vehicle` returns relevant memory records
- `/git/recent` returns last N commits with co-change pairs

### Phase 2 — Memory Enrichment (target: 1 week)

Deliverables:
1. Ollama integration (BGE-M3 for embeddings, Qwen2.5-Coder for summarization)
2. Automated memory extraction from commit messages (LLM-assisted tagging)
3. Trace anomaly ingestion from SigNoz API
4. Embedding generation for all memory records

### Phase 3 — Context Compiler MVP (target: 2-3 weeks)

Deliverables:
1. Task classifier (rule-based: keyword → scope mapping)
2. Retrieval fusion (G2S2 + memory search + git diff + traces)
3. Normalized ranking engine (all 6 signals)
4. Compression pipeline (deterministic pruning + Qwen2.5-Coder)
5. MCP endpoint: `POST /context/brief`
6. Brief observability populated on every compile

### Phase 4 — Governance (target: 1 week)

Deliverables:
1. Policy YAML loader
2. Scope → policy mapping
3. Hard constraint injection into briefs
4. MCP endpoints: `/context/invariants`, `/context/policy`

### Phase 5 — Open Source Packaging (target: 2 weeks)

Deliverables:
1. G2S2 extracted as standalone Python package (`g2s2-core`)
2. G2S2 MCP server (`g2s2-mcp`)
3. CHIPS CORTEX Docker Compose stack (Postgres + pgvector + Ollama + chips-cortex + chips-harvester)
4. Multi-tenant `tenant_id` enforcement
5. OSS documentation and installation guide

---

## 11. Open-Source Docker Compose Target

```yaml
# docker-compose.yml (OSS distribution)
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: chips_cortex
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_models:/root/.ollama

  chips-cortex:
    build: ./cortex
    depends_on: [postgres, ollama]
    environment:
      DATABASE_URL: postgresql://...
      OLLAMA_URL: http://ollama:11434

  chips-harvester:
    build: ./harvester
    depends_on: [postgres]
    volumes:
      - ${REPO_PATH}:/repo:ro    # mount the target repo read-only

volumes:
  postgres_data:
  ollama_models:
```

Install:
```bash
git clone https://github.com/your-org/chips-cortex
cd chips-cortex
cp .env.example .env  # set REPO_PATH and POSTGRES_PASSWORD
docker compose up -d
```
