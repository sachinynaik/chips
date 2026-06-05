# ADR-002: Zenith as a Derived, Contract-Indexed Trace Cache

**Date:** 2026-06-05 (revised same day per Codex review)
**Status:** Spike approved — integration undecided
**Tool:** https://github.com/Polarityinc/zenith (ZenithDB, Rust, Apache-2.0, alpha v0.0.1)

## Context

CHIPS's power thesis rests on the end-to-end semantic contract
(`domain_action_entity_parameter`) that Sachin's codebases carry through every stack
layer, including OTel spans and baggage. That makes production telemetry *joinable* with
code artifacts on the same key. What's missing is a fast way to *query* production
behavior by contract token ("find runs of `booking_cancel_*` where the governor
triggered and status was error") and feed the hits back as brief evidence.

Zenith is an alpha columnar DB purpose-built for agent traces: PAX segments sorted by
`trace_id`, bitmap indexes on low-cardinality fields (`model`, `tool_name`, `status`,
`span_type`), JSONPath indexing over attributes, embedded Tantivy FTS, HNSW vector
search, OTLP ingest endpoint, SQL/ZenithQL query.

## Verified characteristics (config/proto level, 2026-06-05)

Independent verification (Claude-chat deep-dive over Zenith's config and proto):

- **It is an agent-trace search index, not a generic telemetry store.** FTS fields are
  exactly `["prompt", "completion", "tool_io_text"]`; bitmaps on
  `model`/`tool_name`/`status`/`span_type`/`provider`; JSONPath index over attributes;
  HNSW vector search at 1536 dims. The cache role is the workload it was built for,
  not a stretch.
- **No retention/eviction for trace data — verified gap.** TTL exists only for
  JWT/JWKS and compaction leases; GC removes only superseded (compacted) segments.
  Nothing ages out actual trace data. Lifecycle must be owned out-of-band
  (time-window partitions dropped whole, or periodic re-provision) and is the likeliest
  operational bite.
- **Spans-only — verified.** The proto has `span.proto`/`SpanIngestRequest` and
  `query.proto`; there is no log record type. Logs are searchable only as span events;
  raw log-line search stays in the existing stack.
- **`trace_id` is the primary sort key**, so a cache hit carries the correlation ID
  straight back to the full trace in the system of record — a search front-end, not a
  parallel universe.

Initial assessment dismissed it ("proprietary schema, alpha, adds nothing over
OTel+Grafana"). That assessment evaluated the wrong role. The intended role is:

> Not the main data store for logs and traces — a **filtered & indexed text cache**.
> Ingest specific (filtered) traces, then search production telemetry for specific
> things. (Sachin, 2026-06-05)

## Decision

**Spike for possible integration — do not commit to integrate.** "Integrate" is too
strong a decision for an alpha service whose central premise — that contract-token trace
retrieval is a big enough problem that SigNoz + OTel/SQL filtering are insufficient —
is unproven. The spike exists to prove or kill exactly that premise.

If (and only if) the spike clears its success metric, integration follows the posture
below: SigNoz (per ADR-001) remains the trace system of record; Zenith holds only a
filtered, reconstructable subset; a format-breaking alpha upgrade means wipe + re-warm,
never data loss.

**Kill criteria** (also in the roadmap spike table): abandon if the query win over
SigNoz + OTel/SQL filtering is marginal relative to operating another service; abandon
unconditionally if the contract-lane thesis spike fails first. Time budget: 2 days.
No always-on service before an integration decision.

## Purpose & fit

- **Purpose:** queryable runtime half of the contract join. CHIPS indexes code artifacts
  by contract token (contract lane); Zenith indexes production behavior by the same
  token. Hits correlate back to code via the token and to `cortex_decision_log` via
  `brief_id` on the root span.
- **Fit (verified against its config/proto):** FTS fields are `prompt`/`completion`/
  `tool_io_text`; bitmap + JSONPath cover structured attributes. CHIPS spans carry
  structured `chips.*` attributes and contract tokens, not prompt text — so the
  workload leans on the bitmap/JSONPath/token side, which is exactly its design center.
- **Honest bar to clear:** ADR-001 already gives cortex-harvester trace access via the
  SigNoz API. Zenith earns its place only if contract-token queries over the filtered
  set are materially better than SigNoz API + filters. That is what the spike measures.

## Scope

- **In:** OTel Collector tee — full firehose to SigNoz, filtered subset (predicate:
  *span carries contract baggage*) to Zenith's OTLP endpoint; warm-forward retention
  (wipe = re-warm going forward, no backfill obligation); query surface for operator
  investigation and, later, trace-exemplar evidence in briefs.
- **Out:** system-of-record duties; log-line search (spans-only — verified above; logs
  stay in the existing stack); any write path from CHIPS core; backfill/replay
  machinery.
- **Decided upfront — warm-forward-only, never backfillable.** Backfill would require a
  replayable raw archive (bulk re-export from the primary store is awkward); for an
  investigation aid rather than an audit record, warm-forward is sufficient and much
  simpler. A wipe means the cache re-warms from new traffic only — accepted.
- **Where the engineering actually lives: the tee/filter layer, not Zenith.** The
  classic tail-sampling tension (too loose = a smaller Tempo at the same cost; too
  tight = the incident trace isn't cached) is structurally reduced here because the
  selection predicate is *property-based, not tail-based*: "span carries contract
  baggage" is decidable at ingest. Spans without contract tokens are simply out of this
  cache's scope by design.

## Approach

**Integrate** (run the service, ingest via OTLP), with the integration *shape* —
tee/filter predicate, retention, evidence mapping — designed in CHIPS. Per the locked
design rule, contract consumption is gated on the contract design being explicit, not on
every protocol hop being instrumented; missing hops (MQTT/WebSockets/protobuf) get tokens
added when needed.

## Timing & gates

1. Foundation tranche closes (slice 3 + cross-OS runner).
2. Contract-lane thesis spike validates token-keyed retrieval (roadmap §Sequencing) —
   the contract lane is a stack-specific retrieval *hypothesis*; this ADR's spike may
   not proceed, and no infrastructure may be justified by the contract lane, before
   that hypothesis is proven on target repos.
3. OTel ingestion adapter exists (27_05 roadmap item 7) so trace evidence has a path
   into the brief evidence model.
4. Retention/eviction design written (verified gap — see Verified characteristics;
   lifecycle owned out-of-band, e.g. time-window partitions dropped whole). **The spike
   must prototype the retention mechanism, not just the queries** — it is the likeliest
   operational failure point and must be proven before any integration decision.

## Consequences

- + Production-behavior search by contract token; evidence loop from runtime back into
  briefs and the decision log.
- + Alpha-format risk neutralized by derived-cache posture.
- − New Rust service to operate on the shared WSL Docker host (resource budget needed).
- − Single-vendor alpha; mitigated by warm-forward + OTLP-standard ingest (swap-out
  stays possible: same tee could feed ClickHouse instead if Zenith stalls).
