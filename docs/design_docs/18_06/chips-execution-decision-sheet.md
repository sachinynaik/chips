# CHIPS - Execution Decision Sheet (2026-06-18)

> Purpose: convert the reconciled target design in `docs/design_docs/18_06/` into an execution-facing decision record. This sheet synthesizes the seven design docs in this folder and is governed by `A0-architecture-reconciliation.md` for built-vs-target reading. Each row states topic, status, decision, and the trigger if it is deferred or revisited.

---

## Decision Register

| Topic | Status | Decision | Trigger / Next Step |
|---|---|---|---|
| Defect definition | **Open, non-blocking** | Start with high-precision labels only: issue-linked bug/defect fixes, revert-linked fixes, and incident/hotfix fixes as the highest-confidence subset. Store raw commit + linkage + file-touch data so the label remains a query over stored data, not a baked-in harvest decision. | Implement raw capture now. Revisit the label query once the defect corpus is large enough to broaden safely without poisoning calibration. |
| First execution vertical | **Locked** | Track 1 is the first code vertical. Track 2 P0/P1 proceed in parallel as paper artifacts only. Do not block Track 1 code on gate design, and do not build gate code before P0. | Start Track 1 code now. Draft P0 partial-population decision table and P1 ontology in parallel. |
| Target stores vs commitment | **Locked** | Oxigraph/Qdrant/Letta/Cognee are destination vocabulary, not irreversible tool commitments. Architectural requirements are locked; implementations remain simplifiable. | Revisit at simplify checkpoints and after the first real vertical. |
| Materials layer priority | **Locked** | Assay starts as soon as evolutionary signals exist. Refinery, projection, coefficients, and ceremony wait. Versioned score snapshots should start immediately because the baseline history is unrecoverable later. | Build Assay after V1.1/V1.2 signals exist. Start versioned score snapshots immediately. |
| SPOF ownership | **Locked** | Derived Code-Hub SPOF self-maintains from graph fan-in. Declared Infra/Data/Source/Knowledge rows are owned by the lead for now and reviewed on infra-change events, not on a calendar cadence. | Revisit owner assignment as team structure grows and delegation becomes real. |
| External/demo metrics | **Deferred** | Do not build yield/dashboard presentation early. Demo artifacts should follow proven internal signal value, not precede it. | Activate after fragility is meaningful and calibration has real defect evidence. |
| Admission-time chip safety | **Deferred** | Real future scope, but not first-vertical scope. Fire-time gating matters before chip-admission gating does. | Activate when a real chip library or registration path exists. |
| Multi-repo scope | **Locked** | Stay single-repo until one full vertical is proven. Cross-repo contract visibility is the first extension; federated graph/search comes later. | Expand after the first vertical succeeds, starting with contract-shaped cross-repo signals. |

---

## Operational Read

- **Build now:** Track 1 evolutionary signals, fragility path, early Assay, raw defect-corpus capture, and versioned score snapshots.
- **Design in parallel:** gate P0 partial-population table and P1 ontology.
- **Defer intentionally:** demo surfaces, admission-time chip safety, and multi-repo federation.
- **Keep simplifiable:** target stores and tooling, while preserving locked vocabulary and architectural requirements.

---

## Capture-Now Imperative

**Start now or lose forever:** raw defect-corpus capture and versioned score snapshots. Every commit and every score-field state that passes before these exist is unrecoverable history.

---

## Execution Constraint

**Do not build gate code before P0.** The partial-population decision table is the rip-out insurance for the gate. Gate design can proceed now; gate code cannot proceed ahead of that artifact.
