# Tool Adoption Roadmap

**Date:** 2026-06-05 (revised same day per Codex review)
**Status:** Approved as evaluation roadmap — decisions current, revisitable on spike evidence
**Companion docs:** `27_05_chips_generic_vs_stack_specific_roadmap.md` (libraries/adapters),
`docs/adr/ADR-001-v1-architecture.md` (historical baseline), `02_06_execution_ledger.md`
(Foundation tranche authority)

## Purpose

A bucketed, kill-criteria-bearing list of **external tools** evaluated for CHIPS, each
backed by an ADR (`docs/adr/ADR-002` … `ADR-008`). Nothing on this list is a commitment:
**no tool earns "Integrate" until a spike clears its success metric.** This is the
external-tool counterpart to the library/adapter roadmap in
`27_05_chips_generic_vs_stack_specific_roadmap.md` and follows the same design rule:
everything stack-specific must normalize into the generic evidence model.

## Governing decisions (Sachin, 2026-06-05 — revisitable by him, not by drift)

1. **Foundation completes first.** No tool work lands before the Foundation tranche
   closes (slice 3 `repo_metrics_v` + cross-OS runner). ADRs are written now; tool
   *work* is sequenced after. (Exception: companion-tool spikes that touch zero CHIPS
   code, e.g. zap.) **This is a governance/sequencing rule, not a technical-dependency
   claim** — Zenith's technical gates (contract-lane spike, OTel ingestion adapter,
   retention prototype) do not depend on slice 3 or the cross-OS runner; the ordering
   exists to keep the tranche focused.
2. **Retrieval lanes are and/or, not either/or.** Semantic lane (embeddings +
   tree-sitter) works on any codebase; a contract lane (exact
   `domain_action_entity_parameter` token match) applies only where the codebase carries
   the contract. Lane selection per target codebase; CHIPS must stay useful for
   codebases built differently.
3. **Design before implementation, for contracts.** Contract consumers gate on the
   contract *design* being explicit, not on every protocol hop being instrumented;
   missing hops (MQTT/WebSockets/protobuf) get tokens added when needed.

## Contract-lane status: HYPOTHESIS, not premise

The contract lane is a **stack-specific retrieval hypothesis**. It may work very well on
the SpaceMate-family stack and be absent or inconsistently propagated elsewhere. CHIPS
must prove it on target repos — the thesis spike below — **before any new infrastructure
is justified by it** (Zenith included). Building around it earlier risks overfitting
CHIPS to one semantic naming convention.

## The impossibility test (anti-tool-creep rule)

Before any Spike is promoted to Integrate, answer: **what problem becomes impossible —
or an order of magnitude worse — without this tool?** If existing infrastructure
(OTel + SigNoz + Postgres + DuckDB + Grafana) gets 80–90% of the value, the tool is not
integrated. If a borrow's value is achievable without new machinery, it stays a note.

## Buckets

### Integrate

*(empty — nothing has cleared a spike yet)*

### Spike

| Tool | Spike question | Success metric | Abandon condition | Time budget | Ops budget | ADR |
|------|----------------|----------------|-------------------|-------------|------------|-----|
| Zenith | Spike for possible integration: does contract-token trace search beat what we already have? | **Locked rubric in ADR-002** (pre-committed 10-query corpus; ≥7/10 impossible-or-≥10×-faster vs SigNoz+OTel/SQL; none worse; retention prototype works; coverage audit ≥80%) — amendable only by recorded ADR amendment, never at spike start | Per ADR-002 locked rubric: below pass; >2 days; >20 GB; coverage audit fails; or >50% of real investigation questions are raw-log-dependent; or contract-lane thesis spike fails first | 2 days | Ephemeral spike deployment on the shared WSL host, torn down after; **no always-on service before an integration decision** | ADR-002 |
| zap | Companion spike: measured operator-loop token savings without information loss | Measured savings on real CHIPS sessions (test logs, act/CI output) with zero observed loss of needed detail | **Hides needed error detail even once** on or near the exclusion list; or savings unmeasurable/marginal | 0.5 day | None (local CLI, opt-in, off product path) | ADR-003 |

Spike owner for both: Sachin + session agent (solo repo).

### Borrow patterns (no dependency, no standalone work)

| Tool | Borrow (narrowed) | Trigger — only when | ADR |
|------|--------------------|---------------------|-----|
| smallcode | Symbol-aware chunking; bounded-injection patterns; trace-to-test / operator-UX ideas | Touching `structural.py` or the rank/compress boundary | ADR-004 |
| opensquilla | Hybrid lexical/vector **fallback heuristics only** | Designing the multi-lane retriever slice, after the contract-lane spike passes | ADR-005 |

### Watch / Reject

| Tool | Position | ADR |
|------|----------|-----|
| mirage | Watch. Irrelevant until CHIPS has a concrete cross-service evidence requirement AND mirage reaches v1.0; cache pattern noted | ADR-006 |
| piia-engram | Reject dependency; borrow admission-gate pattern if human-in-the-loop memory review is ever built | ADR-007 |
| HRM-Text | Reject | ADR-008 |

## Operational cost (the column that matters for Integrate decisions)

| Tool | Runtime service? | New storage? | New failure mode? | Infra owner? | Rollback difficulty |
|------|------------------|--------------|--------------------|--------------|---------------------|
| Zenith | Yes — new Rust service | Yes — columnar segments | Yes — cache divergence, ingest lag, alpha format breaks | Sachin (shared WSL host) | Low *only if* derived-cache posture is kept (wipe + re-warm); high if it quietly becomes load-bearing |
| zap | No (CLI proxy) | SQLite stats (trivial) | Yes — filtered-away signal | n/a | Trivial (stop using it) |
| Borrows / Watch / Reject | No | No | No | n/a | n/a |

## Sequencing

1. **Foundation tranche closes** (slice 3 + cross-OS runner).
2. **Contract-lane thesis spike** (a measurement, not a tool): token-match retrieval on a
   contract-bearing repo vs the semantic lane — does it surface the cross-layer evidence
   set (rule + workflow + template + prototype) the semantic lane misses? Gates Zenith
   and the multi-lane retriever design. **If it fails, ADR-002 is abandoned, not
   reworked.**
3. **Zenith spike** (ADR-002) only if 2 passes and the OTel ingestion adapter (27_05
   item 7) exists to give trace evidence a path into briefs.
4. **zap spike** (ADR-003) may interleave anywhere — companion tooling, zero CHIPS code.
5. Borrows activate strictly on their stated triggers.

## ADR index

- `ADR-001-v1-architecture.md` — **historical baseline** (2026-05-12); current authority
  is the execution ledger + later ADRs
- `ADR-002-zenith-contract-trace-cache.md` — Zenith: spike approved, integration undecided
- `ADR-003-zap-operator-output-compaction.md` — zap: companion spike (not product path)
- `ADR-004-smallcode-retrieval-patterns.md` — smallcode: narrowed pattern borrows
- `ADR-005-opensquilla-hybrid-recall.md` — opensquilla: fallback-heuristics borrow only
- `ADR-006-mirage-evidence-vfs.md` — mirage: watch
- `ADR-007-piia-engram-admission-gate.md` — piia-engram: reject dependency + pattern note
- `ADR-008-hrm-text-local-copilot.md` — HRM-Text: reject
