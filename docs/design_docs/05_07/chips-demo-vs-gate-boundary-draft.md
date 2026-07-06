# CHIPS — Demo-vs-Gate Metric Boundary (Draft)

**SIGNED OFF (owner decision, 2026-07-06 — recorded as amendment A12).** The 12-row table
is ratified as the explicit OD-5 boundary list, extended with rows 13–15 below. Open-row
rulings: (1) the associative-tier law IS grounded — `chips-track2-p1-ontology-contract.md`
makes "associative never gates a destructive fire" a schema invariant → row 13; (2)
`repo_metrics_v` as direct DRC Policy Eval input stays OPEN until the Policy Eval arm's
design exists (declaring now would mint a contract ahead of design); (3) co-change coupling
signals split per A11 → row 14; (4) CodeGraph MCP tools during the ADR-009 evaluation
window are **allowed as advisory on real work** (owner chose broader than the
measurement-only recommendation) → row 15.

*(Original draft header: DRAFT — for owner sign-off (A5 #4). Drafted 2026-07-05.)*

> Source: `docs/design_docs/05_07/chips-component-decision-amendments.md` A5 "Closable now"
> #4 — "Demo-vs-gate metric boundary — write the explicit list," source register OD-5,
> sized "one-page list (mostly already stated)." This draft assembles what is already
> stated across the 18_06 execution decision sheet, the amendments doc, and the execution
> ledger; it invents nothing new except rows explicitly marked **NEW-INFERENCE**, which are
> not decisions.

## Standing laws applied

1. **Nothing reward-consuming activates before the verifier.** Grounded in
   `02_06_execution_ledger.md` §9 ("Rejected: ... building reward-consumers before the
   verifier") and `implementation_tracking.md` L1 ("Blocked: Nothing reward-consuming in
   this layer may activate until the verifier exists").
2. **Uncalibrated yield/fragility are demo/advisory until calibration.** Grounded in
   `chips-execution-decision-sheet.md` "External/demo metrics" row (Deferred; "Activate
   after fragility is meaningful and calibration has real defect evidence") and A5 #8
   ("Yield calibration cadence + staleness threshold," gated on defect corpus size).
3. **Associative-tier signals never gate.** Referenced in the task brief as a standing law
   but **not found stated in the four files this draft was scoped to read** (decision
   sheet, amendments doc, implementation tracking, execution ledger). Listed under "open
   rows for owner" below rather than asserted here — do not treat as grounded.

## Boundary list

| # | Metric / surface | DEMO-ONLY (show, never gate) | GATE-ELIGIBLE (may feed Signoff/DRC once precondition holds) | Where stated |
|---|---|---|---|---|
| 1 | External/demo yield & dashboard presentation | Yes — deferred, presentation-only | — | `chips-execution-decision-sheet.md`, "External/demo metrics" row |
| 2 | Fragility scores | Yes, until calibration proven meaningful | Becomes gate-eligible once "fragility is meaningful and calibration has real defect evidence" | `chips-execution-decision-sheet.md`, "External/demo metrics" row |
| 3 | Yield scores | Yes, until calibration cadence + staleness threshold defined | Gate-eligible once A5 #8 closes (defect corpus large enough) | amendments doc A5 #8 |
| 4 | Grafana dashboards over `repo_metrics_v` / Prometheus | Yes — visualization only, by design | Never directly; underlying `repo_metrics_v` view is the single computed source, dashboards may only visualize it | `02_06_execution_ledger.md` §5 ("Metrics computed in CHIPS; surfaces only visualize"); `implementation_tracking.md` L3 ("no reward-consumer surfaces before verifier-backed metrics exist") |
| 5 | `composite_reward` / `mastery_math` / `OPE` / `online_bandit` / `rule_induction` outputs | Yes, if ever surfaced before their unlock conditions — advisory/observational only | Gate-eligible only after each row's own unlock evidence is recorded (Phase-3 verifier, data sufficiency, etc.) | `02_06_execution_ledger.md` §2 (all rows currently **blocked**), §9 ("Rejected: reward-consumers before the verifier") |
| 6 | Spike-gated components (Zenith/Trace Cache, Context Layer: Headroom/RTK/lowfat) | Yes — dashed-border "◌ spike-gated" convention signals not-settled; any output is advisory | Gate-eligible only once each spike concludes and the component is confirmed | amendments doc A3 |
| 7 | CodeGraph/Graphify structural-graph outputs during the A1 evaluation window | Yes — evaluation-phase output is advisory; "no swap, no retention, until the spike reports" | Blast Radius Read consumption becomes gate-eligible once ADR-009 verdict confirms gate fitness | amendments doc A1, A8 |
| 8 | Partial-population gate decision table (DRC input × fresh/stale/missing/failed-write) | Yes, during declared shadow phase — "Gate runs advisory-only until signal coverage crosses a declared threshold" | Yes, from enforcement day — "strict table applies from enforcement day" | amendments doc A7 |
| 9 | Defect-corpus labels, tier T4 | Yes — "T4 excluded from calibration until the audit passes" | Tiers T1–T3 are the current highest-confidence gate-eligible subset; T4 becomes gate-eligible once the ~60% hygiene-audit link-rate threshold passes | amendments doc A10 |
| 10 | Defect-corpus labels, tiers T1–T3 | — | Yes — "highest-confidence subset," raw capture underlies query-time label use | `chips-execution-decision-sheet.md` "Defect definition" row; `implementation_tracking.md` L2 |
| 11 | Anti-regression / constraint-candidate review queue outputs (pre-verifier) | Yes — manual-review/advisory today; "not yet fully operational as the controlling verifier-backed write-back loop" | Gate-eligible once the loop is verifier-backed end to end | `implementation_tracking.md` L1/L4 |
| 12 | Admission-time chip safety metrics | Yes — deferred entirely, no build yet, so any interim signal is demo-only by default | Gate-eligible only "when a real chip library or registration path exists" | `chips-execution-decision-sheet.md` "Admission-time chip safety" row |
| 13 | Associative-tier signals (`g:experience`) | Yes — readable for escalation framing only | **Never** PASS-eligible on a destructive fire (schema invariant); an edge becomes gate-eligible only by earning promotion to a higher tier | `chips-track2-p1-ontology-contract.md` (tier table; "associative never gates" invariant) — added at sign-off 2026-07-06 |
| 14 | Co-change coupling signals (pairs + entropy) | Yes — advisory during the declared shadow phase | Gate-eligible as empirical-tier signal once coverage crosses the declared threshold (same split shape as row 8) | amendment A11 (2026-07-06) — added at sign-off |
| 15 | CodeGraph MCP tools (`codegraph_*`) during the ADR-009 evaluation window | Yes — agents may invoke them on real work, output treated as advisory only | Gate-eligible (Blast Radius Read consumption) only after the ADR-009 verdict confirms gate fitness (row 7) | owner ruling at sign-off 2026-07-06 (broader than the measurement-only recommendation) |

## Open rows for owner

Resolved at sign-off 2026-07-06 except one: former open rows 1, 3, 4 became table rows
13, 14, 15 respectively (rulings in the header). The single remaining open row:

1. **`repo_metrics_v` as a direct DRC Policy Eval input** (as opposed to a
   dashboard-visualization source only). L1 lists `repo_metrics_v` as built foundation and
   L7 lists "DRC Policy Eval arm" as not-built; no file read states whether the view itself
   is meant to feed the eventual Policy Eval arm once built, or whether Policy Eval sources
   from elsewhere. **NEW-INFERENCE if included** — not stated either way. **Owner ruling
   2026-07-06: stays open by design until the Policy Eval arm's design doc exists.**

## Counts

- Table rows: 15 (12 as drafted + 3 added at sign-off); several rows are split demo/gate
  depending on precondition (2, 3, 7, 8, 9, 11, 12, 14, 15 each state both sides).
- Open rows for owner: 1 (repo_metrics_v ↔ Policy Eval; deliberately open).
- NEW-INFERENCE flagged explicitly: 1 (the same remaining open row).

Nothing else was read or written beyond the four permitted source files and this one
output file.
