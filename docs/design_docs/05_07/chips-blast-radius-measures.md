# CHIPS — Blast Radius: Edge Sources and Measures

**Date:** 2026-07-05
**Status:** DRAFT — design note. This is the spec behind decision-table rows B1–B5
(`chips-track2-p0-partial-population-decision-table.md`) and the substrate the Blast
Radius Read arm consumes.
**Locked distinction preserved throughout:** blast radius = the *set* a fire reaches;
fragility = the *scalar danger* of reached territory; danger = their product.

---

## 1. Definition

For a fire F with touch-set T (files/symbols/schemas/topics the fire modifies), the blast
radius R(F) is the set of units reachable from T over the edge layers below, each edge
carrying its **confidence tier** and **freshness state**. R(F) is never a bare set: every
member records {via-edge-class, hops, tier, freshness}.

## 2. Edge layers (by the locked edge-confidence hierarchy)

### Tier 1 — Enforced contracts (highest; may gate alone)
| Edge | Source | Note |
|---|---|---|
| schema → consumers | migration-diff table/column touch → ORM models, query sites, schema registry consumers | the "dropped column deep in the service graph" tail case |
| event topic → subscribers | MQTT/Redpanda topic references: emitter change reaches every subscriber | cross-service by construction |
| typed API contract → dependents | contract registry / typed client usage | |
| workflow definition → steps | DBOS workflow registry: changed function referenced by workflow W ⇒ W in radius | |

### Tier 2 — Empirical / observed
| Edge | Source | Note |
|---|---|---|
| runtime call edges | OTel trace graph over trailing window (service→service, span parent/child) | catches edges static analysis can't see |
| test → code | coverage maps: which tests execute T | also feeds untested-fraction measure |
| traffic weight | span/request counts on reached paths | hot vs cold path weighting |

### Tier 3 — Structural / static
| Edge | Source | Note |
|---|---|---|
| reverse call/import closure | code graph (`codegraph_impact` / `callers`, per ADR-009) | k-hop capped, decay 1/(1+hops) |
| symbol references | LSP/serena reverse references | signature-change reach |
| fan-in of reached nodes | derived from same graph | doubles as Code-Hub SPOF input |

### Tier 4 — Associative (NEVER gates — advisory widening only, locked rule)
co-change edges (`cortex_cochange_pairs`) · semantic similarity.

**Degradation:** any layer whose source is stale/missing degrades per P0 §4.2 — Tier 1–2
gaps degrade the arm toward unknown; Tier 4 gaps are recorded and ignored.

## 3. Measures on R(F)

| # | Measure | Definition | Gate use |
|---|---|---|---|
| M1 | Reach size | count of units in R(F) | context, thresholds |
| M2 | Depth | max/median hops from T | deep+narrow ≠ shallow+wide |
| M3 | **Boundary crossings** | # service/process/repo boundaries crossed by Tier 1–3 edges | categorical escalator: 3-service crossing ≫ large same-module |
| M4 | Hub proximity | max fan-in among reached nodes | feeds derived Code-Hub SPOF |
| M5 | **Fragility-weighted reach** | Σ fragility(u) for u ∈ R(F) | the radius × fragility product; primary escalation scalar |
| M6 | **SPOF intersection** | R(F) ∩ {bare SPOFs} ≠ ∅ ? | locked guarantee: bare SPOF in reach escalates |
| M7 | Untested fraction | share of R(F) with untested-risk / weak-test flags | risk multiplier for review |
| M8 | Irreversibility class | operation class of the fire itself: destructive (schema drop, data migration, delete) vs additive | destructive ⇒ tier floor rises independent of size |
| M9 | **In-flight exposure** | R(F) ∩ workflows with live DBOS instances; count of active instances at risk | targets the stated tail case "changes that break in-flight workflows"; no generic tool computes this |

## 4. Ternary mapping (arm output)

- **violation**: M6 true with hard-policy SPOF class; or M8 destructive ∧ reach includes
  Tier 1 consumers with no migration path declared.
- **unknown**: any Tier 1–2 source degraded (per P0); or reach truncated at k-hop cap with
  unexplored frontier; or M9 uncomputable (workflow state unreadable).
- **clean**: full-tier computation, no violation triggers, measures under thresholds.
- Thresholds (M1–M5, M7) are tunable and live in policy facts, not code. Initial values
  set after shadow-mode data exists (missing-item #7) — deliberately not guessed here.

## 5. Phasing

**v1 (current Postgres stack, no Oxigraph):** Tier 3 static closure (ADR-009 candidate or
graphify regenerate) + Tier 1 contract edges (migration-diff table touch, topic-reference
scan, DBOS registry lookup) + M1–M6, M8, **M9** (owner verdict, 2026-07-05: pulled into v1 —
it targets the stated in-flight-workflow tail case and needs only the live DBOS
workflow-registry query already specified in §6). Tier 4 recorded, unused.
**v2:** Tier 2 (OTel trace edges, coverage maps, traffic weights) + M7.
**Oxigraph migration:** R(F) computation moves to SPARQL property paths over `g:structure`
(+ `g:coupling` advisory); semantics unchanged — this note, not the store, is the spec.

## 6. Freshness probes (per P0 §3)

| Source | Probe |
|---|---|
| code graph | indexer status (`codegraph_status` if ADR-009 passes; graphify regenerate stamp otherwise) |
| contract edges | migration head vs applied; registry version pin |
| trace edges | trailing-window recency vs TTL |
| DBOS registry / in-flight | live query at fire time (never cached) |

---

*A hand-authored node under A0. Measures M1–M9 and the ternary mapping are intended to
LOCK on owner sign-off; thresholds stay tunable in policy facts.*
