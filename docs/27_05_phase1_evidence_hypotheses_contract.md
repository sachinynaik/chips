# Phase 1 — Evidence-Ranked Hypotheses: Locked Contract

**Status:** LOCKED (design). No code until this is reviewed.
**Date:** 2026-05-27
**Depends on:** Phase 0 — anti-regression constraint memory (`cortex_constraints`), designed and locked.
**Principle:** CHIPS stays a *deterministic compiler*. It emits evidence + a hypothesis contract + deterministic scoring. The frontier sidecar agent (Claude Code / Codex) generates hypotheses. CHIPS never runs a local generation model and never does prompt-time reasoning.

Reliability ordering (not build-cost ordering): **verification > grounded evidence > generation.** This phase builds the *grounding + scoring* layer; verification (generate-and-test) is a later phase and is the reward source for any future RL.

---

## 0. Scope of this contract

This document locks five interfaces that become load-bearing the moment an agent cites an evidence ID:

1. Evidence ID scheme (§A)
2. `EvidenceBundle` / `EvidenceItem` (§B)
3. `Hypothesis` (§C)
4. Deterministic ranking + contradiction semantics (§D, §E)
5. Write-back rule + review-queue payload (§F)

Plus two cross-cutting items: RL-readiness logging (§G) and the `cortex_constraints` additions Phase 1 requires (§H).

Out of scope for v1: §J.

---

## A. Evidence ID scheme — the contract

**Stability rule (non-negotiable):** every evidence ID is `<kind>:<natural-key>`, where the natural key is derived from the evidence's *identity/content*, **never** from position or compile-time ordering. The same evidence yields the same ID across every compile and into write-back.

| Kind | ID format | Natural key | Phase 1 status |
|---|---|---|---|
| constraint | `con:<uuid>` | `cortex_constraints.id` | supported |
| memory | `mem:<uuid>` | memory row id | supported |
| diff | `diff:<sha>` | commit sha | supported |
| finding | `find:<sha256-12>` | **content hash** of normalized finding fields | supported |
| structural | `struct:<path>#<symbol>` | AST symbol identity | supported |
| workflow | `wf:<workflow_uuid>` | `dbos.workflow_status.workflow_uuid` | supported |
| rule | `rule:<gorule_id>` | GoRules decision/rule id | **reserved** (not populated v1) |
| span | `span:<trace_id>/<span_id>` | OTel ids | **reserved** (not populated v1) |

**Supported evidence kinds for ranking in Phase 1:** `constraint, memory, diff, finding, structural, workflow`.
**Reserved but not yet populated:** `rule, span` — the ID scheme is fixed now so Phase 2 (per-incident causal path) populates them without a contract change. Consumers must treat `rule`/`span` as absent in v1.

**Mandatory prereq fix:** `builder.py` currently assigns findings `f"finding:{index}"` (positional). This violates the stability rule and **must** change to `find:<content-hash>` before anything else in this phase. Content hash = `sha256` of the normalized finding fields (e.g. for security: `test_id|file|line|message`), truncated to 12 hex chars.

**Per-kind normalization (LOCKED 2026-05-31).** The content hash is computed over a normalized
dict built from each finding's *identity-bearing* fields only — volatile metrics (`severity`,
`confidence`, `changed_lines_missing`, scores) are excluded so a re-tune of those does not mint
a new ID. Every normalized dict carries a `"kind"` discriminator (the finding category) so two
different kinds cannot collide on `find:`. The hash is `evidence.finding_evidence_id(normalized)`.

| Soft finding kind | Normalized fields (besides `kind`) | Notes |
|---|---|---|
| `security` (LOW) | `test_id, file, line, message` | per the §A example; `severity` excluded |
| `dead_code` | `type, name, file` | `confidence` (%) excluded — volatile |
| `api_surface` | `change_type, symbol, details` | `details` first to drop if it proves brittle |
| `clones` | `files` (= `sorted([file_a, file_b])`), `lines` | pair sorted so A/B order can't flip the ID |
| `type_errors` | `code, line, message` | ⚠️ extractor does not capture `file` today; add later in harvester (does not change existing IDs since `kind`+`code`+`line`+`message` stay fixed) |
| `uncovered_changes` | `path` | one entry per path; the missing-line count is excluded |

Hard findings (security HIGH/MEDIUM, architecture violations) become `hard_constraints` text, not
`EvidenceItem`s, so they carry no `find:` ID in v1. Only **soft** findings (which become
`SoftContextItem`s) are assigned stable `find:` IDs.

---

## B. EvidenceBundle / EvidenceItem (`models.py`)

A typed, stable-ID **projection** of what `BriefBuilder.build()` already assembles — the normalized evidence model, realized as dataclasses, no DSL.

```python
@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str            # "<kind>:<natural-key>" — stable across compiles
    kind: Literal["constraint", "memory", "diff", "finding",
                  "structural", "workflow", "rule", "span"]
    label: str                  # compact, stable — for logs / UI / write-back review
    text: str                   # full agent-readable content
    weight: float               # ranker score; constraints carry authority weight 1.0
    constraint_kind: Literal["forbidden", "invariant", "known_issue"] | None = None
                                # set iff kind == "constraint"
    target: dict = field(default_factory=dict)
                                # constraints only: {path?, symbol?, workflow_step?, rule_id?}
    refs: dict = field(default_factory=dict)
                                # provenance: file:line, source_ref, trace_id, workflow_uuid, ...

@dataclass(frozen=True)
class EvidenceBundle:
    bundle_id: UUID                       # == brief_id
    constraints: list[EvidenceItem]       # constraint_kind set; contradiction scored against these
    evidence: list[EvidenceItem]          # citable soft signals
    def by_id(self, eid: str) -> EvidenceItem | None: ...
    def constraint_by_id(self, eid: str) -> EvidenceItem | None: ...  # for declared_violations validation
```

**Two lists, deliberately.** `constraints` is the non-negotiable layer that contradiction is scored against; `evidence` is the citable soft pool. The agent may cite IDs from either. `constraint_kind` and `target` are **first-class fields**, never render-only convention — contradiction logic reads them directly.

`label` examples: `GoRule-104`, `wf:checkout RETRIES_EXCEEDED`, `find: bandit B105 auth.py:42`.

---

## C. Hypothesis schema (agent → CHIPS via `cortex_submit_hypotheses`)

```python
@dataclass(frozen=True)
class Hypothesis:
    hypothesis_id: str                    # agent-assigned label; CHIPS validates/normalizes
    claim: str                            # one-sentence "what is wrong"
    mechanism: str                        # predicted failing mechanism
    cited_evidence: list[str]             # evidence_ids — validated against the bundle
    touched_paths: list[str] = ()         # files the proposed fix would change
    touched_symbols: list[str] = ()       # symbols/methods the proposed fix would change
    declared_violations: list[str] = ()   # constraint IDs the agent KNOWS it would relax
    predicted_checks: list[str] = ()      # tests/assertions that confirm/refute (feeds Phase 3)
    rank_hint: float | None = None        # agent self-confidence — ADVISORY ONLY, never scored
```

**Contract enforcement (surfaced, never silent):**
- A `cited_evidence` ID not present in the bundle → contract violation; reported on the result and excluded from scoring.
- A `declared_violations` entry that is not a **constraint** ID (absent, or an evidence ID whose `kind != "constraint"`) → contract violation; reported.
- `touched_paths` / `touched_symbols` exist specifically to make contradiction deterministic (§E).

---

## D. Deterministic ranking formula

CHIPS ranks hypotheses. The LLM's `rank_hint` is advisory and **never** enters the score. All inputs are structured; no LLM judge.

```
score(h) = w_cov·coverage(h) − w_con·contradiction(h) + w_div·corroboration(h) + w_prox·proximity(h)

coverage(h)      = Σ weight(e) over the SET of UNIQUE valid cited evidence IDs
contradiction(h) = | distinct forbidden/invariant constraints matched by h |   (see §E)
corroboration(h) = max(0, |unique kinds among unique valid cited IDs| − 1)
proximity(h)     = 0 in Phase 1 (failing-path distance arrives in Phase 2)
```

**Dedup is mandatory (anti-gaming):** coverage sums over the *set* of unique valid cited IDs — repeated citations of the same ID count once. Corroboration uses the *set* of unique cited kinds — repeated mentions of a kind count once.

**Weights (config, like governor thresholds):** `w_cov = 1.0, w_con = 2.0, w_div = 0.25, w_prox = 0.0`.
`w_con > w_cov` is deliberate — it encodes the safety bias: a hypothesis that violates an invariant is worse than a well-cited one is good.

**Tie-breaks (fully deterministic, in order):**
1. higher `coverage`
2. lower `contradiction`
3. more unique evidence kinds
4. lexicographic `hypothesis_id`

Never rely on dict / insertion order.

---

## E. Contradiction semantics — structural, not semantic

Contradiction is computed from **structured fields only**. No prose comparison, no LLM.

A constraint `C` with `constraint_kind ∈ {forbidden, invariant}` is **contradicted** by hypothesis `h` iff ANY of:
- `C.evidence_id ∈ h.declared_violations`
- `C.target.symbol ∈ h.touched_symbols`
- `C.target.path ∈ h.touched_paths`
- `C.target.workflow_step` or `C.target.rule_id` matches a cited reserved-kind target *(effective only once `rule`/`span` are populated in Phase 2)*

```
contradiction(h) = | { C ∈ bundle.constraints :
                       C.constraint_kind ∈ {forbidden, invariant} ∧ contradicted(C, h) } |
```

**`known_issue` does NOT count toward hard contradiction.** It is guidance the agent already received (injected into `hard_constraints`) and a write-back target — not a determinism-breaking violation. Detecting a hypothesis that *re-triggers* a `known_issue` is deferred to v1.1 (would add a soft penalty term, not a hard contradiction).

Semantic (prose-vs-prose) contradiction is explicitly **out of scope** (§J). If ever wanted, it is an optional LLM-judge enrichment behind a flag, never the default.

---

## F. Write-back rule

Honors the Phase 0 locked decision: **manual/explicit promotion only** for new constraints. Automatic reinforcement of *existing numeric signals* is fine; automatic *creation* of hard constraints is not.

| Outcome | Action | Human confirm? |
|---|---|---|
| Verified-correct fix | record `outcome=accepted` → existing learning loop auto-reinforces cited memories (`learning.py` / `cortex_memory_feedback_scores`). If hypothesis declares `resolves:[con:id]`, queue that constraint for **retire**. | Reinforce: no (already automatic). Retire: **yes**. |
| Verified-wrong / human-rejected | emit a **`ConstraintCandidate`** to the review queue — *not* an active constraint. | **Yes** — becomes active only via `cortex_add_constraint`. |

**Invariant preserved:** no constraint is ever *created or activated* without human confirmation.

**Review-queue payload (named now to prevent lossy drift):**

```python
@dataclass(frozen=True)
class ConstraintCandidate:
    claim: str
    mechanism: str
    cited_evidence: list[str]
    source_brief_id: UUID
    source_hypothesis_id: str
    tenant_id: str | None
    scope: str | None
    proposed_kind: Literal["known_issue", "forbidden", "invariant"] = "known_issue"
    proposed_target: dict = field(default_factory=dict)  # {path?, symbol?, workflow_step?, rule_id?}
    # NOT an active cortex_constraints row until promoted via cortex_add_constraint.
```

A candidate carries everything a reviewer needs to create the constraint (kind + target + provenance) without re-deriving it.

---

## G. RL-readiness logging (instrument now, build RL later)

> Full RL position, SWE-RL principle, and the rejected-ideas ledger: [Reasoning Runtime — Roadmap & Decision Ledger](./27_05_reasoning_runtime_roadmap.md) §3.

RL in CHIPS, if ever built, is **offline policy/bandit tuning of config weights** (ranking, governor, stop/continue) over logged data — never model fine-tuning, never online live exploration. It is **causally gated on the verifier**, which is the reward generator (cf. SWE-RL: a cheap automatic reward is what makes RL work).

The only thing RL demands *now* is replayable logging. Persist per brief, alongside `ranked_signals` / `compression_trace`:

- `weights_used: dict` — the ranking/governor weights in effect for this compile
- `verification_reward: float | None` — populated later by the verifier (Phase 3); null until then

Cost now: near-zero. Skipping it makes offline RL impossible later without re-instrumentation.

---

## H. `cortex_constraints` additions required by Phase 1 (migration 007)

Phase 0 already defines `cortex_constraints` with `kind ∈ {forbidden, invariant, known_issue}`. Phase 1 adds the contradiction target:

- `target JSONB DEFAULT '{}'` — documented keys: `{path?, symbol?, workflow_step?, rule_id?}`.

`kind` is already a first-class column (§B point 2 satisfied at table level). Also add to `cortex_briefs`: `hard_constraints JSONB DEFAULT '[]'` (auditability — which constraints a brief injected), and the RL-readiness fields from §G.

---

## I. Implementation order (the safe sequence)

1. `models.py` — `EvidenceItem`, `EvidenceBundle`, `Hypothesis`, `ConstraintCandidate`
2. `hypothesis.py` — ranking + contradiction as **pure functions** (no DB, no LLM; unit-testable in isolation)
3. the `find:<content-hash>` ID fix in `builder.py` (the one prereq)
4. tests for 1–3
5. **only then** — `builder.py` derives the `EvidenceBundle`; MCP surface (`cortex_submit_hypotheses`, review-queue write-back); wire-contract serialization of `evidence_bundle` (same verbatim treatment as the recent `data_sources` fix)

No persistent graph. No new store beyond the Phase 0 `cortex_constraints` table. No local generation model.

---

## J. Explicitly out of scope for v1

- Semantic (prose) contradiction — structural only (§E).
- `rule:` / `span:` evidence population — reserved IDs only; arrives in Phase 2.
- Persistent causal graph DB — Phase 2 assembles the failing path *per-incident, ephemeral*.
- RL of any kind — only the §G logging hook is in scope now.
- Model fine-tuning (SWE-RL recipe), online RL, HRM/TRM/NAR latent-reasoning architectures — watchlist, no build.
- `known_issue` re-trigger penalty — v1.1.
