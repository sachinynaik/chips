# ADR-009 Spike Runbook — CodeGraph Structural Graph Evaluation

Execution runbook for the 2-day spike approved in `ADR-009-codegraph-structural-graph-spike.md`
(rubric R1–R7, tripwires, constraints — read that file first; this doc does not restate it).
R4 uses the **owner-adjusted** thresholds: 90% node recall / 85% edge precision.

---

## 0. Setup

**Candidate (pinned):** `colbymchenry/codegraph` (MIT). Tree-sitter extraction → local
SQLite + FTS5; native file-watcher with debounced auto-sync; MCP tools `codegraph_impact`,
`codegraph_callers`, `codegraph_callees`, `codegraph_status`.

### Steps (best-documentable without executing)

1. Create scratch workspace, isolated from `src/chips/`:
   ```
   mkdir -p <scratch>/adr-009-spike
   cd <scratch>/adr-009-spike
   git clone https://github.com/colbymchenry/codegraph.git
   cd codegraph
   git log -1 --format='%H %cI'   # record pinned commit SHA + date in the result table notes
   ```
2. Install per the repo's own instructions (language runtime, build step, MCP server
   registration) — **do not assume npm/uv/cargo here**; the actual toolchain must be read
   off the repo's README at spike start.
3. Register the MCP server against a **copy** of the chips repo tree (not the working tree
   used for real development) so file-watcher activity during R1/R3 never touches live
   work:
   ```
   cp -r C:\sachinynaik\chips <scratch>/adr-009-spike/chips-fixture
   ```
4. Obtain or construct the "one SpaceMate-like Python/Dart fixture" required by R1 — a
   small tree mixing `.py` and `.dart` files. If no existing fixture is designated, build a
   minimal synthetic one (a handful of classes/functions with cross-file calls in each
   language) and record its provenance in the result notes.

### Verify-before-trusting note (mandatory, read before any measurement)

The capability list above (tree-sitter, SQLite+FTS5, debounce default, MCP tool names) is
carried from the ADR's PINNED description, not independently re-verified by this runbook.
**Before running any R1–R7 procedure**, reconcile every claim against the cloned repo's
actual README / docs at the pinned commit:
- Confirm the MCP tool names and their argument/response shapes.
- Confirm the debounce default and whether it is tunable (affects R3 sampling window).
- Confirm the on-disk index location and format (needed for R6 "delete and re-index").
- Confirm the canonical output the tool offers for node/edge listing (needed for R1/R2/R6
  serialization — see §1 below).

If any of the above contradicts what this runbook assumes, stop and log it as an open
setup item in the result template (§3) rather than silently adapting the procedure.

### Constraints in force throughout (per ADR)

- Local only. No gate wiring, no G2S2 lineage change, no diagram edits during the spike.
- Graphify remains the operating tool throughout — do not point any live enrichment/gate
  path at CodeGraph.
- All spike artifacts (clones, indexes, logs, comparison dumps) live under the scratch dir.
- Nothing lands in `src/chips/` except the optional R7 prototype, and only behind a branch.

---

## 1. Canonical serialization / comparison method (R1, R2, R6)

All three criteria reduce to "does graph A equal graph B" for CodeGraph's own output across
different runs/states (incremental vs rebuild, run 1..5, pre-delete vs post-reindex). Same
method for all three:

1. Dump the graph via whatever CodeGraph exposes as a full listing. Preferred, in order of
   preference (confirm which exists per the verify-before-trusting note):
   - a dedicated export/dump command, if the CLI/MCP surface has one; else
   - `codegraph_status` plus enumerating all nodes via `codegraph_callers`/`codegraph_callees`
     over every known symbol; else
   - direct read of the underlying SQLite file's nodes/edges tables (acceptable since R6
     already treats the index as files-are-truth — reading the DB directly does not violate
     that law, it just requires knowing the schema, which must be confirmed at spike start).
2. Normalize before hashing/diffing:
   - Node key = `(file_path relative to repo root, symbol qualified name, node kind)`.
     Absolute paths, timestamps, row IDs, and internal integer PKs are excluded.
   - Edge key = `(source node key, target node key, edge kind)`.
   - Sort node list and edge list lexicographically by their keys; no other ordering is
     significant.
3. Serialize the normalized (sorted node list, sorted edge list) as newline-delimited JSON
   or CSV — one canonical file per snapshot, written under
   `<scratch>/adr-009-spike/snapshots/<label>.txt`.
4. **Equality (R1, R6):** `diff` the two canonical files; zero diff lines = pass. On
   non-zero diff, capture the diff itself (it is the tripwire repro artifact).
5. **Identical hash (R2):** `sha256sum` the canonical file per rebuild; all 5 hashes must
   match.

**Rebuild baseline for R1/R6:** "from-scratch rebuild" = delete the CodeGraph index dir
found in step 3 of the verify-before-trusting note, then re-run its indexing command over
the same tree state, then dump per steps 1–3 above.

---

## 2. Per-criterion procedure

### R1 — Incremental = rebuild
- Sample size: ≥ 100 randomized edit sessions, each a burst of create/modify/delete/rename
  ops, across (a) the chips repo copy and (b) the Python/Dart fixture from §0.4.
- Script a randomized edit generator (seeded, so sessions are reproducible) or hand-author
  ≥ 100 sessions if scripting is out of scope for the spike's time budget — record which.
- Per session: apply the burst → wait for debounce settle (poll `codegraph_status` until it
  reports no pending files) → dump canonical incremental graph (§1) → separately rebuild
  from scratch on the same post-burst tree state → dump canonical rebuild graph → diff.
- Record: sessions run, sessions with zero diff, first failing session's diff (if any).
- Threshold: 100% of sessions node+edge-set equal. Any failure → **tripwire, stop** (§4).

### R2 — Determinism
- 5 from-scratch rebuilds of the same fixed tree state (chips repo copy at a pinned commit,
  untouched between rebuilds).
- Per rebuild: delete index → re-index → dump canonical graph → sha256.
- Record all 5 hashes side by side. Threshold: all identical. Any mismatch → **tripwire**.

### R3 — Staleness window
- Burst: 10-file edit (mix of modify/create/delete) applied in one shot.
- Measure wall-clock from the filesystem write to the moment `codegraph_status` (or the
  per-file staleness banner) reports the burst fully synced. Repeat ≥ 10 times (sample
  count not fixed by the ADR — use 10 for a usable p95; note deviation if fewer are run
  under time pressure).
- Separately, for every sampled window, check whether `codegraph_status`/banner correctly
  flagged the affected files as pending *during* the sync window (poll at short intervals,
  e.g. every 250ms, during the window).
- Record: all latencies, computed p95, and per-window pass/fail on "pending correctly
  reported."
- Threshold: p95 < 5s AND 100% correct pending-reporting. Any **unreported** staleness
  (status says synced/clean while content is actually stale) → **tripwire** (silent-wrong-
  answer class). Merely slow (p95 ≥ 5s) but correctly reported → tune, not kill.

### R4 — Coverage vs Graphify baseline (adjusted thresholds: 90% recall / 85% precision)
- **Graphify baseline node set — RESOLVED (coordinator, 2026-07-05): use option (a).**
  The full dump exists at `<repo>/graphify-out/graph.json`: a JSON object with a `nodes`
  list whose entries carry `label` (symbol/heading name), `src` (source path), `loc`
  (e.g. `L90`), `community`, and `file_type` (`code` vs docs) — verified by direct
  inspection during the G2S2 healthcheck. Baseline extraction: filter `nodes` to
  `file_type == "code"` under `src/`, key by (`src`, `label`). Regenerate the graph
  immediately before the comparison so the baseline matches the spike's repo snapshot
  (check the machine's graphify rebuild queue first — builds are single-writer).
  Original fallbacks if the schema has drifted at spike time: (b) a `graphify` CLI
  dump/export subcommand (`graphify --help`), or (c) aggregate per-scope `graphify query`
  results. Document which path was used in the result notes.
- Once a Graphify node set (functions + classes, keyed by qualified name + file) is
  obtained, get the CodeGraph node set for the same repo state via the canonical dump (§1).
- Node recall = |CodeGraph nodes ∩ Graphify nodes| / |Graphify nodes|, restricted to
  functions/classes.
- Edge precision: draw a 30-sample spot-check of CodeGraph call edges; manually verify each
  against source (does the call actually exist as reported: caller → callee). Precision =
  verified-correct / 30.
- Also run the Dart smoke test: index a small Dart fixture, confirm CodeGraph produces any
  non-empty, structurally sane node set for it (no numeric threshold — smoke pass/fail).
- Threshold: recall ≥ 90%, precision ≥ 85%, Python required, Dart smoke passes. Python
  recall materially below Graphify → **tripwire**.

### R5 — Blast-radius fit
- Select ≥ 3 real historical commits from chips repo history with a known actual
  touch-set (the commit's own file diff) or a known regression touch-set (if a linked
  defect/co-change record exists — cross-reference `harvester/enrichment/cochange.py` /
  `defect.py` outputs if available, but this is evaluation-only reading, not code change).
- For each commit: check out the pre-commit state into the CodeGraph-indexed fixture, run
  `codegraph_impact` on the changed symbol(s), compare reach set vs the actual touch-set.
- Record: reach ⊇ actual for how many of the 3 (or more) commits sampled.
- Threshold: ⊇ in ≥ 2 of 3. Not a sole-kill criterion — record and evaluate regardless of
  outcome.

### R6 — Files-are-truth law
- Delete `.codegraph/` (or whatever the confirmed on-disk index dir is, per §0 verify step)
  on the chips repo copy.
- Re-index from a clean clone (fresh `git clone` into a new scratch dir, not reusing the
  edited copy from R1/R3).
- Dump canonical graph (§1), diff against the R2 canonical baseline hash/dump for the same
  commit. Must be R2-identical.
- Threshold: full reconstruction, identical to R2 baseline. Any deviation → **tripwire**.

### R7 — Integration sketch
- Prototype an enrichment-analyzer contract shim mirroring `GraphifyEnricher`'s shape in
  `src/chips/harvester/enrichment/graphify.py` (status values: `ok` / `not_installed` /
  `failed` / `timed_out` / `skipped`, from `AnalyzerStatus` in
  `chips.harvester.enrichment.models`) — e.g. `CodeGraphEnricher` calling
  `codegraph_impact`/`status` instead of shelling out to `graphify query`.
- This is the **only** artifact allowed to touch `src/chips/`, and only behind a branch —
  do not merge, do not wire into the live pipeline.
- Sketch MCP exposure (which of `codegraph_impact`/`callers`/`callees`/`status` would be
  surfaced, and how they'd map onto existing MCP tool registration in `src/chips/mcp/`).
- Estimate integration effort in developer-days from the prototype's actual friction.
- Threshold: estimated ≤ 1 day. Evaluate-only, not a tripwire.

---

## 3. Tripwire handling

On any tripwire condition (R1 failure, R2 failure, R6 failure, unreported staleness in R3,
Python coverage failure in R4):

1. **Stop immediately** — do not continue to later criteria unless they're independent and
   time remains; use judgment, but do not paper over a tripwire by continuing past it
   silently.
2. Package: the failing numbers/diff, exact repro steps (commit/fixture state, commands
   run, canonical snapshot files under `<scratch>/adr-009-spike/snapshots/`), and a
   recommendation with rationale.
3. Hand to owner. **Never auto-kill** — per A6, the agent's role ends at data +
   recommendation; the owner records adopt-partition / reject / re-spike / continue-anyway.
4. Non-tripwire criteria (R3 slow-but-reported, R4 non-Python or edge precision, R5, R7)
   are "evaluate" — record the numbers and continue; they don't halt the spike on their own.

**Time budget: 2 days.** If the budget is consumed before all R1–R7 are measured: stop,
report whatever was measured plus what's outstanding, and treat the overrun itself as an
owner decision point (not an automatic abandon or automatic extension).

---

## 4. Result template (fill in, paste into owner's verdict entry)

| # | Test | Threshold | Measured | Pass/Fail | Notes |
|---|---|---|---|---|---|
| R1 | Incremental = rebuild | 100% node+edge equality, ≥100 sessions | | | |
| R2 | Determinism | identical hash × 5 | | | |
| R3 | Staleness window | p95 < 5s; 100% pending correctly reported | | | |
| R4 | Coverage vs Graphify | ≥90% recall, ≥85% edge precision, Python required, Dart smoke | | | |
| R5 | Blast-radius fit | reach ⊇ actual in ≥2/3 | | | |
| R6 | Files-are-truth | full reconstruction, R2-identical | | | |
| R7 | Integration sketch | ≤1 day estimated effort | | | |

**Pinned commit under test:** `<codegraph SHA + date>`

**Open setup items encountered:**
- R4 Graphify baseline extraction method actually used (a/b/c from §2) and why.
- (append any other verify-before-trusting discrepancies found at spike start)

**Recommendation (agent-authored, owner-decided):** adopt-partition / reject / re-spike /
continue-anyway — with rationale referencing the numbers above.

**Owner verdict:** _(recorded separately by owner in ADR-009 / A1 amendment — not by the
agent running this runbook)_
