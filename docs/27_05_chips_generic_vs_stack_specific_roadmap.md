# CHIPS Roadmap: Generic Core vs Stack-Specific Adapters

## Purpose
CHIPS should be useful in a plain codebase with Git, tests, and runtime access, but it should become materially better when richer signals exist. The right shape is:

- Generic core: retrieval, ranking, compression, feedback, health, and persistence that work for any repo.
- Optional adapters: OTel, DBOS, GoRules, `ts-morph`, Compodoc, or other stack-specific enrichers that map into the same evidence model.

## Recommended Next 5
These are the best next moves for this repository right now, balancing universal value with your richer internal stack.

1. `flashrank`
   Wire reranking between retrieval and compression. Highest likely brief-quality gain for the least architecture change.
2. OpenTelemetry ingestion adapter
   Move beyond source health into trace-derived brief evidence using spans, baggage, correlation IDs, and `x-action`.
3. DBOS workflow lineage adapter
   Convert workflow steps, retries, and workflow correlations into ranked engineering context instead of keeping them as a separate operational surface.
4. GoRules / JDM adapter
   Treat rule evaluations and decision steps as explicit retrieval evidence, especially where JDMs map directly to DBOS workflow steps.
5. `prometheus-client`
   Add real metrics for retrieval, compression, learning recomputes, source probes, and future governor decisions.

## `py-tree-sitter` urgency
`py-tree-sitter` is not a top-priority gap for this repo right now.

- Low urgency for your stack: you already have G2S2, `ts-morph`, Compodoc, OTel spans, DBOS workflow metadata, and correlation IDs.
- Medium value for portability: it could help CHIPS do local structural extraction in repos that do not have your stack or external retrieval infrastructure.
- Current repo status: `tree-sitter` and language packages are already in `pyproject.toml`, but no code usage was found in `src/` or `tests/`.

## Top 10 additions
Status reflects the repository state on 2026-05-27.

| Priority | Addition | Why it adds value | Applicability | Current status |
|---|---|---|---|---|
| 1 | `tiktoken` | Exact token budgeting for compression and prompt packing. | Universal | Implemented in `src/chips/compiler/compressor.py` |
| 2 | `flashrank` | Better reranking before compression, likely best quality-per-day upgrade. | Universal | Dependency added in `pyproject.toml`; no code wiring found |
| 3 | `prometheus-client` | Real counters/histograms for briefs, probes, retries, governor decisions, and learning recomputes. | Universal | Not present |
| 4 | `duckdb` | Fast offline analysis of briefs, outcomes, ranking changes, and observability exports. | Universal | Not present |
| 5 | `diskcache` | Persistent local cache for embeddings, reranks, structural metadata, and probe snapshots. | Universal | Not present |
| 6 | `tree-sitter` / `py-tree-sitter` structural adapter | CHIPS-native AST extraction for repos without `ts-morph` or G2S2-quality structure. | Portable, optional | Dependencies added; no adapter implementation found |
| 7 | OpenTelemetry ingestion adapter | Use spans, baggage, and correlation IDs as first-class ranking evidence instead of only generic runtime health. | High value for your stack; portable conceptually | Partial only: runtime probe via SigNoz/HTTP exists, but no trace-to-brief ingestion found |
| 8 | DBOS workflow lineage adapter | Convert workflow state, step lineage, and workflow correlations into retrieval evidence. | High value for your stack | Partial only: workflow probe/state tool exists, but no lineage enrichment found |
| 9 | GoRules / JDM adapter | Treat decision graphs and rule steps as explicit brief evidence linked to workflow execution. | High value for your stack | Not present |
| 10 | `ts-morph` / Compodoc ingestion adapter | Reuse existing TypeScript structural artifacts instead of re-parsing with a weaker generic layer. | High value for TS-heavy repos | Not present in this repo; available in your broader stack only |

## Recommended order
Build in this order if the goal is maximum value without overfitting CHIPS to one environment:

1. `flashrank`
2. `prometheus-client`
3. `duckdb`
4. OpenTelemetry ingestion adapter
5. DBOS workflow lineage adapter
6. GoRules / JDM adapter
7. `diskcache`
8. `ts-morph` / Compodoc ingestion adapter
9. `tree-sitter` structural adapter

`tiktoken` moves off the backlog because it is already in use.

## Design rule
All stack-specific enrichers should normalize into generic evidence types such as:

- `intent`
- `workflow_step`
- `decision_node`
- `trace_correlation`
- `runtime_failure`
- `service_dependency`
- `source_artifact`

That keeps CHIPS portable while still letting your environment produce better briefs than a generic repo can.
