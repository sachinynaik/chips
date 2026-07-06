# ADR-009 — CodeGraph as Real-Time Structural Graph (Spike)

**Status:** SPIKE RUN 2026-07-06/07 — **VERDICT: REJECT for gate use; advisory use OK
(owner verdict, 2026-07-07, recorded as amendment A14).** Graphify remains the operating
tool; the proposed code/docs partition is NOT adopted. Results: R1 TRIPWIRE 96/100 · R2
14/15 · R3 PASS (p95 4.23s, 0 unreported staleness) · R4 recall 1.0000 PASS / edge
precision 0.800 FAIL / Dart smoke PASS · R5 1/3 · R6 byte-identical (single trial) · R7
PASS (≤1 day). Root cause of the reject: a **silent partial-index flake** (~1.4%/build;
worst case dropped 23% of nodes + the entire call-edge class, exit 0, clean status) that
breaks the files-are-truth reconstruction guarantee the gate lineage requires — plus
systematic ambiguous-name call-edge misresolution (path-dependent). Reconsider a
nodes+contains partition only after the upstream flake is fixed (reproducible: seeded
harness + artifacts in `docs/design_docs/05_07/adr-009-spike-result.md` and
`C:\sachinynaik\adr-009-spike\`). Advisory in-window use stays sanctioned by the
demo-vs-gate boundary row 15.
**Prior status:** APPROVED to run (owner verdict, 2026-07-05) with one adjustment: R4 relaxed to
90% node recall / 85% edge precision (drafted 95%/90%).
**Date:** 2026-07-05 (approved) · 2026-07-07 (verdict)
**Candidate (pinned):** `colbymchenry/codegraph` (MIT; tree-sitter → local SQLite + FTS5;
20+ languages incl. Python and Dart; native file-watcher, debounced auto-sync; per-file
staleness banners; connect-time hash reconciliation; MCP tools incl. `codegraph_impact`,
`codegraph_callers`, `codegraph_callees`, `codegraph_status`).
**Parent decision:** `docs/design_docs/05_07/chips-component-decision-amendments.md` §A1.

---

## Context

Graphify is the operating structural-graph tool (G2S2 lineage; `enrichment/graphify.py`;
`graphify-out/` cache) but requires a regenerate — the structural graph is stale between
regenerations. Blast Radius Read consumes this graph, and the locked guarantee "stale
evidence re-escalates" makes a standing staleness window a gate-quality problem, not an
ergonomic one. CodeGraph claims incremental real-time sync with *declared* staleness
(banner + status), which is purity-law-aligned: it labels the gap instead of answering
through it.

Proposed division of labor (owner, PROPOSED): **CodeGraph for code** (structural graph,
gate-relevant) · **Graphify for everything else** (docs, architecture artifacts). A
partition, not an added graph — the anti-goal holds iff roles stay disjoint and exactly
one graph feeds the gate for code.

## Decision

Run a time-boxed spike. The spike proves or kills exactly one premise: *CodeGraph's
incremental index is correct, deterministic, and fresh enough to be a gate input.*
Features, benchmarks, and agent-savings claims are out of scope.

## Spike success rubric (LOCK on approval — amendable only via recorded ADR amendment, never at spike start)

> **Verdict governance (owner decision, 2026-07-05):** "kill" anywhere in this rubric means
> **kill-recommendation**, not automatic kill. On a tripped criterion the spike stops,
> the data and recommendation go to the owner, and **only the owner records the verdict**
> (adopt-partition / reject / re-spike / continue-anyway). The agent provides data; the
> owner decides. This mirrors the locked gate guarantee — no self-approval by agents —
> applied to the evaluation process itself.

| # | Test | Threshold | On failure |
|---|---|---|---|
| R1 | **Incremental = rebuild.** ≥ 100 randomized edit sessions (create/modify/delete/rename bursts) on the chips repo + one SpaceMate-like Python/Dart fixture. After each debounce settle, canonical serialization of the incremental graph vs a from-scratch rebuild. | 100% node+edge set equality. | **kill** (an incremental graph that drifts from rebuild can never be a gate input) |
| R2 | **Determinism.** 5 from-scratch rebuilds of the same tree. | identical canonical hash, all 5 | **kill** |
| R3 | **Staleness window.** 10-file edit burst, measure watcher→synced. | p95 < 5 s; `codegraph_status` / banner correctly reports pending files in 100% of sampled windows | kill if unreported staleness observed (silent-wrong-answer class); tune if merely slow |
| R4 | **Coverage vs baseline.** Node recall (functions/classes) on chips repo vs Graphify. | ≥ 90% recall; 30-sample call-edge spot-check ≥ 85% precision (owner-adjusted at approval 2026-07-05; drafted 95%/90%); Python required, Dart smoke test passes | kill if Python recall materially below Graphify |
| R5 | **Blast-radius fit.** `codegraph_impact` reach sets for ≥ 3 real historical commits vs known co-change/actual regression touch-sets. | reach ⊇ actually-affected files in ≥ 2 of 3 | evaluate; not sole-kill |
| R6 | **Files-are-truth law.** Delete `.codegraph/`, re-index from clean clone. | full reconstruction, R2-identical | **kill** (every index is a derived, reconstructable cache) |
| R7 | **Integration sketch.** Enrichment-analyzer contract prototype (status: ok/not_installed/failed/timed_out/skipped) + MCP exposure sketch. | estimated ≤ 1 day integration effort | evaluate |

**Kill tripwires (stop + report to owner; never auto-kill):** R1, R2, or R6 failure;
unreported staleness in R3; Python coverage failure in R4. On any tripwire the spike
halts and the owner receives: the failing numbers, reproduction steps, and a
recommendation with rationale. **Time budget: 2 days.** Overrun = stop and report, not
extend — the overrun report is also an owner decision point, not an automatic abandon.

## Constraints during spike

- Local only; **no gate wiring, no G2S2 lineage change, no diagram change** during the
  spike. Graphify remains the operating tool throughout.
- Spike artifacts live under a scratch dir; nothing lands in `src/chips/` except the
  (optional) R7 prototype behind a branch.
- Verdict recorded here as an amendment: **adopt-partition / reject / re-spike**, with
  the R1–R7 numbers attached.

## On success

1. A1's partition flips PROPOSED → CONFIRMED; register + diagram + G2S2 lineage labels
   update (code slot: CodeGraph; docs/architecture slot: Graphify).
2. Partition boundary is written down as file-class globs (what is "code"), owned by this
   ADR's amendment.
3. `codegraph_status` output becomes the freshness probe for decision-table row B1
   (`chips-track2-p0-partial-population-decision-table.md` §3, §4.2).

## On failure

Graphify remains sole structural tool; the freshness gap it leaves is re-recorded as an
open problem (candidate mitigations: scheduled regenerate tightening, or a different
incremental indexer — new ADR either way).
