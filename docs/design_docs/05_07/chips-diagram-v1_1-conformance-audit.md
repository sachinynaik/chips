# CHIPS CORTEX — Diagram v1.1 Conformance Audit & v1.2 Regeneration Order

**Date:** 2026-07-05
**Audited artifact:** `docs/CHIPS CORTEX ARCHITECTURE DIAGRAM.png` (v1.1)
**Governing spec:** `docs/design_docs/18_06/chips-diagram-update-spec.md`
**Method:** every element of the rendered v1.1 image checked against the spec's locked
restatement (§1), the two new blocks (§2), attachment arrows (§3), vocabulary lock (§4),
generator notes (§5), and the v1.2 delta (Materials layer).

---

## 1. Verdict

The v1.1 render implements the spec **almost exactly**. All of the following were verified
correct in the image:

- Signoff FSM: Intent → DRC → Signoff → Fabrication → Audit → Feedback; single fire path;
  both DRC arms ternary (clean / violation / unknown) with UNKNOWN → ESCALATE on both arms.
- Signoff Tier (Auto / Waiver / Manual) and Signoff Review as RESTING STATE with all four
  transitions (Approve → freshness re-check; Edit & Refire → new fire_id; Reject terminal;
  Abandon / Timeout terminal). Terminal states never reach Execute.
- Freshness re-check with stale → re-escalate path.
- Ownership rules, crossing rules, guiding principle banner — all locked text present.
- Promote Pipeline with Tapeout reserved for Promote only (rare & irreversible);
  frequency/irreversibility footer correct.
- Yield & Inspection layer: Yield Score labeled external/demo, Fragility labeled gate-relevant
  (→ DRC escalation), Inspection Suite grouped structural [ext] / evolutionary [gate] /
  people & knowledge [gate]; reads from Codebase Retrieval tools + git history;
  `g:coupling` thin link to Oxigraph present.
- SPOF Register: five categories incl. derived Code SPOF (Hub, high fan-in);
  mitigated / partial / bare status; feeds Signoff Review; declared + derived label.
- Both locked distinctions preserved: blast radius ≠ fragility; coupling ≠ entropy.
- Key Guarantees block complete (unknown escalates, no self-approval, human for manual
  signoff, immutable & auditable, freshness re-check on delayed approvals, stale evidence
  re-escalates, edit & refire creates new fire_id, bare SPOF on blast radius escalates).

## 2. Deviations found (fix in v1.2)

| # | Deviation | Spec reference | Severity |
|---|---|---|---|
| D1 | **Chronicle missing from Cortex Core row.** Render shows 8 modules (Retrieve · Signal · Sage · Signoff · Policy · Trace · Flow · Memory); spec locks 9 including **Chronicle**. | §1 "Cortex Core modules" | Spec violation |
| D2 | **Third simplify checkpoint missing.** Render shows 2 checkpoints; spec orders a third: *Inspection suite scope — keep only defect-predictive signatures; drop any added for symmetry.* | §5, last bullet; `chips-build-brief.md` §6 | Spec violation |
| D3 | **Yield Score → Dashboard/External "demo" arrow absent.** No dashboard/external node exists in the render; Yield Score is labeled external/demo but points nowhere. | §3 arrows summary | Minor |
| D4 | **Zenith / Trace Cache rendered as a settled evidence source.** ADR-002 status is "Spike approved — integration undecided" with explicit kill criteria. Rendering it unannotated presents an undecided component as settled. | ADR-002 header | Minor (annotation) |
| D5 | **Materials layer plane absent.** The v1.2 delta (spec, final section) and `chips-materials-layer-spec.md` define a full understanding plane not yet drawn. Not a v1.1 violation — the delta is explicitly "for the next diagram regeneration" — but the diagram no longer covers full architectural intent. | Spec "v1.2 DELTA"; materials-layer-spec | v1.2 scope |
| D6 | **Context layer missing from Infrastructure row.** Spec §1 locks the infra restatement as "… · Sentry. Context layer: Headroom · RTK · lowfat."; the v1.1 render omits it. *(Found during v1.2 regeneration, after the initial audit pass — recorded here rather than fixed silently.)* Rendered in v1.2 with a "(spike-gated)" annotation consistent with `implementation_tracking.md`. | §1 "Infrastructure (local-first)" | Spec violation (minor) |

## 3. v1.2 regeneration order

Apply, in addition to everything already correct in v1.1:

1. **D1** — Add **Chronicle** to the Cortex Core module row (9 modules total). Sub-label
   consistent with the register: coordination history / Letta-facing. No other module changes.
2. **D2** — Add third item to SIMPLIFY CHECKPOINTS: *3) Inspection-suite scope (keep only
   defect-predictive signatures; drop any added for symmetry).* Keep the existing trigger
   line ("after first end-to-end vertical").
3. **D3** — Either add a small **Dashboard / External** node receiving the lighter
   "demo" arrow from Yield Score, or annotate Yield Score "→ external/demo surface
   (deferred — see execution decision sheet: do not build demo surfaces early)". The
   annotation option is preferred; it matches the locked deferral.
4. **D4** — Annotate Zenith / Trace Cache: *(spike-gated — ADR-002, integration undecided)*.
5. **D5** — Add the **Materials layer** plane per the spec's v1.2 delta section, verbatim:
   Assay (read-only) · Refinery (read-write) · three never-merged dimensions
   (Purity / Decay / Freshness) · Versioned truth (Dolt) · Projection · Delta-signature;
   arrows: evolutionary fault signatures → Decay model + Assay; Assay → Dolt; Projection
   reads Dolt; Refinery → Assay; Materials → Foundry/DRC (Blast Radius Read consumes
   characterized, purity-scored stock). Improvement track as small side panel only.
   Vocabulary lock additions: Materials layer · Assay · Refinery · Purity · Decay ·
   Freshness · Doping · Annealing · Delta-signature · Projection. (Reserved, do not draw:
   Ingot, Wafer.)

Nothing else changes. All v1.1-correct elements are re-rendered as-is.

## 4. Post-regeneration verification checklist

- [ ] Cortex Core row contains exactly 9 modules, Chronicle included.
- [ ] SIMPLIFY CHECKPOINTS contains exactly 3 items + trigger line.
- [ ] Zenith carries the spike-gated annotation.
- [ ] Yield Score demo arrow resolved per D3 (node or deferral annotation).
- [ ] Materials layer present as a distinct plane *before* the Foundry; no vocabulary
      shared with Foundry/Fabrication.
- [ ] Purity / Decay / Freshness drawn as three distinct dimensions, never merged.
- [ ] All §4 vocabulary-lock terms used exactly; no synonyms, no biological terms.
- [ ] Blast radius ≠ fragility and coupling ≠ entropy distinctions still legible.
- [ ] Infrastructure row includes the Context layer (Headroom · RTK · lowfat), spike-gated annotation (D6).
- [ ] Diagram version stamp updated to v1.2.

## 5. v1.2 render status (2026-07-05)

Rendered as `docs/CHIPS CORTEX ARCHITECTURE DIAGRAM v1.2.svg`. All checklist items verified
against the SVG source: 9 Cortex Core modules incl. Chronicle (D1); 3 simplify checkpoints +
trigger (D2); Yield Score resolved via deferral annotation, per the preferred D3 option;
Zenith annotated spike-gated · ADR-002 (D4); Materials layer plane rendered per the v1.2
delta with locked vocabulary and never-merged dimensions (D5); Context layer added to
Infrastructure, spike-gated (D6). The v1.1 PNG is retained as provenance; the SVG is the
v1.2 authority.

---

*A hand-authored node in the decision-provenance lineage under A0. Vocabulary locked;
rendering subject to `/simplify`.*
