# CHIPS — Track 2 P0: Partial-Population Gate Decision Table

**Date:** 2026-07-05
**Status:** SIGNED OFF (owner verdict, 2026-07-05) — paper artifact, no code. Gate code
cannot proceed ahead of this table (build brief, execution decision sheet: "do not build
gate code before P0").
**Cold-start (owner verdict, 2026-07-05): declared shadow phase.** The gate runs
advisory-only until signal coverage crosses a declared threshold; the strict table applies
from enforcement day. The coverage threshold value is recorded here when declared —
softening missing-fragility was explicitly rejected (it would weaken the asymmetry law).
**Coverage threshold (owner verdict, 2026-07-06):** signal coverage = the fraction of
shadow-mode gate fires, over a trailing 14-day window, whose required DRC inputs were ALL
fresh per §2. Enforcement day arrives when this fraction crosses **80%** (provisional,
tunable with shadow-phase evidence, changes recorded here). Framing note: the locked
asymmetry law means premature enforcement cannot produce a wrong PASS — the threshold is
an escalation-noise dial, not a safety dial. The same declared threshold governs
co-change cold-start per amendment A11.
**Substrate note:** written substrate-agnostic. Each input names its target home (`g:*`
named graph, Oxigraph) and its current Postgres analog. The table's semantics do not change
at migration; only the freshness probes do.

---

## 1. Purpose

The Signoff FSM's rip-out risk is not the happy path — it is what the gate does when its
own inputs are degraded. This table fixes, before any gate code exists, the action for
every combination of {DRC input} × {population state}. The governing law:

> **Degradation asymmetry (LOCKED):** a degraded input may *worsen* an outcome
> (clean → unknown, unknown → violation-handling) but may **never improve one**. No input
> state maps to clean except a fresh input whose content is clean. Fail-safe, never
> fail-open.

## 2. Population states (exact definitions)

| State | Definition |
|---|---|
| **fresh** | Record exists for the fire's scope; assay/update timestamp within the input's TTL; producer version matches the pinned contract version. |
| **stale** | Record exists but TTL exceeded, **or** version-skewed (producer schema/ontology version ≠ pinned). Version skew is a *declared unseen class* — treated as stale, never as fresh-with-warning. |
| **missing** | No record for the scope. Distinguish from **known-empty**: a fresh record explicitly asserting "no entries for this scope" is *fresh* (content: empty), not missing. Producers MUST write known-empty markers; absence is never evidence of absence. |
| **failed-write** | Last write attempt errored or partially applied (poisoned). Worse than missing: content cannot be trusted *and* the producer pipeline is signalling fault. Always emits an infra finding in addition to its gate action. |

**Meta-rule:** if the freshness metadata itself is unavailable for an input, that input is
**stale** (unknown freshness = not fresh).

## 3. TTLs (initial; tune with evidence, record changes here)

| Input class | TTL |
|---|---|
| Structural graph / coupling edges | staleness window of the indexer + 10 min |
| Fragility / file signals | 24 h |
| SPOF register (declared rows) | 7 days or last infra-change event, whichever sooner |
| SPOF register (derived Code-Hub) | same as structural graph |
| Policy facts / constraints / invariants / contracts | no TTL (valid until superseded) — but **version-pinned**; skew ⇒ stale |
| Freshness re-check at Approve | evidence must be fresh *at approve time*, not fire time |

## 4. The decision table

Cell notation: effect on the owning arm's ternary output, plus tier effect.
Arm composition (§5) turns cell outcomes into the arm result.

### 4.1 Policy Eval arm

| Input (target home · current analog) | fresh | stale | missing | failed-write |
|---|---|---|---|---|
| **P1. Policy facts / constraints** (`g:policy` · `cortex_constraints`) | evaluate → clean / violation per content | evaluate anyway: **violation stands; clean degrades to unknown** | unknown | unknown + infra finding |
| **P2. Capability contracts** (`g:contracts` · contract memories) | evaluate per content | violation stands; clean → unknown | unknown | unknown + infra finding |
| **P3. Invariants** (invariant memories) | evaluate per content | violation stands; clean → unknown | unknown | unknown + infra finding |
| **P4. Policy version pin** (`policy_version`) | proceed | n/a (skew ⇒ P1–P3 stale) | **arm = unknown** (cannot know which rules applied) | arm = unknown + infra finding |

### 4.2 Blast Radius Read arm

| Input (target home · current analog) | fresh | stale | missing | failed-write |
|---|---|---|---|---|
| **B1. Structural graph** (`g:structure` · CodeGraph index / graphify-out) | compute reach | compute reach, **arm capped at unknown** (reach advisory only) | **arm = unknown; tier floor = Manual** (reach uncomputable) | as missing + infra finding |
| **B2. Coupling edges** (`g:coupling` · `cortex_cochange_pairs`) | weight reach | use, clean → unknown | proceed without co-change widening, **record gap in audit** (edges are widening evidence, not the spine) | as missing + infra finding |
| **B3. Fragility signal** (fragility snapshots) | apply scalar | **assume worst observed fragility for scope**; clean → unknown | assume worst; arm ≥ unknown | as missing + infra finding |
| **B4. SPOF register ∩ reach** | mitigated: proceed · bare: escalate (locked guarantee) | **treat intersecting SPOFs as bare** | treat entire reach as potentially bare ⇒ tier floor = Manual | as missing + infra finding |
| **B5. File signals / churn** (`cortex_file_signals`) | contribute | clean → unknown | proceed, record gap | as missing + infra finding |

### 4.3 Cross-cutting rows (override everything)

| Input | fresh | stale | missing | failed-write |
|---|---|---|---|---|
| **C1. Audit log writability** | proceed | n/a | **BLOCK: no fire executes if its audit record cannot be written.** Not Manual — blocked. Terminal until audit restored. | same — BLOCK |
| **C2. Fire immutability record** (fire frozen at classification) | proceed | n/a | block (a fire that cannot be frozen cannot be evaluated) | block |
| **C3. Tenant boundary resolution** | proceed | treat as missing | **block** (never evaluate cross-tenant by default; cf. known-limitation L1) | block |

## 5. Composition rules

1. **Within an arm:** result = worst cell outcome. Precedence: `violation > unknown > clean`.
2. **Across arms:** Signoff Tier consumes (policy result, blast result, fragility level, SPOF status):
   - any `unknown` on either arm → **tier ≥ Manual Signoff** (locked: UNKNOWN → ESCALATE);
   - `violation` → Manual, and hard-policy violation classes → straight to Reject (terminal);
   - `clean + clean` with fresh inputs → Auto or Waiver per risk thresholds (out of P0 scope).
3. **Waiver constraint:** a Waiver may cover an assessed *risk*; it may **never cover a
   degraded input**. Unknown-from-degradation is not waiverable — it is Manual only.
   (Otherwise waivers become the fail-open path.)
4. **Stickiness:** ≥ 2 degraded inputs on a fire's evaluation, or any bare/assumed-bare SPOF
   in reach ⇒ Manual review may not be delegated; Edit & Refire re-enters with *current*
   input states (no state carryover from the prior fire_id).
5. **Audit completeness:** every degraded cell fires an audit annotation
   `{input, state, action-taken}` — the decision record must show *what the gate knew and
   didn't*. Silent degradation is itself a defect class.
6. **Freshness re-check at Approve** (locked guarantee) re-runs this table on current
   states; any input that regressed from fresh ⇒ re-escalate (never silently execute on
   the stale approval).

## 6. Worked examples

1. *Structural graph 26 h stale, policy fresh-clean, no SPOF hit:* blast arm capped at
   unknown ⇒ Manual Signoff. Reviewer sees reach marked advisory + staleness annotation.
2. *Everything fresh, policy violation on a hard class:* Reject, terminal, audited.
3. *SPOF register failed-write:* intersecting reach treated bare ⇒ Manual (sticky) + infra
   finding opened; the register's own producer becomes a fire-blocking dependency —
   which is correct, because the register lists itself as a Data SPOF.
4. *Audit log unwritable:* everything blocks. No exceptions, including Letta-initiated
   fires (caller, never authority).

## 7. Open items this table hands to P1/P2

- P1 ontology: per-`g:*` version pinning scheme (P4 row assumes it exists).
- P2 vertical MUST exercise ≥ 1 deliberately-induced stale subgraph and 1 failed-write
  to prove rows 4.2-B1 and 4.3-C1 fire (build brief requirement).
- Producer contract: known-empty markers (§2) are a new obligation on every harvester
  writer — needs a small schema addition (explicit empty-assertion rows or per-scope
  heartbeat).
- TTL values in §3 are starting points; every change is an edit to this file, not code.

---

*A hand-authored node in the decision-provenance lineage under A0. The degradation-asymmetry
law and cross-cutting block rows are LOCKED as of owner sign-off 2026-07-05; TTLs and tier
thresholds remain tunable.*
