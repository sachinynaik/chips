# CHIPS — Yield Signals & SPOF Register (build-brief addendum)

> Adds two things to the blast-radius model: the **inspection suite** (defect-predictive
> signals that compute a yield score and a per-region fragility weight) and the **SPOF
> register** (declared + derived single points of failure across the stack). All terms below
> are the locked CHIPS vocabulary — plain English as the label, the technical metric as the
> description, semiconductor terms only where they match the mechanism. No external tool is
> adopted; these are concepts computed natively against our own git, AST, and defect history.

---

## 1. Vocabulary principle (the naming rule, for future signals)

A signal's **label** is a simple word; its **description** carries the precise technical metric.
Use a semiconductor term only where it matches the mechanism (forcing fab onto complexity or
duplication would obscure, not clarify). A signal earns a slot only if it is **defect-predictive**
— the inspection suite is a catalog of *faults*, not of virtues, so we never add the healthy pole
of an axis as its own signal (no "sharpness" to mirror "vagueness").

Two axes that must stay distinct (each is two concepts, not one):
- **Blast radius** = how far a fire reaches (area/scope). **Fragility** = how defect-prone the
  reached territory is (scalar weight on the reach). Far ≠ dangerous.
- **Coupling** = files that change together (the edge). **Entropy** = how scattered that
  coupling is (the severity on the edge). Edge ≠ score-on-edge.

---

## 2. Yield & inspection — the code-health layer

| Label | Description (technical) | Notes |
|---|---|---|
| **Yield score** | defect-validated 1–10 health score per region | the headline number; deterministic, reproducible, no LLM |
| **Fault signature** | one deterministic defect-predictive signal | the unit that composes the yield score |
| **Inspection suite** | the full set of fault signatures | runs over AST + git; sub-30s, CI-fast clock |
| **Fragility** | defect-severity weight on a fire's blast radius | scalar; high blast radius into high-fragility regions escalates Signoff |

**Calibration discipline.** The yield score's weights are **learned from our own defect corpus**
(bug-fix commits over a forward window), not hand-tuned and not imported. We have the corpus by
construction. Re-fit on a slow clock (nightly/weekly); stale weights are flagged and the score
degrades to its raw signals rather than asserting a stale calibration.

**Consumer split.** Yield score + structural signals are **external-consumer** evidence (the
demo/partner credibility artifact) — *not* primary gate inputs, because the evolutionary signals
are the stronger defect predictors. Fragility (driven by the evolutionary signals) **is** a gate
input via DRC/Signoff escalation. Never let a demo metric silently become a gate input.

---

## 3. The inspection suite — fault signatures

### 3.1 Structural fault signatures (plain English; no honest fab equivalent)

| Label | Description (technical) |
|---|---|
| **Complexity** | cyclomatic complexity (McCabe) |
| **Nesting depth** | deep conditional nesting |
| **Bloat** | too much concentrated in one unit — function scope (excessive logic/branching, "brain method") and class scope (too many responsibilities) |
| **Cohesion** | how well a unit's parts belong together (LCOM-family); *low* cohesion is the fault |
| **Duplication** | copy-paste / clone detection (Rabin–Karp) |
| **Vagueness** | raw primitives where domain types belong (primitive obsession) — the code is imprecise about its own meaning |

### 3.2 Evolutionary fault signatures (the stronger defect predictors; gate-relevant)

| Label | Description (technical) | Fab fit |
|---|---|---|
| **Coupling** | files that change together (`g:coupling` edge) | software-native |
| **Entropy** | scatter of a region's coupling/changes (co-change + change entropy) | — |
| **Churn** | change frequency over time | — |
| **Volatility** | code-age instability (process instability) | mild |
| **Defect history** | prior fixes landed in this region (temporal pattern, recency-weighted) | — |
| **Defect density** | size-normalized defect concentration (defects per unit size) — the explicit size-control the yield calibration needs | — |
| **Hotspot** | high-churn × high-complexity region | native fab/EDA term |
| **Untested risk** | coverage gaps on active code | — |
| **Weak tests** | test-quality smells (tests that execute but don't catch) | — |

> The headline finding driving the consumer split: across these signals, the **evolutionary**
> ones (coupling, entropy, churn, defect history, hotspot) are stronger defect predictors than
> the structural ones. Our stack is structure-heavy and evolution-light, so these are the
> higher-value additions and the ones wired into the gate via fragility.

### 3.3 People & knowledge signals

| Label | Description (technical) |
|---|---|
| **Crowding** | authorship dispersion — too many hands in one region over time (the defect-predictive signal) |
| **Contention** | concurrent competition for the same region — multiple devs editing at once (live signal; bus-contention analogy) |
| **Single owner** | one person holds this region (bus factor = 1) — feeds the SPOF register |
| **Orphaned code** | original authors gone (knowledge loss) — feeds the SPOF register |

`g:coupling` lands in Oxigraph as a named subgraph, confidence-tagged below contracts/traces and
above associative recall. Entropy and the other signals are per-region scalars on the CI-fast
clock; fragility composes them and is read at fire-time by the DRC arm.

---

## 4. SPOF register (new — first-class)

A system that computes blast radius for *code fires* must also know the blast radius of *its own
topology*. The SPOF register is the infrastructure/data/knowledge analog of the declared-unseen-
classes list: the value is in SPOFs being **explicit and surfaced early**, not discovered during
an incident. Mostly **declared**, partly **derived**; mitigation-status tracked; freshness-stamped
so it doesn't rot into a stale one-time audit.

| Category | What it is | Examples in our stack |
|---|---|---|
| **Knowledge SPOF** | one person/region holds critical knowledge | single owner, orphaned code |
| **Code SPOF (Hub)** | an over-central unit — high **fan-in** (many dependents) — whose change/failure radiates widely | a class/module everything depends on |
| **Infra SPOF** | a single-instance service everything depends on | Keycloak, the CHIPS daemon, central Cognee, bus relays |
| **Data SPOF** | a single source of truth with no fallback | the Oxigraph blast-radius graph, the audit log |
| **Source SPOF** | a single upstream producer whose fault propagates downstream | the emitter (one wrong generation → every domain conforms to the wrong contract) |

> **Hub is the derived spine of the register.** Unlike the other categories (mostly declared),
> a hub is *computable* directly from the blast-radius graph: a node with high **fan-in**
> (many dependents — not fan-out, which is just coupling/fragility). So the register has a
> self-refreshing category that updates from Oxigraph on every sync, which is the structural
> answer to "how does the register avoid rotting." A hub's blast radius is large by construction,
> so "fire touching a hub escalates Signoff" falls out of the same fan-in computation.

Each row carries: **what it takes down**, its **blast radius**, and **mitigated vs bare**
(replicated / has fallback / has degrade path / none). Derive what's derivable — single owner
from crowding, infra SPOFs from deployment topology — and declare the rest.

**Discipline:** build a *register*, not a *detector subsystem*. Mostly declared, partly derived,
freshness-tracked. The point is explicit-beats-discovered, not a new piece of infrastructure.

**Gate tie-in:** a fire whose blast radius routes through a bare (unmitigated) SPOF escalates the
Signoff tier — the same way high fragility does. Single owner / orphaned code on a chip's reach
makes the manual-signoff tier stickier.

---

## 5. Where each piece lands (no new architecture)

- **`g:coupling`** → new named subgraph in Oxigraph (truth graph).
- **Fragility** → scalar weight read by the **DRC arm**, escalates **Signoff tier**.
- **Yield score + structural signatures** → the **demo/dashboard** layer (external consumer), not
  the gate.
- **SPOF register** → declared+derived artifact, read at the **Signoff review**, freshness-stamped
  like every other subgraph.
- **Crowding / Single owner / Orphaned code** → feed both fragility and the SPOF register's
  Knowledge category, and tie to CASL governance (sticky tiers on concentrated/orphaned regions).

All on the existing clocks: inspection suite + coupling on CI-fast (incremental per push),
yield-weight calibration on the slow/nightly clock, SPOF register declared + derived-on-sync.

---

## 6. Open decisions (carried from prior discussion)

1. **Yield calibration cadence + staleness threshold** — when do learned weights re-fit, and past
   what age do they degrade to raw signals.
2. **The "what is a defect" definition** — bug-fix commit? reverted change? hotfix tag? This is now
   load-bearing for *two* signatures (Defect history's numerator and Defect density's numerator), so
   a noisy definition produces two confident-but-meaningless signals, not one. Settle it with the
   calibration corpus.
2. **Coupling support threshold + generated-code filter** — how many co-occurrences make an edge
   real; exclude ORM/scaffolded files from spurious coupling.
3. **SPOF register ownership** — who maintains the declared rows and reviews mitigation-status;
   what cadence keeps it from rotting.
4. **Demo-vs-gate boundary** — the explicit list of which signals are external-only (yield score,
   structural signatures) vs gate-relevant (fragility, coupling/entropy, bare-SPOF), so a vanity
   metric never becomes a gate input.
