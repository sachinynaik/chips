# CHIPS — Component Decision Amendments (2026-07-05)

> Amendments to `docs/design_docs/18_06/chips-component-decision-register.md`. Each entry
> carries an explicit status: **CONFIRMED** (decision of record) · **PROPOSED** (recommended,
> awaiting owner confirmation) · **OPEN** (evaluation slot, no decision). Nothing here is a
> decision until marked CONFIRMED — recommendations are not laundered into verdicts.

---

## A1. Structural graph tool — Graphify vs CodeGraph

**Status: OPEN — full evaluation ordered (owner decision, 2026-07-05). No swap, no
retention, until the spike reports.**

Driving factor (recorded): **CodeGraph is real-time** — incremental graph sync on file save
(file-watch, ~2s debounce, only affected graph portions updated) — whereas **Graphify
requires a regenerate**. Freshness of the structural graph is gate-relevant: Blast Radius
Read consumes it, and stale evidence re-escalates. A structural graph that is stale between
regenerations is a standing freshness gap.

This is a legitimate recorded gap, so the anti-goal ("add no more code-intelligence
graphs") does not bar the evaluation — the candidate would *replace*, not add.

**Evaluation spec (ADR-009 to be authored from this):**

0. **Candidate PINNED (owner, 2026-07-05): `colbymchenry/codegraph`** (MIT). Verified
   capabilities: tree-sitter extraction → local SQLite + FTS5; 20+ languages **incl.
   Python and Dart** (SpaceMate stack); native OS file-watcher with debounced auto-sync
   (default 2s, tunable); **per-file staleness banners** on MCP responses during the sync
   window; connect-time (size, mtime) + content-hash reconciliation; MCP tools incl.
   `codegraph_impact` / `callers` / `callees` / `status` (blast-radius primitives).
   The staleness-declaration behavior is purity-law-aligned: it labels the gap instead of
   answering through it.

0b. **Division of labor PROPOSED (owner, 2026-07-05):** the tools overlap but each has
   unique value — **CodeGraph for code** (structural graph, gate-relevant, feeds Blast
   Radius Read after the spike passes) · **Graphify for everything else** (docs,
   architecture diagrams, non-code artifacts). This is a **partition, not an added
   graph** — the anti-goal ("no more code-intelligence graphs") holds iff the roles stay
   disjoint and exactly one graph feeds the gate for code. Spike verdict converts this
   from PROPOSED to CONFIRMED; diagram + G2S2 lineage labels update only then.
1. **Criteria** (weighted toward gate fitness, not features):
   - Incremental correctness: after N random edits, does the incremental graph equal a
     from-scratch rebuild? (Purity law: a derived cache must be reconstructable and
     provably consistent.)
   - Staleness window under realistic edit load vs Graphify regenerate cadence.
   - Determinism: same input → same graph, run-to-run.
   - Language coverage for SpaceMate (Python required; TS/Dart as weighted extras).
   - Integration cost: G2S2 lineage seat, `harvester/enrichment/` analyzer contract,
     MCP exposure.
   - Local-first, license, maturity/bus-factor.
2. **Kill tripwires:** incremental ≠ rebuild on any test case; nondeterministic output;
   Python coverage materially worse than Graphify. Per A6, tripwires stop the spike and
   produce a kill-*recommendation* — the owner records the verdict.
3. **Time budget:** 2 days (house pattern, per ADR-002).
4. **Output:** ADR-009 with verdict adopt-replace / reject / re-spike. Until then Graphify
   remains the operating tool (status quo ≠ decision).

---

## A2. CLI surface — split into two slots

**Status: CONFIRMED (owner sign-off, 2026-07-05) — Neovim (editor/fire surface) + tmux
(session runtime). Supersedes the 18_06 "Helix adopt"; Helix demotes to alt with the
existing Steel-merge watchlist trigger.**

The register's single "Helix / CLI" row conflates two roles. Split:

| Slot | Requirement (locked) | Recommendation | Status |
|---|---|---|---|
| Edit / fire surface | surgical edit + summon-palette chip firing (tree-sitter, LSP, ripgrep, fuzzy pick → fire) | **Neovim** (supersedes 18_06 Helix adopt) | PROPOSED |
| Session runtime (multiplexer) | persistent sessions · pane management · hosts the fire surface and agent views | **tmux** | PROPOSED |

**Editor rationale — why Neovim over Helix (new evidence, 2026-07-05):** the 18_06 Helix
adopt was conditioned on "Steel plugin watch-not-depend." The condition has now aged badly:
the Steel PR (helix-editor/helix #8675) remains **unmerged as of mid-2026**, more than a
year after prototype. The locked requirement is a *keybound summon-palette → ranked fuzzy
search → fire* UX. Helix cannot host that natively without a plugin system — it is
shell-out-only for the foreseeable future. Neovim delivers the requirement **today**
(Lua + Telescope-class pickers calling the `chips` CLI; tree-sitter and LSP first-class;
stable on Windows). Helix demotes to *alt* (revisit if Steel merges to mainline stable —
the existing watchlist trigger already says exactly this).

**Runtime rationale — why tmux:**
1. The summon-palette overlay is directly buildable with `tmux display-popup` — the firing
   surface works in any editor and over SSH/WSL.
2. Battle-tested, universal, scriptable; zero adoption risk on the WSL host CHIPS already
   assumes (ADR-002).
3. **Agent observation is not the multiplexer's job in CHIPS** — that is the Signoff
   Console / Web UI's locked role (rich blast-radius render). Buying agent-awareness
   through Herdr (young, single-maintainer) would duplicate a planned surface in a
   less-governed layer.
4. Zellij: fine ergonomics; its WASM plugins buy nothing tmux popups don't for this
   requirement; younger ecosystem. Pass.
5. **Herdr: watch.** Re-evaluate only if the Signoff Console lags and terminal-level
   agent observation becomes acute; its socket API + per-agent state would then map onto
   the MCP/Agents surface.

Diagram rule: label the surface by role until slots are CONFIRMED; then "Neovim / CLI
(tmux)" or equivalent.

**Removing the CLI surface entirely: rejected** (and not requested). It is the human
rapid-fire path; without it, entry is Web UI / MCP / API only.

---

## A3. Rendering convention — spike-gated components

**Status: CONFIRMED.**

Components whose ADR status is "spike approved — integration undecided" are rendered with a
**dashed border + "◌ spike-gated" tag** (not removed, not rendered as settled). Applied in
diagram v1.2 to: Zenith / Trace Cache (ADR-002), Context Layer (Headroom · RTK · lowfat).
Rationale: removal misrepresents the record; unannotated presence launders an undecided
integration into a settled one.

---

## A4. Current-state companion diagram

**Status: DEFERRED (owner decision, 2026-07-05).**

A built-components-only companion diagram will be produced **after** the component slots
above are finalized. Until then the target diagram (v1.2) is the sole visual, read under the
A0 convention: target design docs are not built-runtime descriptions.

---

## A5. Pending decision queue (consolidated, 2026-07-05)

Everything still open across the register, ADRs, and this file — split by whether it is
closable now or gated on an event.

**Closable now (no prerequisite):**

| # | Decision | Source | Closes via |
|---|---|---|---|
| 1 | CodeGraph spike verdict (A1) — gate-fitness of `colbymchenry/codegraph`; confirms/kills the code-vs-docs partition | this file | run 2-day spike → ADR-009 |
| 2 | ~~Track 2 P0 — partial-population gate decision table ({DRC input} × {fresh/stale/missing/failed-write} → action)~~ **DECIDED 2026-07-05 (A7)** | build brief | paper artifact; **blocks all gate code** |
| 3 | Co-change support threshold + generated-code filter | register OD-2 | short design note; blocks entropy quality |
| 4 | Demo-vs-gate metric boundary — write the explicit list | register OD-5 | one-page list (mostly already stated) |
| 5 | Zenith spike — run it or kill it (approved 2026-06-05, unexecuted) | ADR-002 | 2-day spike per its locked rubric |
| 6 | Stack-role verification — Dolt/Timescale/Meilisearch/txtAI/Redpanda: CHIPS-specific vs SpaceMate-wide | register OD-8 | inventory pass against A0 |

**Gated on an event (do not force early):**

| # | Decision | Gate |
|---|---|---|
| 7 | P1 ontology contract (g:* vocabulary, named-graph partitions, versioning) | needed when Oxigraph lands |
| 8 | Yield calibration cadence + staleness threshold | defect corpus large enough |
| 9 | pgvector scale check (keep vs Qdrant) | simplify checkpoint, post-vertical |
| 10 | Chip-admission safety gate | real chip library exists |
| 11 | Materials clock / coefficient tuning | Assay running (post V1.1/V1.2 signals) |
| 12 | DeltaX vs Timescale (OLAP slot) | Materials projection work begins |
| 13 | Context-compression integration (Headroom · RTK · lowfat) | their spikes |
| 14 | Simplify checkpoints ×3 (Letta↔Cognee · DRC consolidation · inspection scope) | first end-to-end vertical |

Implementation blockers on the critical path (not decisions, listed for completeness):
**L7** positional finding evidence IDs (mandatory Slice 0) · **L12** anti-regression queue
not verifier-driven.

---

## A6. Spike verdict governance

**Status: CONFIRMED (owner decision, 2026-07-05).**

No spike, evaluation, or tripwire may auto-kill (or auto-adopt) a component. The agent's
role ends at: run the rubric, report the numbers, attach a recommendation with rationale.
**The owner records every verdict.** Applies to all spikes present and future (ADR-009,
ADR-002/Zenith, context-compression spikes, and successors). Rationale: during setup,
thresholds are provisional and calibrated by judgment; and the locked gate guarantee —
no self-approval by agents or orchestrators — applies to the evaluation process itself.

---

## A7. P0 cold-start — declared shadow phase

**Status: SIGNED OFF (owner decision, 2026-07-05).** Gate runs advisory-only until signal
coverage crosses a declared threshold; strict table applies from enforcement day; softening
missing-fragility explicitly rejected (would weaken the asymmetry law). Full table and
asymmetry-law/block rows (LOCKED) recorded in
`chips-track2-p0-partial-population-decision-table.md`.

---

## A8. ADR-009 — approved to run

**Status: APPROVED (owner decision, 2026-07-05).** Spike approved to run with R4 relaxed to
90% node recall / 85% edge precision (drafted 95%/90%). Full rubric and tripwires recorded
in `ADR-009-codegraph-structural-graph-spike.md`. Spike verdict itself remains open (A5 #1)
until the spike is run and reported.

---

## A9. Blast radius M9 — pulled into v1

**Status: CONFIRMED (owner decision, 2026-07-05).** In-flight DBOS workflow exposure (M9)
is pulled into v1. Recorded in `chips-blast-radius-measures.md` §5.

---

## A10. Defect labels — locked

**Status: LOCKED (owner decision, 2026-07-05).** Tiers T1–T4; ~60% hygiene-audit link-rate
threshold; T4 excluded from calibration until the audit passes. Recorded in
`chips-defect-corpus-harvest-spec.md`.

---

*A hand-authored node in the decision-provenance lineage under A0. Statuses are explicit;
a PROPOSED entry becomes CONFIRMED only by owner sign-off recorded in this file.*
