# re_gent — Decision-Grade Assessment for CHIPS CORTEX

**Author:** Research engineering pass (Claude, co-reviewed with Codex)
**Date:** 2026-06-02
**Scope:** `regent-vcs/re_gent` (Apache-2.0, v1.1.0, Go) evaluated against CHIPS's architecture (deterministic context-compiler; sidecar to coding agents; Python 3.13; Postgres/SQLAlchemy/Alembic; FastMCP "chips-cortex"; OTel + Prometheus + DuckDB export already shipped). Priorities, in order: **(1) determinism, (2) local-first, (3) simplicity, (4) sidecar-not-inline.**

Sibling notes (same series, same verdict-grammar): `docs/research/open-bias-assessment.md`, `docs/research/openkb-forge-assessment.md`. Sources fetched 2026-06-02.

---

## 1. Executive Summary

**re_gent — Verdict: COMPANION TOOL + PATTERN SOURCE. Do NOT (and cannot) embed. Re-evaluate as a Phase-4 reward-log/failure substrate; borrow its content-addressed audit-DAG data model for CHIPS's own brief-provenance.**

re_gent (`regent-vcs/re_gent`, Apache-2.0, **v1.1.0, 1 Jun 2026, Go 98.5%, ~652★**) is *"git for AI coding agents"*: it auto-captures every agent **tool-invocation** (Claude Code / Codex CLI / OpenCode) into a **content-addressed DAG of steps**, stored **fully locally** in a `.regent/` directory (`objects/` blobs, `refs/` session pointers, `index.db` SQLite index, `config.toml`). A **step** is `{parent, tree (workspace snapshot), causes:[{tool_name, args, result}], session_id, timestamp}`, keyed by a **BLAKE3** content hash. It exposes `rgt log` (`--json`/`--graph`/`--session`), `rgt blame <path>:<line>` (per-line → the prompt/step that wrote it), `rgt show <hash>`, `rgt sessions`, `rgt status`, `rgt cat <hash>`. CLI-first + a VS Code extension; **rewind/fork are roadmap, not yet shipped**. No cloud, no API key.

Three things fix its relationship to CHIPS:

1. **It is a Go CLI, not an importable library.** There is no Python import surface. So "depend on it" is not even on the table — the only integration is **ingesting its output** (`rgt log --json`, or reading `index.db`) as an external data source. That is a *boundary*, not a dependency. ✅ confirms "companion, not embed."
2. **It answers a different question than CHIPS's nearest gap.** re_gent records **what the agent did** (action provenance: which prompt produced which line). CHIPS's Slice A5a needs **why the brief recommended what it did** (brief-rationale provenance: which constraints fired, which evidence supported each). **Adjacent systems, not the same one** — re_gent does *not* deliver A5a.
3. **Where it genuinely fits is later and is twofold:** (a) **Phase-4 reward substrate** — re_gent's per-session, per-turn outcome trail is a clean external feed for correlating a CHIPS brief with the agent's *subsequent actions and their success/failure*, populating `verification_reward`; (b) **failure→constraint promotion** — recurring known-bad action patterns in re_gent's blame trail are a signal to promote a durable constraint (human-confirmed). Both are Phase-4-shaped, both respect the sidecar boundary (CHIPS *reads* the trail, never intercepts).

Plus a **pattern borrow** independent of the tool: re_gent's **content-addressed, append-only step-DAG with `blame`** is a strong data-model template for how CHIPS could persist its *own* brief-provenance/audit records (content-addressed, immutable, blame-able by `find:`/`con:` evidence ID) in Slice A5a.

**Net:** Don't adopt now (A4 → A5a → A3 come first; re_gent is Phase-4-adjacent). Run it alongside in the dev workflow if useful today. Borrow the audit-DAG+blame *shape* for A5a. Schedule a real **ingestion spike at Phase 4** to wire re_gent's `--json` trail into the reward log + failure-promotion path — gated on a shared correlation key existing (see §4).

---

## 2. Mechanics (verified against repo, 2026-06-02)

- **What it captures & how:** hooks auto-configured on `rgt init` ("zero config"), at the **tool-invocation level** for Claude Code / Codex CLI / OpenCode — *not* filesystem/git polling. Capture is automatic per agent turn; no manual commits.
- **Data model:** `Step = {parent, tree (workspace snapshot), causes:[{tool_name, args, result}], session_id, timestamp}`; **BLAKE3** content-hash; steps form a per-session DAG (`refs/` branch per session).
- **Storage:** `.regent/` mirrors `.git/` — `objects/` (content blobs), `refs/`, `index.db` (SQLite query index), `config.toml`. **Fully local.**
- **Commands:** `rgt log [--json|--graph|--session|-n]`, `rgt blame <path>[:<line>]` (→ step hash, session, tool, **prompt text**, timestamp), `rgt show <hash>` (parent + tree + tool call + output + the user/assistant conversation pair), `rgt sessions`, `rgt status`, `rgt cat <hash>`. **Roadmap-only:** rewind/fork, GC, more adapters (Cursor/Cline/Continue).
- **Integration shape:** Go CLI + VS Code extension. **Not a library** (no documented import API). Programmatic egress = `rgt log --json` + `rgt cat <hash>`; `index.db` is readable SQLite but not a supported public interface.
- **Local/cloud:** fully local; no service, no key.
- **Maturity:** v1.1.0 (5 releases), 73 commits, ~652★/46 forks. Core audit trail (log/blame/show) feature-complete; rewind/GC/extra adapters pending.

---

## 3. Head-to-Head vs CHIPS

| Dimension | CHIPS | re_gent | Implication |
|---|---|---|---|
| **Question answered** | *Why* did the brief recommend X (constraints fired, evidence cited)? | *What* did the agent do (prompt→line blame)? | Adjacent provenance layers; re_gent ≠ A5a |
| **Integration** | Python, MCP-native | **Go CLI**, `.regent/` + SQLite + `rgt log --json` | Ingest-as-data-source only; cannot import → companion not dep |
| **Determinism** | Deterministic compile | Content-addressed (BLAKE3) DAG — deterministic given identical inputs | ✅ compatible |
| **Local-first** | Postgres+MCP+Ollama, cloud barred | Fully local, no key | ✅ compatible |
| **Sidecar boundary** | Compiles brief before agent acts; never intercepts | Observes agent turns (hooks), never blocks | ✅ both observe-not-intercept |
| **Maturity** | Infra under deliberate TDD | v1.1.0, ~652★, core complete; rewind pending | Companion-grade; don't make load-bearing yet |
| **Correlation seam** | brief_id / correlation IDs (OTel baggage) | its own `session_id` | **Integration cost** = mapping session_id ↔ brief_id (see §4 Q1) |

**The crux:** re_gent and CHIPS both *observe without intercepting* and both store deterministic, content-addressed, local provenance — they are philosophically aligned. They simply provenance **different halves of the loop** (agent actions vs brief rationale). That makes re_gent a natural *downstream* feed into CHIPS's reward log, not a component of the compiler.

---

## 4. Mapping onto CHIPS's Slices

- **Slice A5a (auditability) — BORROW THE PATTERN, not the tool.** re_gent's content-addressed append-only **step-DAG + `blame`** is a template for CHIPS's own brief-provenance record: per brief, an immutable, content-addressed audit entry blame-able by evidence ID (`find:`/`con:`). Use the *shape*; CHIPS stays in Postgres, not `.regent/`.
- **Phase 4 reward log (`verification_reward`) — INGEST AS DATA SOURCE.** Wire `rgt log --json` (or `index.db`) so a CHIPS brief can be correlated to the agent's subsequent turns and their outcome → reward signal. Respects the sidecar boundary (read-only).
- **Failure→constraint promotion (write-back / locked backlog) — INGEST.** Recurring known-bad patterns in re_gent's blame trail = candidate constraints, surfaced to the human-confirm gate (`cortex_add_constraint`). Pairs with the deterministic rule-induction approach in the gap-tool map.
- **NOT near-term:** re_gent does not advance A4 (flag layers off), A3 (decompose builder), or A5a's *core* deliverable. It is Phase-4-adjacent. **Does not reorder A4.**

---

## 5. Prioritized Recommendations

| # | Recommendation | Type | Rationale | Determinism | Local-first |
|---|---|---|---|---|---|
| 1 | **Borrow re_gent's content-addressed step-DAG + blame data-model for the A5a brief-provenance record** (Postgres-backed, blame-able by evidence ID). | Borrow (pattern) | Proven shape for immutable, queryable provenance; aligns with A5a's "explain the brief" goal. | **PASS** — content-addressed, deterministic | **PASS** |
| 2 | **At Phase 4, ingest `rgt log --json` as a reward-log feed** correlating brief → subsequent agent actions/outcomes → `verification_reward`. | Companion (ingest, defer to Phase 4) | Cheapest external source of outcome signal; read-only, sidecar-safe. | **PASS** — deterministic trail | **PASS** — fully local |
| 3 | **At Phase 4, mine re_gent blame trails for recurring known-bad patterns → constraint candidates** (human-confirmed via `cortex_add_constraint`). | Companion (ingest, defer) | Operationalizes failure→constraint promotion (Codex gap #1). | **PASS** *if* mined deterministically (pattern match, not LLM judge) | **PASS** |
| 4 | **Optionally run re_gent in the dev workflow now** (agent-action audit for CHIPS's own development). | Companion (workflow) | Useful provenance during CHIPS dev; zero coupling. | **PASS** | **PASS** |
| 5 | **Do NOT embed / depend on re_gent.** | Skip (as dependency) | Go CLI, no Python import surface; v1.1.0 core-only. Value is ingest + pattern, not linkage. | — | — |

---

## 6. Open Questions / Validate Before Committing

1. **Correlation key (blocker for Recs #2/#3).** re_gent keys by its own `session_id`; CHIPS keys by brief_id / OTel correlation IDs. A reliable **session_id ↔ brief_id mapping must exist** before any reward-log ingestion is meaningful. Determine whether the agent's CHIPS-brief request and its re_gent session can share a key (e.g., OTel baggage threaded through the agent). If not, ingestion is guesswork — defer.
2. **Egress stability.** `rgt log --json` is supported; `index.db` is internal SQLite (not a public API) and may change. Prefer the `--json` contract; pin a re_gent version if ingested.
3. **Rewind dependency.** Any CHIPS use that assumes rewind/fork must wait — those are roadmap-only in re_gent today.
4. **Pattern-borrow vs build (Rec #1).** Confirm A5a's provenance record can be content-addressed cleanly given CHIPS's existing `find:<content-hash>`/`con:` IDs — likely yes, but validate before adopting the DAG shape.
5. **Sequencing.** This is research; A4 remains the next product slice, A5a the one after. re_gent's real wiring is Phase-4. Nothing here reorders A4.

---

### Source references
- re_gent: `regent-vcs/re_gent` (Apache-2.0, v1.1.0, 1 Jun 2026, Go 98.5%, ~652★/46 forks, 73 commits). Data model `Step{parent, tree, causes[{tool_name,args,result}], session_id, timestamp}`, BLAKE3 hash, `.regent/{objects,refs,index.db,config.toml}`. Commands `rgt log/blame/show/sessions/status/cat`; `--json`/`--graph` egress; rewind/fork/GC roadmap-only. Adapters: Claude Code, Codex CLI, OpenCode. Sources: github.com/regent-vcs/re_gent, re-gent.dev.
- Related (not assessed here): `Ekaanth/blameprompt`, `sunilmallya/agentdiff` (comparable prompt→line provenance) — noted as the same category if re_gent's egress proves unstable.
- CHIPS internal: `docs/research/open-bias-assessment.md` (SHADOW/trace + approval), `docs/27_05_reasoning_runtime_roadmap.md` §3 (reward log / Phase 4), phase1-wiring Slice 4 (human-confirm write-back gate), `docs/research/gap-tool-map.md` (deterministic rule-induction for failure→constraint).
