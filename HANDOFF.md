# HANDOFF — Cowork session 2026-07-05 → Claude Code

Context for continuing the CHIPS CORTEX architecture-finalization work. Read alongside
`AGENTS.md` (conventions) and `docs/adr/A0-architecture-reconciliation.md` (reading rules:
target docs ≠ built runtime).

---

## 1. What this session produced

### Docs (all under `docs/` unless noted)
| File | What it is | Status |
|---|---|---|
| `design_docs/05_07/chips-diagram-v1_1-conformance-audit.md` | v1.1 diagram audit: 6 deviations (D1–D6) + regeneration order + checklist | done |
| `CHIPS CORTEX ARCHITECTURE DIAGRAM v1.2.svg` | regenerated target diagram, all D1–D6 applied; **v1.2 is the visual authority**, v1.1 PNG kept as provenance | done |
| `design_docs/05_07/chips-component-decision-amendments.md` | A1–A6 decision amendments incl. pending-decision queue (A5) and spike governance (A6) | living doc |
| `design_docs/05_07/chips-track2-p0-partial-population-decision-table.md` | Track 2 P0: {DRC input} × {fresh/stale/missing/failed-write} → gate action | DRAFT, awaiting owner sign-off |
| `adr/ADR-009-codegraph-structural-graph-spike.md` | CodeGraph spike design, rubric R1–R7, kill *tripwires* (owner decides, per A6) | designed, awaiting approval to run |
| `design_docs/05_07/chips-blast-radius-measures.md` | edge tiers + measures M1–M9 behind P0 rows B1–B5 | DRAFT |
| `design_docs/05_07/chips-defect-corpus-harvest-spec.md` | GitHub-issue label verification, tiers T1–T4, gaps A–E | DRAFT |

### Code — ⚠️ WRITTEN BUT NEVER EXECUTED (sandbox VM was broken all session)
| File | Change |
|---|---|
| `migrations/versions/013_add_issue_refs.py` | new `cortex_issue_refs` table (PK repo+ref, truthful fetch_status incl. 'skipped') |
| `src/chips/harvester/issue_refs.py` | NEW: GitHub issue fetcher (injectable httpx client), `pending_refs`, `store_issue_ref` upsert, `harvest_issue_refs` batch (halts on rate-limit), `label_tier_sql()` T1–T4 at query time |
| `src/chips/harvester/enrichment/defect.py` | Gap E: revert-introduced defect credit — new fields `revert_introduced_count/_commits`, new 2nd query (revert_of_sha = g.sha) |
| `tests/unit/test_issue_refs.py` | 12 tests, httpx MockTransport, no network |
| `tests/memory/test_issue_refs_migration.py` | 4 migration tests |
| `tests/harvester/enrichment/test_defect.py` | updated for new query order + 2 new revert tests |

**FIRST ACTION in Claude Code — verify:**
```bash
uv sync --dev
uv run pytest tests/unit/test_issue_refs.py tests/harvester/enrichment/test_defect.py tests/memory/test_issue_refs_migration.py
uv run coverage run -m pytest && uv run coverage report   # repo gate: 90%
```
Watch for: `DefectPredictor.predict` now executes THREE queries (count → revert → recent);
any other test mocking that conn with a 2-item side_effect will break.

**DONE (2026-07-05):** verified in the WSL Docker harness (not Windows uv — see
`chips-db-test-loop` memory) — 23/23 targeted tests green (13 issue_refs + 6 defect +
4 migration; `23 passed in 7.06s`), migrations 012→013 applied cleanly. Full live-tree
suite: `1138 passed in 44.64s` (includes all working-tree WIP; WS A *isolation* check
remains a separate open item). Coverage gate (90%) deferred to the actgpu CI gate at
push time.

## 2. Decisions made this session (recorded in amendments A1–A6)
- **A1:** Graphify-vs-CodeGraph = OPEN; candidate pinned `colbymchenry/codegraph`; proposed
  partition: CodeGraph for code, Graphify for docs/architecture. ADR-009 spike decides.
- **A2 (CONFIRMED):** Neovim (editor/fire surface) + tmux (session runtime). Helix → alt
  (Steel PR #8675 still unmerged). Diagram updated.
- **A3 (CONFIRMED):** spike-gated components render dashed + "◌ spike-gated" (Zenith, Context layer).
- **A4:** current-state companion diagram deferred until components finalized.
- **A6 (CONFIRMED):** no auto-kill/auto-adopt anywhere — agent reports data + recommendation,
  **owner records every verdict**.

## 3. OPEN — the four finalization questions (owner was about to answer; tool died)

**ANSWERED (2026-07-05)** — verdicts recorded in amendments A7–A10:
1. **P0 cold-start:** ANSWERED — declared shadow phase (gate advisory-only until signal
   coverage crosses a threshold), strict table from enforcement day; softening
   missing-fragility explicitly rejected. missing fragility/SPOF → assume-worst makes
   nearly every fire Manual on day one. Recommended: declared **shadow phase** (gate
   advisory-only until signal coverage crosses a threshold), strict table from enforcement
   day. Alternatives: strict from day one / soften missing-fragility (weakens the asymmetry
   law — not recommended).
2. **ADR-009:** ANSWERED — approved to run, R4 relaxed to 90% node recall / 85% edge
   precision (drafted 95%/90%). approve rubric as written and run the 2-day spike?
   (R1/R2/R6 non-negotiable.)
3. **Blast radius M9:** ANSWERED — yes, pulled into v1. pull in-flight DBOS workflow
   exposure into v1? Recommended yes — it targets the stated tail case and needs only a
   live workflow-registry query.
4. **Defect labels:** ANSWERED — locked: T1–T4 + ~60% hygiene-audit threshold + T4 excluded
   from calibration until audit passes.

## 4. Standing owner actions (unchanged, highest value first)
- **Gap A:** ANSWERED (2026-07-05) — harvester daemon is **not running anywhere** on this
  dev machine (no process/task/systemd/cron/container); finding recorded in the defect-corpus
  spec's Gap A section. Owner decision on SpaceMate deployment + full-history backfill still
  pending. confirm the harvester daemon runs against the **SpaceMate repo** (not just
  chips). If not: deploy + full-history backfill immediately — baseline loss is unrecoverable.
- Run verification (§1 above).
- Sign off P0 + approve ADR-009 → run spike → record verdict.
- Remaining closable decisions (A5 queue): co-change threshold + generated-code filter ·
  demo-vs-gate boundary list · Zenith spike run-or-kill (approved 2026-06-05, never run) ·
  stack-role inventory (Dolt/Timescale/Meilisearch/txtAI/Redpanda).

## 5. Critical path (unchanged)
verify new code → SpaceMate capture (Gap A) → ADR-009 spike → P0 sign-off →
**P2 end-to-end vertical** (one real fire through DRC → Signoff → Manual Review → Execute →
Audit on the Postgres stack) → simplify checkpoints fire → re-lock as v2.0 + build
current-state diagram (A4).

## 6. Known gaps in this session's work (honest ledger)
- New code unverified (VM failure) — treat as data, not shipped, per A6.
- `implementation_tracking.md` still lags code (calls fragility/yield aspirational; they
  exist raw+uncalibrated). Worth a sync pass.
- Top-10 missing list (agreed with owner): gate FSM, enforcement path, real evolutionary
  signals, defect corpus *deployment*, blast-radius computation, outcome loop, shadow mode,
  review surface, cold-start story, independent ground-truth benchmark. Items 4+7 are
  capture-now; 1+2+8 = the P2 vertical.
