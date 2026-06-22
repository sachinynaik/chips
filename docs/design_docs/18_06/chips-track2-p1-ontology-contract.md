# Track 2 · P1 — Ontology Contract (Named-Graph Partition)

**Lineage:** TARGET (aspirational). Read under [`../../adr/A0-architecture-reconciliation.md`](../../adr/A0-architecture-reconciliation.md).
**Status:** Paper artifact. **No gate/ontology code may bind these partitions until this contract is ratified.** P1 is a *schema* — its partitions are what code references and what migrations are made of, so it is ratified before code (cost asymmetry: a wrong partition boundary is a migration, not an edit).
**Parents:** [`chips-build-brief.md`](./chips-build-brief.md) (Track 2 P1), [`chips-track2-p0-partial-population-decision-table.md`](./chips-track2-p0-partial-population-decision-table.md) (ratified — P0 emits into this partition).
**Resolves:** the named-graph partition scheme and per-arm read/write reach.

---

## 0. The two load-bearing lines (read these first)

Everything else in this contract derives from these two lines. A partition error can only hide here, so they lead:

**Line 1 — the tier list (partition by provenance/derivation tier):**

> `enforced/authored` { `g:contract`, `g:policy` } **>** `empirical` { `g:coupling`, `g:ownership`, +promoted } **>** `structural` { `g:struct` } **>** `associative` { `g:experience` } — plus `g:decision` as a **write-only audit target in its own category** (not a read-tier).

**Line 2 — the tier-change invariant (what makes the schema provably stable):**

> **An edge's tier membership changes only by {authoring, promotion}. Never by time. Never by the gate.** Decay / freshness / staleness are orthogonal continuous overlays — they change an edge's *scores*, never its *graph*.

If those two lines are right, the rest (per-arm reach, writability binding, metadata, out-of-scope) is mechanical derivation.

---

## 1. Partition principle — provenance/derivation tiering

Each `g:*` read-graph is a **confidence tier defined by how the edge was known**, not a bag of typed edges with a per-edge confidence field. The edge-confidence hierarchy from P0 §4 (`enforced contracts > empirical/observed > structural/static > associative`) is therefore **structural** — it is *which graph you are allowed to read to PASS*, not a value you check on an edge.

Consequence: **"associative never gates a destructive fire" is a schema invariant**, not a code check. The associative tier sits below the PASS threshold, so an associative edge *cannot* be the basis to PASS a destructive fire — enforced by graph membership.

**The partition axis is provenance (how known), and only that.** Two facts that are *not* the partition axis and must never be conflated with it:

- **Scope of authority is not the axis.** A `g:contract` (binds an integration) and a `g:policy` (binds behavior) are the *same provenance* — both authored, deterministic, human-asserted, 100%-known rules. They differ in *what they govern*, not in *confidence in the knowing*. So they share the **top tier**; the governed-scope is metadata on the edge, not a tier boundary. (Putting policy below contract would make a declared-policy violation spuriously weaker than a contract violation — both are authored rules the fire is breaking; both ground a top-tier `violation`.)
- **Temporal trust is not the axis.** Decay/freshness are continuous overlays (the Materials-layer scores, kept independent of purity). A stale empirical edge stays in `g:coupling` with a rising decay score; it does **not** migrate down to associative as it ages (Line 2). This is what stops the partition from thrashing every time a signal goes stale.

## 2. The tier list (detailed)

| Tier | Graph(s) | Provenance — how the edge was known | Can ground a `violation`? | PASS-eligible for a destructive fire? |
|---|---|---|---|---|
| **enforced/authored** (top) | `g:contract`, `g:policy` | Authored, deterministic, human-asserted rules (written down → 100% known) | Yes — both; a contract *and* a policy violation are top-tier | Yes |
| **empirical** | `g:coupling`, `g:ownership`, + promoted edges | Observed behavioral history (co-change, ownership/SPOF signals); promoted edges that earned this tier | Contributes to Blast Radius reach | Yes |
| **structural** | `g:struct` | Static/AST-derived (a static call/dep edge; may be dead code never exercised) | Contributes to Blast Radius reach | Yes |
| **associative** (lowest) | `g:experience` | Experience-/inference-derived, unvalidated | No | **No — read for escalation framing only** |
| **write-only audit** (own category) | `g:decision` | n/a — not a knowledge graph; an append-only decision/provenance log | n/a (never read for a verdict) | n/a |

**Why `g:struct` is separate from `g:coupling`** (confirmed, not granularity for its own sake): P0's hierarchy lists empirical and structural as *distinct tiers*. Co-change is behavioral evidence ("these files actually change together"); a static call edge is derived-from-AST ("this function statically calls that") and can be dead code never exercised. Folding them would collapse a tier boundary the PASS rule depends on. Separate graph keeps the invariant honest.

## 3. The tier-change invariant + orthogonal-overlay rule

**Tier membership changes only by {authoring, promotion}** — both deliberate, both auditable, both rare:

- **Authoring** — a human writes a contract/policy, or a deterministic analyzer emits a structural/empirical edge into its own tier. The edge is *born* in its tier.
- **Promotion** — an `g:experience` (associative) edge is validated and **earns** a higher tier (typically empirical). See §4.

**Nothing else moves an edge between graphs.** Specifically: **decay, freshness, and staleness never move tiers** (they are continuous overlays on the edge's scores), and **the gate never moves tiers** (it reads tiers; it does not re-tier). The set of tier-mutating events is exactly `{authoring, promotion}`. This is the structural guarantee that makes tier-as-graph viable — the partition is provably stable, the schema cannot thrash.

## 4. Promoted edges — stamp rides the edge, no `g:promoted`

A promoted edge **lands in the tier its evidence now justifies (typically empirical) and carries a provenance stamp that rides the edge**:

```
origin = promoted
source_experience_id = <id of the experience edge it was promoted from>
promoted_at = <version / timestamp of the promotion event>
```

- **No separate `g:promoted` graph.** A separate graph would force the PASS rule to special-case its *effective* confidence — reintroducing the per-edge confidence judgment the partition exists to eliminate.
- **The edge *is* empirical now, on the merits.** Promotion is, by definition, the act of an edge earning a new tier (it has been validated — that's what promotion *is*). The stamp does not mark a second-class edge; it records that this empirical edge's *provenance includes a promotion event*.
- **The stamp is read for audit/Materials, never for PASS.** PASS-eligibility reads *tier* (graph membership) only. The stamp satisfies the lock — *a promoted edge is never indistinguishable from a structurally/empirically-derived one* — without making it weaker.

This is why §3's tier-mutating set is exactly `{authoring, promotion}`: promotion is the *only* non-authoring way an edge crosses a tier boundary.

## 5. `g:decision` — the write-only audit target (contract, not substrate)

`g:decision` shares the `g:` namespace but is a **different kind**: an append-only audit/provenance write target, not a knowledge graph queried for edges. P1 defines its **contract**, not its store:

- **Write-only from the gate's perspective.** The gate *writes* the decision record into it; **no arm reads it for a verdict.**
- **Ternary-writability-probed (P0 §3/§7a).** The accountability arm's only relationship to `g:decision` is the point-of-use ternary writability probe (`writable / transiently-unwritable / durably-unwritable`); `durably-unwritable` → BLOCK, `transiently-unwritable` → bounded-retry-then-resolve.
- **Substrate deferred — deliberately.** Which store backs `g:decision` (Postgres now; possibly Dolt-versioned later) is **left to the deferred Dolt trigger (#30)**, not bound here. P1 defines the *role* (write-only, ternary-writability-probed, reads-nothing), not the *backing store* — the same target-vs-current discipline applied everywhere. P1 must not depend on the storage decision.

## 6. Per-arm read/write reach

Aligned to the ratified P0 arms (P0 §9) and to ternary writability for the accountability arm:

| Arm | Reads (for verdict) | Writes | Notes |
|---|---|---|---|
| **Policy Eval** | `g:contract`, `g:policy` (top tier) | — | A `violation` from *either* is a top-tier violation; the kind (contract vs policy) is governed-scope metadata, not a tier difference |
| **Blast Radius Read** | `g:coupling`, `g:ownership` (empirical), `g:struct` (structural) + the **Fragility** scalar (a computed signal, not a graph); **may read `g:experience` for escalation framing, never to PASS** | — | Fragility is the built danger scalar; coupling/struct are the area. `g:ownership` = the locked people-signal vocabulary (Crowding / Single-owner → SPOF register); Code-Hub SPOF derives from `g:coupling` fan-in, not a new graph |
| **Accountability** | **nothing** (reads no graph for a verdict) | `g:decision` | Gated on **ternary writability at decision time**, not content (§5) |

## 7. PASS-eligibility rule (the structural form of the edge-confidence hierarchy)

A destructive fire is **PASS-eligible only on edges at the `structural` tier or above** (`structural`, `empirical`, `enforced/authored`). **`associative` (`g:experience`) edges can never be the basis to PASS a destructive fire** — they may be read only to enrich the *escalation framing* (P0 §8 blindness-surfaced payload). This is the edge-confidence hierarchy realized as graph membership rather than a per-edge confidence check.

## 8. Edge metadata (rides the edge; never a tier boundary)

Two metadata fields are explicitly *not* partition axes — they ride the edge and are read for audit/framing, not for tier or (except where noted) PASS:

- **`governed_scope`** (top tier) — distinguishes a contract edge from a policy edge. Same tier, same provenance; different *what-it-governs*.
- **`origin` provenance stamp** (§4) — distinguishes a promoted empirical edge from a natively-observed one. Same tier; different *history*.

Decay/freshness scores (Materials layer) also ride the edge as overlays (§1, §3) and never affect tier.

## 9. Required invariant tests (the executable guards for the schema)

- **Tier stability under decay:** an empirical edge that goes stale (rising decay/freshness scores) **stays in `g:coupling`** — it does NOT migrate to `g:experience`. Guards Line 2 / §3.
- **Tier-change set is exactly {authoring, promotion}:** the gate reading/evaluating an edge **never changes its graph**; time passing **never changes its graph**. Only an authoring write or a promotion event moves an edge between graphs.
- **Policy == contract tier:** a `g:policy` violation and a `g:contract` violation both produce a **top-tier `violation`** of equal gate strength; they differ only in `governed_scope` metadata.
- **Promotion lands + stamps:** a promoted edge appears in the empirical graph (PASS-eligible) **and** carries the `origin=promoted` stamp; PASS-eligibility is decided by graph membership, the stamp is never consulted for PASS.
- **Associative never PASSes:** an `g:experience`-only edge on a destructive fire is **not** PASS-eligible (→ ESCALATE), but *is* readable for the escalation framing payload.
- **`g:decision` is write-only:** no arm reads `g:decision` for a verdict; the accountability arm only probes its ternary writability and writes to it.
- **Substrate independence:** the `g:decision` contract (write-only, ternary-writability-probed) holds regardless of backing store — no P1 test or consumer asserts Postgres-vs-Dolt.

## 10. Ratification checklist

1. The **two load-bearing lines** (§0): the tier list and the tier-change invariant.
2. `g:contract` + `g:policy` **share the top tier** (provenance is the axis; governed-scope is metadata).
3. `g:struct` is a **separate** structural tier (not folded into `g:coupling`).
4. Promoted edges = **stamp-rides-edge into the justified tier**, no `g:promoted` graph.
5. `g:decision` = **write-only audit target**, ternary-writability-probed, reads-nothing, **substrate deferred to #30**.
6. The per-arm reach table (§6) and the PASS-eligibility rule (§7).

## 11. Out of scope (deliberately)

- **Which store backs `g:decision`** — deferred to the Dolt trigger (#30). P1 defines the role, not the substrate (§5).
- **Staleness budgets** (what makes `fresh` → `stale`) and the **accountability retry bound** — deferred to open decision #3; read from config (P0 §12), not bound here.
- **The full predicate/quad vocabulary inside each named graph** — the subject/predicate/object shapes per tier are a later detail; P1 fixes the *partition*, not the per-graph predicate schema.
- **Promotion mechanism internals** (Cognee → Tapeout → truth) — the Materials/Promote layer owns those; P1 only fixes *where a promoted edge lands and how it is stamped*.
- **Any implementation.** P1 is paper; ontology/gate code waits on ratification.
