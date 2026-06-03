# open-bias — Decision-Grade Assessment for CHIPS CORTEX

**Author:** Research engineering pass (Claude, co-reviewed with Codex round 1 + round 2)
**Date:** 2026-06-02
**Scope:** `open-bias/open-bias` (Apache-2.0, v0.4.1 beta, Python) evaluated against CHIPS's actual architecture (deterministic context compiler; sidecar to coding agents; Python 3.13; PolicyLoader + `cortex_constraints` + hard_constraints/forbidden_edits; pgvector + flashrank + graphify + structural; Ollama local-first; Postgres/SQLAlchemy/Alembic; FastMCP "chips-cortex"). Priorities, in order: **(1) determinism, (2) local-first, (3) simplicity, (4) sidecar-not-inline architectural identity.**

Sources cited inline are the actual open-bias README / product site fetched during this assessment (2026-06-02). Companion repos (re_gent, sigmap) covered briefly in §6 for completeness; this note's subject is open-bias.

Sibling research note (same series, same verdict-grammar): `docs/research/openkb-forge-assessment.md`.

---

## 1. Executive Summary

**open-bias — Verdict: BORROW THE DETERMINISTIC TIER + COMPILATION + TRACE; REJECT THE LLM-JUDGE + PROXY INTERCEPTION. Do NOT adopt as a dependency.**

open-bias (`open-bias/open-bias`, Apache-2.0, v0.4.1, 12 May 2026, Python) is a **runtime policy-enforcement proxy** that sits *between* an app and an LLM provider (`openbias serve` → `http://localhost:4000/v1`, drop-in OpenAI-compatible). Rules are authored in plain-English `RULES.md`, run through a **`RULES.md → Compiler → engine config`** pipeline, and evaluated by one of **four pluggable engines** (`judge` = LLM rubric scorer, `nemo` = NVIDIA NeMo Guardrails, `fsm` = deterministic state machine [experimental], `llm` = LLM classification [experimental]). Enforcement is tiered into three modes — **BLOCK** (stop request, return error), **INTERVENE** (modify next turn / replay response), **SHADOW** (log & pass through). It emits **JSONL traces + OpenTelemetry**, and supports a **trace capture → replay → compare → review → approval** loop. It is **fail-open by design** (the proxy never blocks the hot path; the judge runs in a background `asyncio.Task`, "0ms async deferred intervention").

The round-2 reframing is correct: **CHIPS's biggest unmet need is enforcement + audit + verifier-fed write-back, not more retrieval.** open-bias targets exactly that layer. But two things disqualify it as a *dependency* while making it valuable as a *pattern source*:

1. **Architectural-identity collision.** CHIPS is a **sidecar context-compiler** — its enforcement is *compile-time* (constraints shape the brief **before** the agent acts; it never intercepts a model call). open-bias's BLOCK/INTERVENE are *runtime proxy interception* — they sit at the model boundary and mutate/block the request stream. Adopting that path would change CHIPS from advisory to inline. That interception belongs to whatever **consumes** the CHIPS brief (the host agent, or a peer runtime), not to CHIPS itself.
2. **The judge tier is non-deterministic** — but, crucially, **only one engine of four is.** open-bias is *not* monolithically stochastic. Its `fsm` engine and its hard-limit checks are deterministic; the `judge`/`llm` engines are not. So the borrow line runs *inside* open-bias, not around it.

**Net:** borrow (a) the `RULES.md → compiler → engine-config` *compilation* idea (CHIPS already half-has this in PolicyLoader/`cortex_constraints` — open-bias shows the compile-the-policy step), (b) the **deterministic tier** (FSM / hard-check enforcement) as the model for CHIPS's own constraint enforcement, and (c) **SHADOW + JSONL trace + replay/approval loop**, which map almost 1:1 onto CHIPS's nearest real gaps (Slice A5a auditability, the Phase-4 reward log, and the human-confirm write-back gate). Reject the LLM `judge` engine (use CHIPS's locked **deterministic contradiction-flagging** instead) and the proxy interception (outside the sidecar boundary). **No code dependency; beta maturity (v0.4.1, ~123★) argues for borrow-not-depend regardless.**

---

## 2. open-bias Deep-Dive (verified against README + product site)

### 2.1 What it is and how it integrates

- **Shape:** standalone HTTP proxy (`openbias serve`, listens `:4000/v1`), drop-in for any OpenAI-compatible client (`OpenAI(base_url="http://localhost:4000/v1", ...)`). `pip install openbias`. Architecture exposes `PRE_CALL` / `POST_CALL` hooks.
- **Providers:** Anthropic, OpenAI, Gemini, generic via `base_url` (`ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY`). Ollama only *inferred* from "any provider" — **no explicit Ollama-native guarantee** in the README.
- **License:** Apache-2.0 (clean to vendor/borrow with attribution). **Maturity: v0.4.1, May 2026, beta, single-org, ~123★.**

### 2.2 The rule/policy model — the genuinely interesting part

- Rules are **plain Markdown** in `RULES.md` (e.g. *"Maximum discount is 15%. Never reveal internal pricing, cost basis, or margin data."*).
- A **compiler** turns `RULES.md` → **engine config**; ships a starter `RULES.md` and *"synthesizes a default evaluator — no config file needed."* Optional `openbias.yaml` for advanced cases.
- This is the load-bearing idea for CHIPS: **policy-as-prose compiled into an executable enforcement config.** CHIPS already has the policy *brain* (PolicyLoader static layer + `cortex_constraints` dynamic layer, merged in locked precedence, restrictive-wins) but its constraints are consumed as *context to shape a brief*, not *compiled into an enforcement artifact with a verdict per rule*.

### 2.3 The four engines — where the determinism line actually runs

| Engine | Mechanism | Deterministic? | CHIPS relevance |
|---|---|---|---|
| `judge` | Sidecar LLM scores response against rubrics (tone/safety/instruction-following), aggregate score → action | **No** (LLM, model/temp-dependent) | **Reject** — collides with priority #1; CHIPS's answer is deterministic contradiction-flagging |
| `nemo` | NVIDIA NeMo Guardrails | Partly (Colang rules deterministic; embeddings/LLM steps not) | Heavyweight dep; skip |
| `fsm` | Deterministic state machine (experimental) | **Yes** | **Borrow the shape** — maps onto CHIPS hard_constraints/forbidden_edits |
| `llm` | LLM classification (experimental) | **No** | Reject (same reason as `judge`) |

Plus a **tiered split** stated on the product site: *"Hard limits like discount caps get instant, deterministic checks. Nuanced policies like tone of voice get AI-powered judgment."* → open-bias itself separates a deterministic hard-constraint tier from a probabilistic nuance tier. **CHIPS only wants the first tier**, and already has its substrate (`hard_constraints`, `forbidden_edits`).

### 2.4 Enforcement modes — semantics and the sidecar mismatch

- **BLOCK** — critical violation → `WorkflowViolationError`, request halted, error returned. *Runtime interception. Outside CHIPS's sidecar boundary.*
- **INTERVENE** — non-critical violation → correction queued for the next turn ("modify next turn or replay resp"). *Runtime, stateful across turns. Outside CHIPS's boundary; this is the host agent's job.*
- **SHADOW** — log & pass through; response returns immediately, judge evaluates in a background `asyncio.Task`, violations applied as interventions next turn. *Observe-without-acting. **This is the one CHIPS can use** — it is telemetry, not interception.*

**Borrow boundary, stated sharply:** SHADOW (observe + record) is inside CHIPS's identity; BLOCK/INTERVENE (intercept + mutate the model stream) are not. Codex round 2 recommended borrowing "BLOCK / INTERVENE / SHADOW" — this note **splits that trio**: borrow SHADOW + the rules-compilation step + the trace/replay loop; explicitly **reject BLOCK/INTERVENE** as belonging to the brief *consumer*, not the compiler.

### 2.5 Trace / audit output — the closest fit to a real CHIPS gap

open-bias emits **JSONL traces + OpenTelemetry**, each carrying request + evaluator verdict + enforcement decision, and supports **capture → replay → compare → review → approval**. CHIPS already shipped Prometheus + OTel on the brief path (commit `5764757`) and a DuckDB brief-history export (`0205972`). open-bias's *rule-by-rule pass/fail verdict record* and *human approval flow* are precisely the shapes CHIPS's **Slice A5a (auditability)** and **write-back human-confirm gate** (phase1-wiring-plan Slice 4: *no constraint activated without human confirm*) need. **This is the highest-value borrow.**

---

## 3. Head-to-Head vs CHIPS

| Dimension | CHIPS today | open-bias | Implication |
|---|---|---|---|
| **Where it acts** | Compile-time (shapes brief before agent acts) | Runtime (intercepts model calls) | Architectural-identity collision; borrow patterns, not the proxy |
| **Policy authoring** | PolicyLoader (static) + `cortex_constraints` (dynamic, SQL/migration-entered) | `RULES.md` plain-English → **compiler** → engine config | **Borrow the compile-the-policy step** — CHIPS lacks an explicit compiler |
| **Enforcement determinism** | Deterministic precedence merge (restrictive-wins) | Tiered: deterministic hard-checks + `fsm`; non-deterministic `judge`/`llm` | Borrow the deterministic tier; reject the LLM tier |
| **Audit** | OTel + Prometheus + DuckDB export; A5a (brief auditability) NOT yet built | JSONL per-rule verdict trace + replay/approval | **Borrow trace+approval shape into A5a** |
| **Verifier / reward** | Phase 3 gated verifier + Phase 4 reward log (`weights_used`/`verification_reward` cols exist, unpopulated) | SHADOW captures violations for "self-improvement" | SHADOW trace = candidate reward-log feed |
| **Local-first** | Ollama-direct, cloud barred in core path | Cloud providers default; Ollama only inferred | open-bias as-is fails priority #2 → another reason not to depend |
| **Maturity** | Infra under deliberate TDD | v0.4.1 beta, ~123★, single-org | Borrow-not-depend |

**The key correction to "open-bias is the missing execution muscle":** CHIPS does not *want* execution muscle at the model boundary — that would make it an inline interceptor and break the sidecar thesis. What CHIPS wants is the **compile-policy-to-verdict** step and the **observe-and-record** step. open-bias demonstrates both; it also demonstrates the interception step, which CHIPS should leave to the brief's consumer.

---

## 4. Mapping onto CHIPS's Actual Slices

The reason to write this note *now* (vs park it) is that open-bias's borrowable pieces line up with the **nearest** roadmap slices, not distant ones:

- **Slice A5a — auditability (Codex #4, next product slice after A4).** open-bias's **rule-by-rule pass/fail verdict trace** + **replay/compare/approve** loop is a concrete reference design for "explain *why* the brief recommended what it did." Borrow: a per-brief verdict record (which constraints fired, which evidence supported each, restrictive-wins decisions) emitted as a JSONL/OTel artifact alongside the existing DuckDB export.
- **Write-back human-confirm gate (phase1-wiring Slice 4).** open-bias's **approval flow** is the same invariant CHIPS already locked: *no constraint activated without human confirm (`cortex_add_constraint`)*. Borrow the capture→review→approve UX shape.
- **Deterministic contradiction-flagging (locked Track-C backlog item).** This is CHIPS's **deterministic replacement** for open-bias's LLM `judge`. open-bias validates the *need* (catch policy violations / conflicts) and the *anti-pattern* (don't do it with an LLM judge if you value determinism). Borrow the goal; keep CHIPS's structured/assertion-level comparison.
- **Phase 4 reward log (`weights_used`/`verification_reward`).** open-bias's **SHADOW trace** (violations observed without acting) is a clean conceptual feed for the reward log — observe outcomes, record them, never act inline.
- **NOT a near-term fit:** BLOCK/INTERVENE interception (no CHIPS slice; outside boundary), `nemo`/`judge`/`llm` engines (determinism/local-first fails), the proxy server (operational surface, priority #3).

---

## 5. Prioritized Recommendations

| # | Recommendation | Type | Rationale | Blast radius | Determinism check | Local-first check |
|---|---|---|---|---|---|---|
| 1 | **Borrow the per-rule *verdict trace + replay/approve* shape into Slice A5a (brief auditability).** Emit, per brief, which constraints fired, the evidence supporting each, and the restrictive-wins decisions — as a JSONL/OTel artifact beside the DuckDB export. | Borrow (open-bias trace/approval) | A5a is the next real slice after A4; open-bias is a ready reference design for exactly this. | Med (new audit artifact on brief path; ranking/assembly unchanged) | **PASS** — recording deterministic decisions | **PASS** — local artifact |
| 2 | **Borrow the `RULES.md → compiler → engine config` *compilation* idea** — add an explicit compile step that turns PolicyLoader + `cortex_constraints` into a single resolved, inspectable enforcement artifact per scope. | Borrow (open-bias compiler) | CHIPS has the policy brain but no explicit compile-to-artifact step; this strengthens A5a auditability and the merge gate (A5c). | Med (new compile pass over existing constraint layers) | **PASS** — pure deterministic merge | **PASS** |
| 3 | **Treat open-bias's `fsm`/hard-check tier as the model for CHIPS constraint *enforcement* (deterministic only).** Map onto existing `hard_constraints`/`forbidden_edits`. | Borrow (concept) | Confirms CHIPS's deterministic-tier direction; nothing to adopt, validates design. | Low (design) | **PASS** | **PASS** |
| 4 | **Use SHADOW (observe-without-acting) as the conceptual feed for the Phase-4 reward log;** capture violations/outcomes, never intercept. | Borrow (concept, defer to Phase 4) | Aligns with `weights_used`/`verification_reward` population; respects sidecar boundary. | Low (Phase-4-shaped) | **PASS** — logging only | **PASS** |
| 5 | **Reject open-bias's LLM `judge`/`llm` engines; keep CHIPS's locked deterministic contradiction-flagging instead.** | Skip + Borrow goal | LLM judgment is non-deterministic (priority #1). open-bias validates the need, not the method. | N/A | **FAIL** for the judge engine — that's why it's rejected | open-bias judge defaults cloud → also **FAIL** |
| 6 | **Reject BLOCK/INTERVENE proxy interception as outside CHIPS's sidecar boundary** — that layer belongs to the brief *consumer* (host agent / peer runtime). | Skip | Adopting it converts CHIPS from advisory to inline; breaks the thesis. | N/A | N/A | N/A |
| 7 | **Do NOT add open-bias as a runtime dependency.** | Skip | Beta (v0.4.1), cloud-default, proxy operational surface (priority #3). Value is in 3 isolated patterns, re-implementable in-stack. | N/A | — | — |
| 8 | **re_gent — run alongside as a dev-workflow companion (agent-action provenance); do NOT embed.** | Defer/companion | Adjacent (records *what the agent did*), not CHIPS's job (*why the brief recommended X*). Good substrate for promoting failures → constraints later. | N/A | — | — |
| 9 | **sigmap — borrow the deterministic *signature-map as fallback context* idea only; skip the tool.** | Borrow (concept) | Useful as a low-cost deterministic evidence projection when embeddings/rerank unavailable; tool overlaps CHIPS retrieval. | Low (concept) | **PASS** (signature maps are deterministic) | **PASS** |

---

## 6. Companion Repos (brief — not this note's subject)

- **re_gent** — agent-action provenance / prompt-to-line blame / audit trail / reward-log substrate. **Companion, not dependency** (Go sidecar; integrates as a data source CHIPS *ingests*, not a library it imports). Distinct from A5a: re_gent records *what the agent did*; A5a explains *why the brief recommended what it did*. Adjacent systems. Best long-term fit: promoting observed failures into constraints / the Phase-4 reward log. **Verdict: run alongside if useful; do not embed.**
- **sigmap** — ships an MCP server (`sigmap --mcp`, 9 tools) + emits ranked file lists / compressed `.cursorrules`/`CLAUDE.md`. **Overlaps CHIPS's own retrieval+compression path head-on** → replace-or-don't-adopt. Salvageable idea: **compact deterministic signature maps as a fallback evidence projection** when embeddings/rerank are unavailable. **Verdict: borrow the signature-map idea; skip the tool.**
- **dirac** — explicitly rejects MCP (README: *"Native Tool Calling Only… MCP is not supported"*; *"Oh, and no MCP"*); standalone CLI / VS Code extension, **not an importable library**. Architecturally incompatible with MCP-native CHIPS. **Verdict: reference architecture for edit-precision ideas only; not a dependency candidate.**
- **agent-desktop** — out of scope for CHIPS's current gaps. **Verdict: defer.**

---

## 7. Spike Plan (time-boxed; ~half-day, do NOT wire into product code)

The goal of the spike is to extract the three borrowable shapes (verdict-trace, policy-compile, SHADOW-feed) as **design inputs to Slice A5a**, not to integrate open-bias. Strict no-dependency, no-product-edit.

**Pre-spike (cheap, before any code):**
- Confirm CHIPS's A5a contract surface: where in `builder.build()` the constraint-firing + restrictive-wins decisions are made, and where the DuckDB/OTel export hooks already sit (reuse, don't duplicate). *(Search via `/g2s2` only — never broad grep.)*
- Confirm the write-back human-confirm gate's current state (`cortex_add_constraint` path) so the borrowed approval-flow shape matches the existing invariant.

**Spike steps (isolated; a scratch worktree or `docs/` scratchpad, never the product tree):**
1. **Read the open-bias modules that matter** (Apache-2.0, attribution if any snippet is quoted): the `RULES.md` compiler path, the `fsm` engine (deterministic tier), and the trace/JSONL + approval-flow code. Capture the *data shapes*, not the code — what a per-rule verdict record contains, what the approval state machine's states are.
2. **Sketch the CHIPS verdict-trace schema** for A5a: per brief → `[{constraint_id, fired: bool, supporting_evidence: [evidence_id], decision: "restrictive-wins"|..., source_layer: "policy"|"learned"}]`. Reuse existing `find:<content-hash>`/`con:` ID schemes. This is the concrete A5a artifact proposal.
3. **Sketch the policy-compile step**: a deterministic function `compile_policy(scope) -> ResolvedPolicy` that materializes PolicyLoader + `cortex_constraints` into one inspectable artifact (the thing A5a traces against). Note overlap with the planned `PolicyAssembler` from the A3 strangler-fig decomposition — this may *be* that component's output.
4. **Map SHADOW → reward log**: one paragraph on how observed-but-not-acted outcomes would feed `verification_reward` at Phase 4, respecting the sidecar boundary (record only, never intercept).
5. **Write the decision**: which of Recs #1–#4 become real slices, in what order relative to A5a, and what is explicitly rejected (#5/#6).

**Exit criteria:** a short A5a design addendum (verdict-trace schema + compile-step sketch) appended to or referenced from the A5a slice doc. **No product code, no dependency added, no commit beyond the design doc.**

**Determinism gate for the spike:** every borrowed shape must pass the determinism check in §5. If a borrowed idea can only be made to work with an LLM judge, it is rejected, not adapted.

---

## 8. Open Questions / Validate Before Committing

1. **A5a scope overlap.** Does the borrowed verdict-trace belong *inside* A5a, or is it a separate slice feeding A5a? Decide before A5a starts so the slice boundary stays surgical.
2. **Compile-step vs A3 `PolicyAssembler`.** The policy-compile borrow (Rec #2) likely overlaps the planned `PolicyAssembler` component in the A3 BriefBuilder decomposition. Resolve whether it's one component or two before building either — avoid a duplicate compile path.
3. **Ollama-locality of any borrowed evaluation.** Anything borrowed that *evaluates* (not just records) must be deterministic + local. open-bias defaults to cloud judges; CHIPS must not inherit that. The only borrowed *evaluation* is the deterministic tier — confirm no LLM creeps into the trace path.
4. **re_gent ingestion contract (if ever pursued).** If failures-→-constraints via re_gent is pursued at Phase 4, define the data-source schema CHIPS ingests; it is a boundary, not an import.
5. **License hygiene.** open-bias is Apache-2.0; if any snippet is vendored, retain notice/attribution. Same for sigmap if the signature-map idea is implemented from its source.
6. **Sequencing vs A4.** This note is research, not a slice. A4 (flag experimental layers OFF) remains the next *product-code* move; A5a (where these borrows land) is the slice after. Nothing here reorders A4.

---

### Source references

- open-bias: `open-bias/open-bias` README (Apache-2.0, v0.4.1, 12 May 2026) — `openbias serve` → `:4000/v1`; `RULES.md → Compiler → engine config`; engines `judge`/`nemo`/`fsm`/`llm`; modes BLOCK ("stop req return error") / INTERVENE ("modify next turn or replay resp") / SHADOW ("log & pass through", background `asyncio.Task`, "0ms async deferred intervention"); `PRE_CALL`/`POST_CALL` hooks; `openbias.yaml`; providers Anthropic/OpenAI/Gemini; JSONL traces + OpenTelemetry; capture→replay→compare→review→approval; fail-open by design.
- open-bias product site (`openbias.dev`): "Self-improving Agent Reliability"; tiered model — *"Hard limits … instant, deterministic checks. Nuanced policies … AI-powered judgment"*; "Judge LLM, NeMo, FSM — pick per concern"; "Full Audit Trail … rule-by-rule pass/fail results"; "1 line change · 0ms (async default)."
- Companion repos (verified earlier this session): dirac README ("Native Tool Calling Only … MCP is not supported"); sigmap (`sigmap --mcp`, 9 tools; ranked file lists + compressed context).
- CHIPS internal: `docs/research/openkb-forge-assessment.md` (sibling note); `docs/31_05_codex_remediation_plan.md` (#4 auditability, slice order A4→A3→A5a); phase1-wiring-plan Slice 4 (human-confirm write-back gate); roadmap Phase 3/4 (verifier + reward log).
