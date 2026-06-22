# Track 2 · P0 — Partial-Population Decision Table

**Lineage:** TARGET (aspirational). Read under [`../../adr/A0-architecture-reconciliation.md`](../../adr/A0-architecture-reconciliation.md).
**Status:** Paper artifact. **No gate code exists or may be written until this table is ratified** (build-brief anti-goal: "Do not skip Track 2 P0").
**Parents:** [`chips-build-brief.md`](./chips-build-brief.md) (Track 2 P0), [`chips-execution-decision-sheet.md`](./chips-execution-decision-sheet.md).
**Resolves:** carried **open decision #6** (partial-population gate actions).

---

## 1. Why this table exists

The Signoff gate's **DRC** stage reads from named graphs that, in the real system, are
**partially populated**: a graph may be fresh, stale, empty, missing, or its sink may be
unreachable. A gate that silently treats "missing" or "stale" as "clean" manufactures false
confidence on exactly the inputs it can't see. This table fixes, before any gate code, what the gate
does for every population state — the **rip-out insurance**.

## 2. The single governing principle

Two facts the gate must never conflate:

> **"The gate can't see it" ≠ "the action is unsafe."** A blind input means CHIPS *does not know* the
> blast radius — not that it is large. CHIPS *informs* human judgment; it does not replace it.

So the gate has exactly **one** law and **one** BLOCK exception:

- **Law — `UNKNOWN → ESCALATE`.** Any input the gate cannot trust (stale, missing, empty, unreadable)
  routes the fire to **Signoff Review** (Manual Signoff / Waiver) **with the blindness surfaced as the
  review headline**. The human is the one party who can resolve a blind input (it is literally what the
  receipt-validated interview is for). The gate never silently denies on blindness.
- **The one BLOCK — unrecordable approval.** BLOCK *only* when a human's approval could not be made
  accountable, i.e. **the decision cannot be durably written *now*.** Approving into a void where the
  approval won't be auditable defeats the entire point of Manual Signoff being an audited decision.

Fire-class (destructive vs non-destructive) is **not** a BLOCK axis. It only affects how loudly the
escalation is framed.

## 3. The BLOCK predicate (deterministic, point-of-use, ternary)

BLOCK is keyed on **one checkable predicate, not a state name** — and that predicate is **ternary**,
the same shape as the gate's other arms, never a writable/unwritable binary:

> **Can the gate, right now, perform a durable write of this decision?**
> → `writable | transiently-unwritable | durably-unwritable`

- **`writable`** — the write will succeed; the graph is merely thin / empty / stale → **not a BLOCK**.
  This is *visibility* blindness, handled by the `UNKNOWN → ESCALATE` law.
- **`durably-unwritable`** — the approval genuinely cannot be recorded (sink absent, misconfigured,
  persistently unreachable, write returns a hard/non-retryable error) → **BLOCK**. Unrecordable approval.
- **`transiently-unwritable`** — the write fails *retryably* this instant (timeout, momentary lock,
  retryable error) but the approval *can* be recorded, just not right now → **bounded retry, then
  resolve** to one of the other two. A recovery within the bound proceeds (record, continue to the
  visibility arms); staying down past the bound *becomes* `durably-unwritable` → BLOCK. A terminal
  BLOCK here would let an infrastructure flicker manufacture a spurious refusal on a safe, fully
  human-approved high-stakes fire — the inverse of the failure this table protects against.

**Why a predicate, not a state name:** "missing" is ambiguous — it can mean "no sink, can't write"
(unrecordable → BLOCK) or "writable but empty" (recordable, impaired view → ESCALATE). Keying on
*will-a-write-succeed* collapses that ambiguity into one deterministic check and **cannot misfire on
cold-start**: a brand-new CHIPS has an empty-but-writable provenance graph, so it escalates-and-records
rather than refusing every fire.

**Why ternary, not binary:** "the sink is down for 200ms" and "the approval can never be recorded" are
*different facts*. A binary predicate collapses them and turns audit-sink availability into gate
availability — blindness-about-the-sink (transient) becoming a deny, the same conflation the original
draft made with blindness-about-the-world. The transient state applies the `UNKNOWN →
don't-fail-closed-on-transient-uncertainty` discipline to the **accountability arm itself**, which is
the one arm that hard-blocks.

**Point-of-use:** the writability probe runs **at the moment of the gate decision**, never assumed
from an earlier health check — the same discipline as the Signoff approve-time freshness re-check. A
sink writable at classification can be down at approval; re-probe at decision time and again at the
approve-time re-check. The retry bound is read from config (see §12), not hardcoded.

## 4. Locked inputs (not re-litigated here)

From the build-brief Signoff FSM:

- **DRC has two ternary arms**, each returns `clean | violation | unknown`:
  - **Policy Eval** — does this fire violate a known rule / constraint / contract?
  - **Blast Radius Read** — how far does this fire reach, and how dangerous is that reach?
- **`UNKNOWN → ESCALATE` on both arms** (fail-safe, never fail-closed-by-blindness).
- **Edge-confidence hierarchy:** enforced contracts > empirical/observed > structural/static >
  associative. **Associative edges never gate a destructive fire** (they cannot be the basis to PASS one).
- **Yield is never a gate input; Fragility is.**

## 5. Vocabulary

**Population state** of a visibility input at read time: `fresh | stale | empty | missing | unreadable`.
**Per-input verdict:** `clean | unknown | violation`. **Arm verdict** (after combine): same.
**Gate action:**

| Action | FSM effect |
|---|---|
| `PASS` | arm is clean; eligible for Auto Signoff if the other arm also passes |
| `ESCALATE` | route to Signoff Review (Manual / Waiver), **blindness surfaced**; never auto-pass |
| `BLOCK` | terminal refuse before Signoff; the decision could not be durably recorded |

## 6. Combine rule

**Worst-state-across-the-reach wins.** An arm reads N inputs; its verdict is the worst per-input
verdict (`violation` > `unknown` > `clean`). A single critical `unknown` cannot be outvoted by many
`clean` inputs.

## 7. The decision grid (visibility-vs-accountability axis)

### 7a. Accountability path — checked first, as a precondition (ternary)

| `can-we-durably-write-the-decision-now?` (point-of-use, ternary) | Action |
|---|---|
| **`writable`** (incl. empty-but-writable graph) | no veto — proceed to the visibility arms; the decision will be recorded |
| **`transiently-unwritable`** (timeout / momentary lock / retryable error) | **bounded retry**, then resolve: recovers within bound → proceed (record); exceeds bound → falls through to `durably-unwritable` |
| **`durably-unwritable`** (sink absent / misconfigured / persistently unreachable / hard write error) | **BLOCK** (terminal — unrecordable approval) |

A transient sink failure is **not** a terminal BLOCK — a flaky audit store must never become a
denial-of-service on the gate. Only a *durable* failure (or a transient one that exceeds the retry
bound) is unrecordable approval.

### 7b. Visibility inputs — only reached if the accountability precondition passed

| Input population state | Per-input verdict | Action |
|---|---|---|
| `fresh` | `clean` | PASS-eligible |
| `stale` | `unknown` | **ESCALATE** (blindness surfaced) |
| `empty` | `unknown` | **ESCALATE** (blindness surfaced) |
| `missing` | `unknown` | **ESCALATE** (blindness surfaced) |
| `unreadable` | `unknown` | **ESCALATE** (blindness surfaced) |
| known `violation` | `violation` | **ESCALATE** (Manual Signoff / Waiver) |

**No visibility-input state BLOCKs.** Associative-only evidence on a destructive fire is treated as
not-clean (→ can't PASS → ESCALATE), honoring the edge-confidence rule.

### 7c. Final gate decision

1. **Accountability precondition (ternary).** Probe writability: `durably-unwritable` → **BLOCK**
   (stop); `transiently-unwritable` → bounded retry, then re-resolve (recovers → proceed;
   exceeds bound → BLOCK); `writable` → proceed.
2. **Else combine visibility arms** (worst-state-wins): both arms `clean` on `fresh` inputs →
   **PASS-eligible** (Auto Signoff); any `unknown` → **ESCALATE** (blindness surfaced); any `violation`
   → **ESCALATE** (Manual / Waiver).

## 8. The blindness-surfaced escalation (the bound that makes ESCALATE safe)

An ESCALATE driven by `unknown` must **not** present like a normal "here's the blast radius, approve?"
review. It must headline the gap so the human approves the *blind action with eyes open*, e.g.:

> **CHIPS is blind here.** The `<input>` is `<state>` on this `<fire-class>` fire. CHIPS cannot show
> you its `<policy reach | blast radius>`. Approve only if you independently know what this touches.

This is the purity law applied to the gate: a gap is labeled as a gap, loudly. The human is never lulled.

## 9. Per-arm input reach (aligns with P1 ontology)

| Arm | Reads (named graphs) | Notes |
|---|---|---|
| **Policy Eval** | `g:policy` (constraints/rules), `g:contract` (enforced contracts) | a contract `violation` is the strongest signal |
| **Blast Radius Read** | `g:coupling` (co-change/dependency reach + Code-Hub SPOF via fan-in), `g:ownership` (people SPOF register: Crowding / Single-owner), Fragility signal | Fragility is the built danger scalar; coupling is the area. `g:ownership` is the named graph for the **locked people-signal vocabulary** (Crowding, Single-owner → SPOF register) — not a new graph; the Code-Hub SPOF is derived from `g:coupling` fan-in, not from `g:ownership`. P1 binds these exact names. |
| **Accountability path** | `g:decision` / audit-provenance write | gated on the **ternary writability at decision time** (`writable / transiently-unwritable / durably-unwritable`), not content |

## 10. Worked examples

1. **Cold-start, destructive fire, empty-but-writable `g:decision`, all visibility inputs empty** →
   accountability precondition passes (write will succeed) → visibility arms `unknown` → **ESCALATE**
   (blindness surfaced) and the decision is recorded. *A new CHIPS can fire from day one.*
2. **All visibility inputs fresh + clean, audit path writable** → both arms PASS → Auto-Signoff-eligible.
3. **`g:coupling` stale, audit path writable** → Blast Radius `unknown` → **ESCALATE** (blindness surfaced).
4. **Audit sink down / unreachable at decision time** → **BLOCK** (unrecordable approval), regardless of
   how clean the visibility inputs look.
5. **`g:contract` violation, audit path writable** → Policy Eval `violation` → **ESCALATE** (Manual / Waiver).
6. **Audit path writable at classification but down at approve-time re-check** → **BLOCK** at the
   re-check (point-of-use defeats a stale health assumption).

## 11. Required tests (the executable guards)

- **Cold-start guard (load-bearing):** empty provenance graph + writable sink + destructive fire →
  **ESCALATEs and records, does NOT BLOCK.** Guards the broad-phrasing failure mode; ties to the
  Materials-layer onboarding/cold-start mode (the system works before it knows anything by
  escalating-and-recording, not refusing).
- **Unrecordable-approval BLOCK (durable):** sink absent / misconfigured / persistently unreachable /
  hard write error at decision time → **BLOCK**.
- **Transient-vs-durable (load-bearing):** transient sink failure that **recovers within the retry
  bound** on a destructive fire → **records-after-retry and proceeds, does NOT terminal-BLOCK**; a
  transient failure that **exceeds the bound** → resolves to durable → **BLOCK**. This is the guard
  against a flaky audit store becoming a denial-of-service on the gate.
- **Point-of-use writability:** writable at classification, durably-unwritable at approve-time re-check → **BLOCK** at re-check.
- **Visibility never blocks:** every visibility input state (stale/empty/missing/unreadable) on a
  destructive fire → **ESCALATE** with blindness in the surfaced payload, never BLOCK.
- **Worst-state-wins:** one `unknown` input among many `clean` → arm verdict `unknown` → ESCALATE.

## 12. Ratification checklist

1. The single law (`UNKNOWN → ESCALATE`) and the single BLOCK (`can't durably write now`).
2. The BLOCK predicate is **writability-at-decision-time**, probed at point-of-use; empty-but-writable
   → ESCALATE, not BLOCK.
3. The blindness-surfaced escalation payload (§8) is mandatory for `unknown`-driven ESCALATEs.
4. The per-arm reach (§9).
5. Staleness budgets per named graph (what makes `fresh` → `stale`) — **deferred to open decision #3**
   (Yield calibration cadence / staleness threshold). Gate code **reads the staleness budget — and the
   accountability-arm retry bound (§3) — from config**, never hardcoded, so #3 resolving is a config
   change, not a code change.

## 13. Out of scope (deliberately)

- The full `g:*` predicate vocabulary and named-graph partition scheme — that is **P1** (held until
  this table is ratified, so the audit-path reach can align to "writability at decision time").
- Signoff tier routing internals and Review resting-state transitions — the build-brief owns those;
  this table only emits `PASS | ESCALATE | BLOCK` into them.
- Any implementation. P0 is paper; gate code waits on ratification.
