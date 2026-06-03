# CHIPS span registry — OpenInference kinds + `chips.*` attributes (snapshot)

**Status:** Foundation / active. **Source of truth:** `src/chips/observability/openinference.py`
(this doc mirrors it; the span contract test pins both).

CHIPS adopts the [OpenInference](https://github.com/Arize-ai/openinference) semantic
conventions as a *thin attribute-naming standard* for its retriever / reranker /
embedding / tool / chain spans, and emits them **manually** (no auto-instrumentors —
CHIPS bars LLM generation in the hot path, so the auto-instrumentors for OpenAI /
LangChain / LlamaIndex buy nothing). CHIPS-domain concepts that OpenInference has no
vocabulary for ride the same spans under a namespaced `chips.*` custom-attribute space.

Treating the convention as a **snapshot** (not a hard dependency) means an upstream spec
change cannot silently churn CHIPS span attributes. Any rename/addition here is a
deliberate, reviewed change — enforced by the end-to-end span contract test.

## Span tree per brief (`BriefBuilder.build`)

```
CHAIN      "chips.compile.brief"   (root span — the brief build)
├─ EMBEDDING  "chips.embed.task"
├─ RETRIEVER  "chips.retrieve"
├─ RERANKER   "chips.rerank"
└─ TOOL       "chips.compress"
```

One span of each kind, emitted unconditionally so the tree shape is deterministic
regardless of the governor short-circuit branch. Span kind is carried on the standard
OpenInference key `openinference.span.kind` (values: `CHAIN`, `RETRIEVER`, `RERANKER`,
`EMBEDDING`, `TOOL` — `LLM`/`AGENT` are intentionally unused).

## `chips.*` attribute registry

| Key | Span | Meaning |
|---|---|---|
| `chips.task_kind` | CHAIN | classified task kind (e.g. `bugfix`) |
| `chips.scope` | CHAIN | brief scope (omitted when `None`) |
| `chips.tenant_id` | CHAIN | tenant (omitted when `None`) |
| `chips.brief_id` | CHAIN | generated brief UUID |
| `chips.latency_ms` | CHAIN | end-to-end build latency |
| `chips.governor.triggered` | CHAIN | governor short-circuit fired |
| `chips.embedding.dimensions` | EMBEDDING | task-embedding vector length |
| `chips.retriever.memory_count` | RETRIEVER | retrieved memories |
| `chips.retriever.diff_count` | RETRIEVER | retrieved diffs |
| `chips.retriever.file_signal_count` | RETRIEVER | retrieved file signals |
| `chips.retriever.structural_count` | RETRIEVER | structural items |
| `chips.reranker.input_count` | RERANKER | items into the reranker |
| `chips.reranker.output_count` | RERANKER | items after reranking |

`None`-valued attributes are omitted (never stamped as empty), so absence is meaningful.

## Configuration

Spans flow only when the OTel stack is installed (`_OTEL_AVAILABLE`) **and** a tracer
provider is active. Production wiring: `configure_telemetry("chips-cortex")` at the MCP
server entrypoint (`src/chips/mcp/bus.py`), gated on `CHIPS_ENABLE_OTEL` /
`OTEL_EXPORTER_OTLP*`. Tests inject an in-memory provider via the `_get_tracer` seam.
