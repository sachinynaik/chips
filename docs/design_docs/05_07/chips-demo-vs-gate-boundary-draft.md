# CHIPS — Demo-vs-Gate Metric Boundary (Draft)

**DRAFT — for owner sign-off (A5 #4). Drafted 2026-07-05 from OD-5 + existing stated
boundaries; decides nothing by itself.**

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

## Open rows for owner

These could not be grounded on either side from the four files this draft was scoped to
read; they need an owner statement before they can be added to the table above.

1. **Associative-tier signal classification (standing law #3 above).** The brief states
   "associative-tier signals never gate" as a standing law, but none of the four files read
   for this draft (decision sheet, amendments doc, implementation tracking, execution
   ledger) states it. Likely lives in a P1/ontology-partition design doc outside this
   draft's read scope — owner should confirm the source doc and whether it belongs in this
   table.
2. **`repo_metrics_v` as a direct DRC Policy Eval input** (as opposed to a
   dashboard-visualization source only). L1 lists `repo_metrics_v` as built foundation and
   L7 lists "DRC Policy Eval arm" as not-built; no file read states whether the view itself
   is meant to feed the eventual Policy Eval arm once built, or whether Policy Eval sources
   from elsewhere. **NEW-INFERENCE if included** — not stated either way.
3. **Co-change coupling signals** (amendments doc A5 #3, OD-2: "Co-change support threshold
   + generated-code filter — blocks entropy quality"). Stated as blocking *entropy signal
   quality*, not explicitly classified as demo-only vs gate-eligible once the threshold is
   set. Owner should state which side this lands on.
4. **MCP-exposed CodeGraph tools (`codegraph_impact`/`callers`/`callees`/`status`)** used
   directly by an agent during the evaluation window, distinct from row 7's structural-graph
   *data* — i.e., is direct tool use during the spike itself permitted at all (even
   advisory), or fully blocked until ADR-009 concludes? Amendments doc A1 says "no swap, no
   retention, until the spike reports" but does not explicitly address in-spike tool
   invocation as demo-only vs disallowed.

## Counts

- DEMO-ONLY rows: 8 (rows 1, 2, 3, 4, 5, 6, 7-partial/pre-verdict, 11-pre-verifier, 12) —
  see table; several rows are split demo/gate depending on precondition (2, 3, 7, 8, 9, 11,
  12 each state both sides).
- GATE-ELIGIBLE rows: 8 (rows 2-post-calibration, 3-post-A5#8, 5-post-unlock, 7-post-ADR-009,
  8-post-enforcement-day, 9-post-audit, 10, 11-post-verifier, 12-post-chip-library) —
  precondition-gated, not currently active.
- Open rows for owner: 4.
- NEW-INFERENCE flagged explicitly: 1 (open row 2, `repo_metrics_v` as direct DRC input).

Nothing else was read or written beyond the four permitted source files and this one
output file.
