# Session Handoff — 2026-07-07

**Scope of this handoff:** the multi-day session covering 2026-07-05 → 2026-07-07 (the
merge train, the A5/A11–A14 owner sign-offs, the P0 coverage threshold, and the ADR-009
CodeGraph spike run + verdict). Written for a fresh Claude Code session (or a human)
continuing this work.

**Repo state at handoff:** `master` @ `583179e` — clean, synced with origin, CI green
(run 28816730069). Working tree clean. Branch protection live on `master` (required
`build` check, `strict:false`, `enforce_admins:false`). All merges go through PRs,
rebase-merged one at a time, green between.

---

## 1. Design & technical decision documents produced/updated this session

All paths relative to repo root `C:\sachinynaik\chips\`.

### ADRs and verdict records

| Document | What it decides | Status |
|---|---|---|
| `docs/adr/ADR-009-codegraph-structural-graph-spike.md` | CodeGraph as real-time structural graph. Spike RUN 2026-07-06/07. **Verdict A14: REJECT for gate use; advisory OK.** Graphify stays the operating tool; code/docs partition NOT adopted. | Verdict recorded, merged (PR #8) |
| `docs/design_docs/05_07/adr-009-spike-result.md` | Full spike evidence package: R1–R7 result table, three defect signatures (A silent partial index / B ambiguous-name call-edge misresolution / C duplicate-edge flap), open setup items, recommendation. | Merged (PR #8) |
| `docs/design_docs/05_07/chips-component-decision-amendments.md` | The amendment log. New this session: **A11** (co-change thresholds), **A12** (demo-vs-gate boundary ratified), **A13** (stack role inventory), **A14** (ADR-009 spike verdict). A5 closable-now queue rows 1, 3, 4, 6 struck DECIDED. | Merged (PRs #7, #8) |

### Signed-off design notes (drafts → SIGNED OFF this session)

| Document | Owner verdicts recorded |
|---|---|
| `docs/design_docs/05_07/chips-cochange-threshold-design-note-draft.md` | **A11:** Fixed N=2 on both surfaces (pair fetcher + entropy); query-time generated-code filtering (not capture-time); reuse A7 shadow-phase framing; extend `classify_generated_kind` now (lockfiles + vendored). |
| `docs/design_docs/05_07/chips-demo-vs-gate-boundary-draft.md` | **A12:** 15-row demo-vs-gate table ratified (rows 13–15 added). Row 15: CodeGraph tools **allowed as advisory** on real work in-window. One row deliberately open: repo_metrics_v ↔ Policy Eval (until Policy Eval design). |
| `docs/design_docs/05_07/chips-stack-role-inventory-draft.md` | **A13:** Dolt = target-adopt gated on Materials; Meilisearch = keep CHIPS role on shared substrate; **txtAI REMOVED stack-wide** (replaced by unified chat/search embedding architecture, shared with video analytics); **Redpanda → NATS JetStream**; schema-registry slot OPEN (buf stands alone). |
| `docs/design_docs/05_07/chips-track2-p0-partial-population-decision-table.md` | **P0 coverage threshold declared:** signal coverage = fraction of shadow-mode gate fires over a trailing 14-day window whose required DRC inputs were ALL fresh; enforcement day arrives at **80%** (provisional + tunable — a noise dial, not a safety dial; the locked asymmetry law prevents wrong PASSes). |

### Registers updated in place

- `docs/design_docs/18_06/chips-component-decision-register.md` — Meilisearch CONFIRMED
  (shared substrate); txtAI REJECT/REMOVED; MinIO / NATS JetStream (was Redpanda+RisingWave);
  Redpanda Schema Registry struck.
- `docs/implementation_tracking.md` — remains the current-state truth layer; synced earlier
  in the arc (fragility/yield, issue_refs, defect Gap E).

### Context documents (read these to understand the decisions)

- `docs/adr/A0-architecture-reconciliation.md` — two-lineage reading convention, canonical vocabulary.
- `docs/02_06_execution_ledger.md` — the readiness gate (reward-consuming work still blocked on Phase-3 verifier).
- `HANDOFF.md` (repo root) — the *previous* (2026-07-05 Cowork) handoff; its actionable items were executed and landed via PR #4. Superseded by this document.

---

## 2. Pending work (implementation plans, task lists, next steps)

Ordered by priority as agreed with the owner:

1. **SpaceMate harvester deployment + backfill** — the approved next large task.
   Plan doc: `docs/design_docs/05_07/spacemate-harvester-deployment-plan.md`.
   Both prereqs already approved by owner ("Approve both: dedicated PG + fix alembic first"):
   - Stand up a dedicated `chips-prod-postgres` container on the WSL Docker host
     (chips CI now uses **57432**; SpaceMate e2e owns 55432; `:5432` is a foreign DB — never probe it).
   - **Fix the alembic.ini hardcoded-URL defect properly first** — small TDD slice, before deployment.
   - The unrecoverable-baseline clock is ticking: every day un-harvested is SpaceMate git/defect
     history not yet captured into `cortex_git_commits`.

2. **A11 follow-up implementation slices** (recorded in amendment A11; three small TDD slices):
   - Pair-fetcher floor + generated-code JOIN-exclusion in `CochangeFetcher.fetch`
     (`src/chips/harvester/enrichment/cochange.py` — currently has NO floor/filter).
   - Query-time entropy storage (replace the capture-time hard-zero in
     `_compute_stored_cochange_entropy`, `src/chips/harvester/signals.py`).
   - `classify_generated_kind` extension: lockfiles + `/vendor|/vendored|/third_party`
     path segments (`src/chips/harvester/signals.py`).

3. **File Signature A upstream** at `colbymchenry/codegraph` — seeded repro ready
   (`C:\sachinynaik\adr-009-spike\` scripts + artifacts; pinned SHA
   `99152212a99d8da363a280852ce44488a22f6328`, npm 1.2.0). **Outward-facing — needs
   explicit owner go-ahead before filing.** ADR-009 reconsideration (nodes+contains
   partition) is gated on this fix landing upstream.

4. **Zenith spike (A5 queue item #5)** — the last open closable-now decision-queue item
   (approved 2026-06-05, never executed). Run it or formally kill it.

5. **Housekeeping:**
   - Dependabot PR #1 (idna 3.14→3.15) still open + 17 dependabot alerts unreviewed.
   - WSL IPv6/registry-mirror substrate proposal — still PROPOSED, machine-wide
     (see risk section; memory: `docker-hub-pull-flake-mirror-workaround`).
   - Delete `/home/runner/stale-venv-quarantine-20260706` on the runner (user-run; root-owned).
   - Spike scratch (`C:\sachinynaik\adr-009-spike\`) and local branch
     `spike/adr-009-r7-codegraph-enricher` — **retain until the upstream filing is done**
     (they are the repro artifacts), then delete.
   - Old local `slice/*` branches — historical, untouched; prune when convenient.

Session-memory pointers (auto-memory at
`C:\Users\sachi\.claude\projects\C--sachinynaik-chips\memory\`): `MEMORY.md` index, esp.
`branch-push-state-and-harness-critical-path`, `chips-db-test-loop`,
`stack-substrate-unified-chat-search`, `act-gitignore-copy-exclusion`,
`docker-hub-pull-flake-mirror-workaround`.

---

## 3. Workstreams, branches, and push state

### Merged this session (all rebase-merged to master, branches deleted on origin)

| PR | Branch | Contents |
|---|---|---|
| #2 | `feat/ws-a-track1-signals` | WS A Track 1 harvester signals: co-change min-support threshold, Assay decay, truth-replay rebuild. |
| #3 | `ci/harden-runner-artifacts` | CI hardening: `UV_PROJECT_ENVIRONMENT=/tmp/chips-venv` on runner (venv out of checkout path), persistent flashrank model cache (runner `$HOME/.cache/flashrank`, act toolcache volume). |
| #4 | `feat/compiler-compression-contract` | #33 compression contract + issue-ref harvesting (migration 013, `issue_refs.py`, T1–T4 tiers) + Gap E revert defect credit + 05_07 design tranche (A7–A10, ADR-009 spike pack, v1.2 diagram) + executed HANDOFF. |
| #5 | `ci/move-service-port-57432` | CI postgres service port 55432 → 57432 (collision with SpaceMate e2e harness). |
| #6 | `feat/ws-b-track2-paper` | WS B Track 2 paper docs: P0 partial-population table + P1 ontology contract ratified. |
| #7 | `docs/a5-signoffs-a11-a13` | Owner verdicts A11–A13, P0 coverage threshold, `.pytest_tmp` gitignore. |
| #8 | `docs/adr-009-verdict-a14` | ADR-009 verdict A14 + spike evidence package into repo. |

### Local branches that still exist — push/merge state

| Branch | State | Action |
|---|---|---|
| `master` | `583179e`, synced, clean | — |
| `spike/adr-009-r7-codegraph-enricher` @ `1cfc745` | **LOCAL-ONLY BY DESIGN — never merge, never push** (ADR-009 constraint). Contains the R7 prototype: `src/chips/harvester/enrichment/codegraph.py` (~90 LOC `CodeGraphEnricher`) + `tests/harvester/enrichment/test_codegraph.py` (5/5 green in WSL harness). | Retain as spike artifact until upstream filing done, then delete. |
| `feat/evidence-hypothesis-primitives` | **ahead 1 of origin** (`5adb052` docs reconcile commit, unpushed) | Historical WS branch; content likely already on master via the train — verify before pushing or prune. |
| `slice/enrich-reliability` | **ahead 1 of origin** (`e7d6bf9`, unpushed) | Same: verify subsumed-by-master, then prune. |
| `docs/tooling-research`, `multireview-harness`, `slice/*` (×10), `worktree-agent-*` | Historical, local-only, untouched this session | Prune sweep when convenient (verify subsumption first). |

**Nothing on master is unpushed. No dirty working tree. The only deliberate never-push
branch is the spike branch.**

### Conventions in force

- Rebase-merge only (linear history), one PR at a time, CI green between merges.
- Plain `git commit` / `git push` — never `--no-verify`, `SKIP_ACT=1`, `SKIP_LINT=1`,
  or local `core.hooksPath`. Pre-push act gate + self-hosted runner `sachin-wsl-gpu-chips`.
- Tests run ONLY via the WSL harness (`/chips-test` skill):
  `wsl -d Ubuntu-24.04 -- bash scripts/test-in-wsl-docker.sh <pytest args>` —
  Windows pytest cannot reach the WSL Docker Postgres.
- Coverage gate: 90% (`uv run coverage report` fails under it).

---

## 4. Key risks, challenges, unknowns — things to watch out for

1. **CodeGraph Signature A (silent partial index) — the standing trap.** Advisory use is
   sanctioned (A12 row 15), but ~1.4% of index builds silently drop content (worst
   observed: 23% of nodes + the ENTIRE call-edge class; exit 0; clean `status`). **Any
   advisory consumer must run an external count-based sanity check** before trusting an
   index. Do NOT promote any CodeGraph surface toward the gate until upstream fixes A —
   and even then, call edges stay advisory (Signature B caps them).

2. **WSL egress black-holing (unresolved, machine-wide).** Bulk transfers to some
   destinations (HF CDN, docker registry-1) black-hole from WSL; IPv6-disable/forced-IPv4/
   MTU-clamp all insufficient; **WSL reboot silently reverts sysctl mitigations**. Current
   posture = pre-warmed caches (flashrank in runner home + act-toolcache volume; docker
   pulls via mirror.gcr.io + digest verify). If CI suddenly times out downloading
   something new, suspect this first. Durable substrate fix still PROPOSED, not applied.

3. **act's repo copy excludes gitignored files.** Warm caches in the working tree are
   invisible to the pre-push act gate — persistent warm state must live in the
   `act-toolcache` volume (`/opt/hostedtoolcache`). A "works on runner, dies in act"
   asymmetry is usually this.

4. **Port topology on the shared Docker host.** chips CI = **57432**; 55432 = SpaceMate
   e2e (another live lane); **5432 = a foreign DB, never probe it**. The planned
   `chips-prod-postgres` needs a fresh port — collision caused a real master CI failure
   once already.

5. **alembic.ini hardcoded-URL defect** — known, approved-to-fix, NOT yet fixed. It will
   bite the harvester production deployment if skipped; the owner explicitly ordered
   fix-first.

6. **SpaceMate unrecoverable-baseline clock.** Until the harvester daemon covers the
   SpaceMate repo, point-in-time signals (coverage runs, working-tree states) are being
   lost. Git history itself is replayable, but the longer deployment waits, the weaker the
   early defect/co-change corpus.

7. **P0 80% coverage threshold is provisional.** All-inputs-fresh over trailing 14 days is
   the declared metric; the number is a noise dial (the asymmetry law is the safety).
   Expect to tune it against real shadow-phase data — do not treat 80% as sacred, and do
   not let tuning it become a backdoor to weakening the asymmetry law.

8. **A12's one deliberately open row** (repo_metrics_v ↔ Policy Eval) is open **on
   purpose** — pending Policy Eval design. Don't "helpfully" close it.

9. **Spike setup unknowns (recorded, unresolved):** npm 1.2.0 binary vs pinned repo SHA
   not bit-verified; R1 incremental path used manual `codegraph sync` rather than
   watcher-debounce (watcher measured separately in R3). Relevant only if the spike is
   re-litigated or re-run post-upstream-fix.

10. **Ledger gates still bind.** Reward-consuming work (composite_reward, mastery, OPE,
    online bandit, rule induction) remains **blocked on the Phase-3 verifier**; the
    Signoff gate does not exist yet (don't call constraint-injection "the gate");
    Oxigraph migration is trigger-gated, not scheduled. Vocabulary per A0.

11. **Uncommitted-WIP hygiene.** The tree is clean today — keep it that way. The previous
    arc's pain (43 mixed dirty files across two workstreams) came from letting unrelated
    WIP accumulate on one branch.
