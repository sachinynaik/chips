# ADR-009 Spike Result — CodeGraph Structural Graph Evaluation

**Run:** 2026-07-06/07 (setup→R7 in one day; box: Windows dev machine, local only).
**Pinned commit under test:** repo `99152212a99d8da363a280852ce44488a22f6328` (2026-07-06);
installed binary npm `@colbymchenry/codegraph` **1.2.0** (repo clone and npm build are
same-day; exact-SHA build not separately verified — open setup item).
**Fixtures:** chips @ `6d48f6b` (git clone, not cp -r — excludes untracked noise; logged
deviation), synthetic Python/Dart fixture (authored for spike, provenance in tree).
**All artifacts:** `C:\sachinynaik\adr-009-spike\` (scripts/, snapshots/, r1-out/).

## Result table

| # | Test | Threshold | Measured | Pass/Fail |
|---|---|---|---|---|
| R1 | Incremental = rebuild | 100% node+edge equality, ≥100 sessions | **96/100** (seed 20260706, reproducible) | **FAIL — TRIPWIRE** |
| R2 | Determinism | identical hash ×5 | first run 4/5 + 1 short rebuild; clean rerun **10/10 identical** | ⚠️ owner adjudicates (deviant = Signature A below) |
| R3 | Staleness window | p95 <5s; 100% pending reported | **p95 4.23s; 10/10 reported; 0 unreported-staleness** | **PASS** |
| R4 | Coverage vs Graphify | ≥90% node recall; ≥85% edge precision; Dart smoke | **recall 1.0000 (479/479)**; **edge precision 0.800 (24/30)**; Dart smoke PASS (27 nodes/46 edges, correct locations) | recall PASS · precision **FAIL** · smoke PASS |
| R5 | Blast-radius fit | reach ⊇ actual in ≥2/3 commits | **1/3** (2afcd58 YES 3/3; b24d98f NO 1/2; 513057f NO 1/4) | **FAIL** (evaluate-class) |
| R6 | Files-are-truth | fresh-clone reconstruction R2-identical | **byte-identical sha256** | PASS (single trial; probabilistically undermined by Signature A) |
| R7 | Integration sketch | ≤1 day estimated effort | `CodeGraphEnricher` prototype: ~90 LOC + 5/5 tests green, ~15 min actual; MCP exposure ≈ half-day via the hypotheses-module pattern (`src/chips/mcp/`) | **PASS** (est. ≤1 day; branch `spike/adr-009-r7-codegraph-enricher` @ 1cfc745, local-only) |

## The three defect signatures (full detail: snapshots/r1-tripwire-package.md)

- **A — silent partial index (the disqualifier-class finding).** From-scratch indexing
  sometimes silently drops content: 5 files (R2 run1), 1 file (R1 s13), and — worst —
  **~23% of nodes plus the ENTIRE call-edge class** (R5 c3 first init: 2,167 nodes/0 call
  edges vs 2,837/2,374 on retry). Always exit 0, always zero per-file error records,
  `codegraph status` reads healthy. Frequency ≈ 3 events / ~220 indexing runs (~1.4%).
  Because it is silent, a consumer cannot distinguish a gutted index from a healthy one
  without an external count-based sanity check.
- **B — ambiguous-name call-edge resolution.** 6/30 sampled call edges wrong (R4), all
  name-collision misresolutions (`subprocess.run`→`HarvesterDaemon::run`, Protocol stubs,
  same-named methods on other classes, src→test cross-links); R1 s70 shows the same
  resolution FLIPPING between incremental and rebuild paths (13 edges,
  `PostgresHarvesterStore::*` vs `HarvesterStore::*`); R1 s13 shows incremental never
  re-resolves edges out of unchanged files (staleness drift).
- **C — duplicate-edge multiplicity flap** (R1 s20/s22): cosmetic for set-consumers.

## What held up

Node extraction and containment structure were flawless in every measurement: R4 recall
100%, R6 byte-identical, R2 14/15 with the deviant explained by A, R3 zero unreported
staleness with honest pending reporting, Dart full support confirmed. The staleness
*reporting* contract (the silent-wrong-answer class the ADR feared for the watcher) is
clean — the silent-wrong-answer risk turned out to live in the INDEXER (Signature A), not
the watcher.

## R5 caveat (measure-class, not tool-specific)

Both R5 misses are commits that co-modified DEPENDENCIES or PARALLEL surfaces (extending
`HarvesterStore` to serve the change; applying the same refactor to `tests_ctx.py`) —
caller-direction blast radius cannot see those regardless of tool. Graphify's call edges
would share this limit. Co-change coupling (A11's lane) is the complementary signal.

## Open setup items

- npm 1.2.0 binary vs pinned repo SHA not bit-verified (same-day releases).
- R4 baseline method: option (a) as resolved, with one correction — the field is
  `source_file`, not `src` (the runbook's field name came from the query CLI's display
  format, not the JSON schema).
- R1 incremental path = manual `codegraph sync` (deterministic settle) rather than
  watcher-debounce polling; watcher measured separately in R3. Logged deviation.

## Agent recommendation (owner records the verdict, per A6)

**Reject for gate use; keep as advisory tooling; file Signature A upstream.**
Rationale: the gate lineage's foundational law is files-are-truth / reconstructable
derived caches. Signature A breaks exactly that guarantee, silently, at ~1.4% per index
build — and R1/R2/R6 all inherit it. The partition variant (nodes+contains only) that
looked live mid-spike is undermined by the same signature (the R5-c3 event dropped 23% of
NODES, not just call edges). Per demo-vs-gate row 15, advisory in-window use is already
sanctioned; nothing measured here justifies promoting any CodeGraph surface to
gate-eligible. Reconsider only after upstream fixes A (it is cleanly reproducible:
seeded harness + artifacts in this package) — at which point B alone would still cap call
edges at advisory, but a nodes+contains partition would become defensible.
