# Tool Adoption Roadmap

**Date:** 2026-06-05
**Status:** Accepted (decisions locked with Sachin, 2026-06-05 session)
**Companion docs:** `27_05_chips_generic_vs_stack_specific_roadmap.md` (libraries/adapters),
`docs/adr/ADR-001-v1-architecture.md` (v1 architecture), `02_06_execution_ledger.md`
(Foundation tranche authority)

## Purpose

A prioritized list of **external tools** evaluated for introduction into CHIPS, each backed
by an ADR (`docs/adr/ADR-002` … `ADR-008`) that records purpose, fit, scope, and the
proposed implementation approach (**integrate** / **build on** / **borrow** / **reject**).
This is the external-tool counterpart to the library/adapter roadmap in
`27_05_chips_generic_vs_stack_specific_roadmap.md`, and follows the same design rule:
everything stack-specific must normalize into the generic evidence model.

## Governing decisions (locked 2026-06-05)

1. **Foundation completes first.** No tool introduction lands before the Foundation
   tranche closes (slice 3 `repo_metrics_v` + cross-OS runner). Tool ADRs are written
   now; tool *work* is sequenced after.
2. **Retrieval lanes are and/or, not either/or.** CHIPS retrieval is multi-lane:
   - **Semantic lane** — embeddings + tree-sitter structural retrieval; works on any
     codebase (the generic-core promise).
   - **Contract lane** — exact-match retrieval keyed on the end-to-end semantic contract
     (`domain_action_entity_parameter`) where the codebase carries it (UI labels, chat
     prototypes, services, DBOS workflows, GoRules JDM files, Jinja templates, OTel
     spans/baggage, x-headers, gRPC/SSE/webhooks/MQTT, response codes).
   Lane selection depends on the instrumentation present in the target codebase. The
   contract lane is an *adapter-grade enhancement*, never a requirement — CHIPS must stay
   useful for codebases built differently.
3. **Design before implementation, for contracts.** Contract tokens are near-universal in
   HTTP today; adding them to MQTT/WebSockets/protobuf is straightforward *because the
   contract design is explicit*. Where a propagation hop is missing, the fix follows the
   design and can be added at any point. Tools that consume the contract (e.g. Zenith)
   are gated on the design being stated, not on every hop being instrumented.

## Prioritized adoption list

| # | Tool | Approach | Timing | Gate / prerequisite | ADR |
|---|------|----------|--------|---------------------|-----|
| 1 | Zenith (Polarityinc) | Integrate — as a *derived, warm-forward* contract-indexed trace cache (never system of record; SigNoz keeps that role) | Post-Foundation | Contract-lane thesis spike; OTel ingestion adapter (27_05 item 7); retention owned out-of-band | ADR-002 |
| 2 | zap (bitan-del) | Borrow / companion spike — operator-loop output compaction only | Anytime (off critical path) | Never in deterministic / raw-output-contractual paths | ADR-003 |
| 3 | smallcode (Doorman11991) | Borrow — symbol-aware chunking, budgeted-injection, trace-to-test patterns | Opportunistic, when touching the related slice | Read-before-build on retrieval/budget slices | ADR-004 |
| 4 | opensquilla | Borrow — hybrid lexical+vector recall with keyword fallback (feeds the multi-lane retriever design) | Opportunistic | Multi-lane retriever slice exists | ADR-005 |
| 5 | mirage (strukto-ai) | Watch — two-layer cache pattern; possible future heterogeneous-evidence ingestion | Revisit ≥ v1.0 | CHIPS needs cross-service evidence ingestion at all | ADR-006 |
| 6 | piia-engram | Reject as dependency; borrow the memory admission-gate pattern | If/when human-in-the-loop memory review is built | — | ADR-007 |
| 7 | HRM-Text (sapientinc) | Reject — wrong vehicle for the local-copilot ambition; re-vehicle via small pretrained code model + CHIPS-as-RAG | Ambition deferred, vehicle TBD | New ADR when the copilot ambition is picked up | ADR-008 |

## Sequencing after Foundation

1. **Contract-lane thesis spike** (not a tool — a measurement): point CHIPS retrieval at a
   contract-bearing repo, take real contract tokens, and measure whether token-match
   retrieval surfaces the cross-layer evidence set (rule + workflow + template +
   prototype) that the semantic lane misses. This spike gates Zenith's timing and shapes
   the multi-lane retriever design.
2. **Zenith** (ADR-002) once the spike validates the lane and the OTel ingestion adapter
   exists to feed it.
3. **zap spike** (ADR-003) can interleave anywhere — it touches the operator loop, not
   CHIPS code.
4. Borrow items (ADR-004/005) activate as their host slices are built; no standalone work.

## ADR index

- `ADR-001-v1-architecture.md` — v1 architecture decisions (2026-05-12)
- `ADR-002-zenith-contract-trace-cache.md` — Zenith as derived contract-indexed trace cache
- `ADR-003-zap-operator-output-compaction.md` — zap operator-loop spike
- `ADR-004-smallcode-retrieval-patterns.md` — smallcode pattern borrows
- `ADR-005-opensquilla-hybrid-recall.md` — opensquilla hybrid-recall borrow
- `ADR-006-mirage-evidence-vfs.md` — mirage watch
- `ADR-007-piia-engram-admission-gate.md` — piia-engram rejection + pattern borrow
- `ADR-008-hrm-text-local-copilot.md` — HRM-Text rejection + re-vehicled ambition
