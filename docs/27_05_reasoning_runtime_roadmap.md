# Reasoning Runtime — Roadmap & Decision Ledger

**Status:** Living roadmap. Decisions here are LOCKED unless explicitly revisited with new evidence.
**Date:** 2026-05-27
**Companion:** [Phase 1 — Evidence-Ranked Hypotheses: Locked Contract](./27_05_phase1_evidence_hypotheses_contract.md)

**Purpose:** capture the architecture and the *reasons behind it* — including what we rejected and why — so these discussions are not re-litigated every time a new reasoning paper or tool appears. If a proposal matches something in the **Rejected-Ideas Ledger (§5)**, the burden is on the proposer to show what changed, not to re-argue from scratch.

---

## 1. North-star principles

1. **CHIPS is a deterministic compiler, not a model runtime.** It compiles evidence, constraints, rankings, and contracts. The frontier sidecar agent (Claude Code / Codex) does the generation/reasoning. CHIPS never runs a local generation model and never reasons at prompt time.
2. **Reliability ordering: `verification > grounded evidence > generation`.** Better generation (evidence, causal grounding) lowers the *cost* of verification; verification is what actually makes results reliable. This is the backbone everything else hangs off.
3. **The compounding flywheel is the point.** Every approach must close a return edge into durable constraint memory (`cortex_constraints`), or the system stays stateless and relearns the same failures. Subagents don't share a context window — they share the CHIPS sidecar's store. Durable memory lives there, never in any agent's context.
4. **Local-first AI; simplicity as discipline.** Every component not added is a failure mode avoided. New stores, new services, new DSLs, new model-training programs must each prove necessity against the existing Postgres + MCP + Ollama surface.
5. **Determinism wherever the stack allows it.** The host stack (GoRules, DBOS, OTel baggage/spans, x-headers, tree-sitter/ts-morph) is already deterministic and machine-readable. The job is to route those signals into the brief — not to re-encode them into a bespoke language.

---

## 2. The three reasoning approaches (how they layer)

```
constraint memory (Phase 0)  ─────────────────────────────────────────┐
        │ grounds                                                      │
        ▼                                                              │ write-back:
 evidence bundle + hypothesis contract + deterministic ranking         │  survivors → reinforce
   = "verifier-guided multi-hypothesis search"        (Phase 1, then 3)│  pruned-wrong → candidate
        │ enrich rich incidents                                        │  known_issue (human-confirmed)
        ▼                                                              │
 per-incident causal evidence path                          (Phase 2)  │
        │ for high-assurance paths                                     │
        ▼                                                              │
 generate-and-test prune (the verifier)                     (Phase 3) ─┘
        │ produces the reward log
        ▼
 offline policy tuning / RL                                 (Phase 4)
```

**(A) Verifier-guided multi-hypothesis search** — base approach. CHIPS emits a structured evidence bundle + a strict hypothesis contract; the agent generates N hypotheses citing evidence IDs; CHIPS scores them deterministically (coverage − contradiction); the top 1–2 are verified. Reliability comes from the *verify* step, not the generation. Details: Phase 1 contract doc.

**(B) Per-incident causal evidence path** — the stack's differentiated advantage. Given a correlation/trace ID, assemble the *failing subgraph* on demand — spans + DBOS workflow steps + fired GoRules + code symbols (via structural/graphify), joined by baggage/correlation IDs. **Ephemeral per incident — NOT a persistent graph DB** (see §5). Adds `proximity` signal to hypothesis ranking.

**(C) RL for policy improvement** — see §3. Tunes *which* hypotheses get generated/ranked/verified and *when to stop*. Offline, over the reward log Phase 3 produces. Never model fine-tuning, never online.

These are **one loop, not three alternatives.** The return edge into `cortex_constraints` (pruned-wrong → candidate known_issue; verified-correct → reinforce / retire) is what makes "stop repeating mistakes" true rather than aspirational.

---

## 3. RL — the durable position

This section exists so the RL conversation does not recur. Read it before proposing any RL work.

### 3.1 There are two different "RL"s. We do one and not the other.

| | RL-to-train-a-model | RL/bandit-to-tune-a-policy |
|---|---|---|
| Examples | SWE-RL (GRPO-fine-tunes Llama-3-70B), HRM, NAR | tune `ranker` weights, `governor` thresholds, `w_cov`/`w_con`, stop/continue |
| Produces | model weights | config weights |
| Cost | GPUs, training infra, MLOps, eval harness | offline replay over logs |
| Verdict for CHIPS | **Never** (near/medium term) | **Yes** — the real target |

**Why never train a model:** SWE-RL's own headline is `Llama3-SWE-RL-70B = 41.0%` on SWE-bench Verified (vs 36.2% SFT baseline). That is *below* what the frontier sidecar agent already delivers. RL-fine-tuning a local model would spend a training program to build a weaker competitor — negative value, and it violates principle #1 (CHIPS stays a deterministic compiler).

### 3.2 The SWE-RL principle (what we actually take from it)

SWE-RL's real contribution is its **reward design**, not its recipe: a **cheap, automatic, rule-based reward** is enough to drive useful learning at scale. Concretely, SWE-RL rewards a predicted patch by `difflib` **sequence similarity to the oracle patch** (format penalty otherwise) — **no execution environment required** — trained on GitHub PR data.

Transferable lesson for CHIPS: the analogous cheap automatic reward is the **verification outcome** (tests pass/fail from Phase 3) and/or **similarity to the eventually-accepted fix**. The GRPO-on-70B machinery is *not* transferable; the reward-design discipline is.

### 3.3 CHIPS already runs a primitive policy-RL

`learning.py` is a feedback-weighted online adjustment — `outcome_weights = {accepted: +0.05, rejected: −0.10, ignored: 0.0}` adjusting memory confidence. That is a contextual bandit in spirit. "RL for policy" is therefore **formalizing and extending the loop that already exists**, not importing a new paradigm.

### 3.4 The reward is the gate — RL is causally dependent on the verifier

The verifier (Phase 3) **is** the reward generator. Without it, the only reward is sparse human accept/reject — data-starved on an internal tool. So RL is not merely "after" the near-term work; the near-term work (Phase 1–3) is its **prerequisite**, because it produces the reward log. **No verifier → no useful RL.**

### 3.5 Form factor: offline, never online

- Internal tool, modest volume → **online live exploration in production briefs is reckless** (degrades real briefs while exploring).
- The path: **instrument** (log policy decisions + rewards) → **Offline Policy Evaluation** ("what would outcomes have been under weights W′?") → **contextual bandit** if OPE shows headroom → **sequential RL** only if single-step bandit plateaus *and* trajectory-level reward exists.
- A well-tuned bandit + good reward often beats full RL at a fraction of the cost. **Prove the gap with OPE before paying for RL machinery.**
- Always ship tuned **weights as config**, validated on held-out logs.

### 3.6 What RL requires *now*

Nothing to build — only the logging hook (Phase 1 contract §G): persist `weights_used` + `verification_reward` per brief. Cost now ≈ zero; skipping it makes offline RL impossible later without re-instrumentation.

---

## 4. Phased roadmap & dependencies

| Phase | Deliverable | Status | Depends on |
|---|---|---|---|
| **0** | Anti-regression constraint memory (`cortex_constraints`): scoped, manual add/retire, force-injected into `hard_constraints`/`forbidden_edits` as a dynamic policy layer beside the static `PolicyLoader` | **Substrate implemented** (`c79bd74`, migration 007): `ConstraintRepository` + `assemble_*` + build-time injection + governor/reranker/structural. **Gap:** no MCP add/retire surface yet — constraints enter only via SQL/migration (L9, D4) | — |
| **1** | Evidence-ranked hypotheses: stable evidence IDs, `EvidenceBundle`, `Hypothesis` contract, deterministic coverage−contradiction ranking, write-back review queue | **Partially landed.** Pure layer committed (`86caf4d`): `EvidenceBundle`/`Hypothesis`/ranking + `evidence.finding_evidence_id`. **Pending:** §A finding-ID wiring (still positional `finding:{index}` — L7, D2), `EvidenceBundle` derivation in `build()`, `cortex_submit_hypotheses`, write-back review queue ([doc](./27_05_phase1_evidence_hypotheses_contract.md)) | Phase 0 |
| **2** | Per-incident causal evidence path (ephemeral); populates `rule:`/`span:` evidence; adds `proximity` to ranking | Planned | Phase 1; reuses `runtime.py`, `workflow.py`, structural/graphify |
| **3** | Verifier-guided generate-and-test (gated to high-assurance paths); write-back of survivors/pruned to `cortex_constraints` | Planned | Phase 1; worktree isolation, test/rule selection |
| **4** | Offline policy tuning: OPE → contextual bandit on ranking/governor/stop-continue; reward = verification outcome; ship weights as config | Planned | Phase 3 (reward source) + §3.6 logging |
| **Watchlist** | See §5 | No build | proven gap only |

**Build-cost order:** 0 < 1 < 2 < 3 < 4. **Reliability order:** verification (3) > grounding (1, 2) > generation. These are different orderings — do not conflate.

---

## 5. Rejected-Ideas Ledger (do not re-propose without new evidence)

Each was seriously evaluated and cut. The reason is recorded so it isn't re-argued.

| Idea | Verdict | Reason |
|---|---|---|
| **GRAM** (Generative Recursive Reasoning) | **Reject** | 2026 preprint, **no released code**; a latent-variable VAE trained on Sudoku/MNIST/constraint-satisfaction. Not a code-reasoning controller. The spec's "seed a search using Serena snapshots as heuristic" describes something that does not exist. |
| **Zerolang transpiler** (encode GoRules/traces into Zerolang) | **Reject** | Zerolang (vercel-labs, v0.1.4, "not production-ready, expected security vulns") is a *general-purpose programming language*, not an interchange format. Category error. Its one good idea — *compiler emits structured JSON for agents* — argues **for** feeding GoRules JDM JSON + OTLP JSON (training-distribution-friendly), **against** a bespoke DSL. |
| **HRM / TRM** (Hierarchical/Tiny Recursive reasoning) | **Watchlist** | Latent-reasoning architectures (HRM = OpenReview `d0e11…` / arXiv 2506.21734, code at sapientinc/HRM). Wrong layer — prompt-time reasoning belongs to the frontier agent, not a sidecar. Revisit only on a proven, quantified gap. |
| **Neural Algorithmic Reasoning** (arXiv 2406.09308) | **Watchlist** | Foundational research (nets imitating classical algorithms, OOD generalization). Not applicable to retrieval/ranking policy tuning. |
| **RL fine-tuning a local model** (SWE-RL recipe) | **Reject** | Builds a model weaker than the frontier sidecar (41% < frontier). Negative value; violates "CHIPS stays a deterministic compiler." Take the *reward principle* (§3.2), not the recipe. |
| **Online / live RL in production** | **Reject** | Degrades real briefs while exploring. Offline OPE/bandit only (§3.5). |
| **`.reasoning/` flat-file state store** | **Reject** | Forks truth from the Postgres-backed system (briefs/outcomes/learning/constraints). Second source of truth, not tenant-scoped, drifts vs DB. State lives in Postgres / AgentMemory. |
| **DBOS shadow-simulation runtime** | **Reject (early)** | DBOS is a durable workflow engine, not a hypothetical-world sandbox. "Does the change pass tests?" = a git-worktree test run. Simple validation first; a bespoke shadow runtime is the wrong early investment. |
| **Standalone `reason` CLI** | **Reject** | The MCP tool surface already *is* the interface (`--compile` = `cortex_brief`). A parallel CLI duplicates it. |
| **Persistent causal graph DB** | **Defer** | Premature. The failing graph is assembled **per-incident, ephemeral** (Phase 2). A persistent graph (ingestion, staleness, storage, source-of-truth) is justified only for cross-incident recurrence analytics, after per-incident assembly proves insufficient. |
| **Semantic (prose) contradiction scoring** | **Defer** | v1 contradiction is **structural** (touched paths/symbols/declared violations vs constraint targets) to stay deterministic. Semantic = optional LLM-judge enrichment behind a flag, never default. |

---

## 6. References

| Ref | What it is | Bucket |
|---|---|---|
| SWE-RL — arXiv 2502.18449 (Meta) | RL on open software evolution; rule-based reward = patch similarity to oracle, no execution env; Llama-3-70B + GRPO; 41.0% SWE-bench Verified | In-scope **for its reward-design lesson only** (§3.2) |
| HRM — arXiv 2506.21734 / OpenReview `d0e11…` (Sapient Inc) | Hierarchical latent reasoning architecture; code at github.com/sapientinc/HRM | Watchlist |
| Neural Algorithmic Reasoning — arXiv 2406.09308 | Nets imitating classical algorithms; OOD generalization | Watchlist |
| GRAM — ahn-ml.github.io/gram-website | Generative Recursive Reasoning (VAE for Sudoku/MNIST); code "coming soon" | Rejected |
| Zerolang — github.com/vercel-labs/zerolang | Experimental general-purpose language; v0.1.4; not production-ready | Rejected (wrong abstraction) |
