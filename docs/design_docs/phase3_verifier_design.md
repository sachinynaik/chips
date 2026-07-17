# Phase-3 Verifier — Design (for owner sign-off)

**Status:** DESIGN PROPOSAL — the Phase-3 keystone. Governed by `02_06_execution_ledger.md`
and `02_06_contextual_bandit_design.md`. **This designs the single prerequisite that unblocks
`composite_reward` → mastery/OPE/online-bandit/rule-induction (all `blocked` today).** Nothing here
builds a blocked capability; it specifies the artifact whose existence flips those rows toward
`active`. **Building it requires owner sign-off** — the verifier *mints* the reward-label invariant
every downstream metric depends on (minting = design checkpoint before code).

## 1. What the verifier is (and is not)

**Is:** a deterministic labeler that, for each compiled brief, decides whether the work that
followed it turned out **good / bad / unknown**, and writes that label into the slot the decision
log already reserves — `cortex_decision_log.verifier_outcome` (JSONB, currently NULL, §9.1 of CB).

**Is not:** an LLM judge, a model, or anything non-deterministic. Ledger §5 invariant is
non-negotiable: *"No LLM judge / non-deterministic input in the reward path; `w_review` and
`w_latency` = 0 until the verifier term dominates."* A verifier that violates this poisons every
metric above it — that is the keystone failure mode (§7).

## 2. Why it is buildable now (grounding — not invented)

The verifier does **not** need new ground-truth infrastructure. CHIPS already produces the
deterministic outcome signals it needs:

- **Durability / defect signal** — `cortex_defect_corpus` with **revert linkage** and
  hotfix/incident keyword tiers (T1–T4), plus `DefectPredictor` revert-introduced credit. If the
  files a brief pointed at (or the agent edited after receiving it) are **reverted or
  hotfix-corrected within a window**, that is a deterministic *bad* outcome.
- **Retrieval precision** — `cortex_briefs.retrieval_overlap_score` and `agent_edited_files`:
  did the brief's retrieved files actually match what the agent edited? Deterministic.
- **Test/CI outcome** — `cortex_briefs.test_outcome` / `post_task_outcome` (already columns).
- **The linkage table** — `cortex_brief_outcomes` (migration 004) + the `submit_brief_feedback`
  MCP tool (L4, partial) already carry brief→outcome. The verifier consumes these; it does not
  invent a new capture path.

So the verifier is a **join + deterministic rule** over existing tables, emitted as a labeled
`verifier_outcome`, not a research project.

## 3. The one decision only the owner can anchor

The whole reward rests on a single product definition: **what deterministic signal constitutes a
"verified good outcome" for a brief?** The candidates (all deterministic, all already-computed):

| Option | "Good" means | Strength | Weakness |
|---|---|---|---|
| **A — Durability** (recommended primary) | files touched after the brief are **not** reverted/hotfixed within N days | strongest "did it actually hold up"; reuses defect corpus + revert linkage | needs a maturation window (label latency → recompute-in-order, §9.4) |
| **B — Test/CI outcome** | the resulting change's CI/tests passed | immediate, crisp | passing tests ≠ good design; not all repos gate on CI |
| **C — Retrieval precision** | brief's retrieved files ⊇ what the agent edited | available at brief time (low latency) | measures the brief's *aim*, not the task's *success* |

**Recommendation:** primary = **A (durability)**, corroborated by **B**, with **C** as an
early-signal covariate — because durability is the only one that answers "was the guidance
actually good," and it's exactly what the harvester was built to measure. C alone would reward a
brief for pointing at the right files even if the change was later reverted (reward hacking).

**This is the sign-off decision.** Everything downstream is mechanical once it's fixed.

## 4. Pipeline (deterministic, offline-first)

```
brief compiled (build_and_log → cortex_briefs + cortex_decision_log)
   → agent edits files, records outcome (submit_brief_feedback → cortex_brief_outcomes)
   → [maturation window elapses]
   → verifier job: join brief_id → agent_edited_files → defect_corpus/revert linkage
                    over the window  →  outcome ∈ {good, bad, unknown} + evidence refs
   → write cortex_decision_log.verifier_outcome (deterministic, replayable)
   → (unblocks) composite_reward, verifier-dominant, schema-constrained
```

- **Deterministic + replayable:** same log + same window ⇒ byte-identical labels (mirrors the
  mastery replay-twice invariant). Late outcomes ⇒ **recompute-in-order** (§9.4), never
  out-of-order injection.
- **`unknown` is first-class:** briefs whose window hasn't matured, or whose files never got a
  follow-up signal, are labeled `unknown` and **excluded** from reward — not coerced to 0
  (data-sufficiency §6; theater-avoidance).

## 5. Data-sufficiency contract (ledger §6 — mandatory or it stays blocked)

- `N_min` labelled briefs/repo before any reward/mastery is reported as more than
  **insufficient-evidence** (an explicit surfaced value, not 0/null).
- Maturation window W (per repo; default proposal: 14–30 days of history, tunable) declared
  per-repo; a brief younger than W is `unknown`.
- Aggregation: **repo-level** primary.

## 6. What this unblocks, in order (each still ledger-gated)

1. **Verifier** built + labeling (this doc) → `composite_reward` prerequisite met.
2. `composite_reward` (§ CB): verifier-dominant, `w_review=w_latency=0`, each term normalized;
   **reward-schema conformance test** (rejects non-deterministic source fields) is the promotion
   gate.
3. `mastery_math`, then `OPE` (needs action-variation across `policy_version`), then
   `online_bandit` (ledger §7 checklist), then `rule_induction` (own doc). **None** of these are
   authorized by this doc — each promotes only when its own row's unlock evidence exists.

## 7. Failure modes (the keystone risks)

| Failure | How | Detection | Mitigation |
|---|---|---|---|
| **Weak verifier poisons everything** | labels are noisy/wrong → every reward consumer learns garbage | held-out durability agreement + confidence gate | ship verifier **shadow/observe-only first**; gate `composite_reward` on measured label precision, not mere existence |
| Non-determinism creeps in | someone adds an LLM/heuristic judge term | reward-schema conformance test | test rejects non-deterministic source fields (already specified) |
| Label-latency path dependence | out-of-order backfill of late outcomes | replay-twice equality test | recompute-in-order on the fully-labelled ordered log |
| Reward hacking on precision | rewarding retrieval overlap alone | option-C-only detection | durability (A) dominates; C is covariate-only |
| Survivorship bias | async outcome loss | log-count vs labelled-count audit | synchronous outcome write / documented bias |

## 8. Build sequence (after sign-off; delegate-buildable, each with a test gate)

1. **Verifier job skeleton** (read-only join over existing tables → `verifier_outcome`), labels =
   `unknown` for all → *gate:* replay-twice byte-identical + label-count audit. (Foundation-safe;
   no reward consumed.)
2. **Durability rule (Option A)** wired to defect_corpus/revert linkage over window W → *gate:*
   golden test on a hand-labelled sample (RGR-for-labels: prove the rule agrees with ground truth
   on a checked sample before trusting the bulk).
3. **Corroboration (B/C)** as covariates → *gate:* determinism + precision report.
4. **Shadow run** — labels written, **not** consumed — accumulate until `N_min`.
5. *(Only then, separate sign-off)* promote `composite_reward` to `active` per its row.

Steps 1–4 mint no reward and consume nothing blocked — they are the sanctioned Phase-3 start.
Step 5 is the next gate, not part of this doc.

## 9. Open sign-off items for the owner

1. **§3 anchor:** confirm primary = durability (A) + corroborating B, C-as-covariate — or choose otherwise.
2. **Window W** default (14 / 30 days?) and per-repo override policy.
3. **`N_min`** per repo before reward leaves insufficient-evidence.
4. Green-light to build **steps 1–4 (shadow verifier)** via Sonnet delegates under coordinator
   review — explicitly *not* step 5 (reward consumption).
