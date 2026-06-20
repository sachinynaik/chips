# Repowise Teardown — Borrow-List for CHIPS (build-brief addendum)

> A bounded teardown of `repowise-dev/repowise` (AGPL-3.0, v0.17.x, ~2.2k★) producing one
> decision: for each concept, **borrow / absorb / reject**, ranked by priority × fit, tagged
> by consumer and by cheap-projection-vs-new-build. We adopt **no code** (AGPL + heavy overlap);
> we mine **concepts and formulas** to implement natively against our own git + defect corpus.
> This is an addendum to `chips-build-brief.md`; it adds blast-radius edge classes and severity
> inputs, it does not change the locked architecture.

---

## 0. Framing — three rules that drive the ranking

**Rule 1 — Two consumers, ranked separately.** CHIPS code-intelligence serves two masters:
- **Internal (engineering):** blast radius, Signoff/DRC escalation, defect prevention. Test:
  *does it predict defects or prevent a bad fire?*
- **External (partners / customers / due-diligence / demos):** evidence the platform is
  enterprise-grade, scalable, controlled, reliable. Test: *does it credibly demonstrate rigor
  in language buyers recognize?*

A signal can be low-value internally and high-value externally (the structural health score is
the canonical example). Both are legitimate; they're ranked on separate axes below.

**Rule 2 — The cheap-projection gate (anti-sprawl).** External-consumer metrics must be *cheap
projections of data we compute anyway*, never their own subsystem. "It impresses customers"
can justify any feature; the discipline is: a demo metric is allowed **iff** it falls out of
something we already compute (AST we already parse, git we already have). The moment it needs
its own build, it's sprawl with a sales alibi — reject it.

**Rule 3 — Evolution beats structure for risk (the headline finding).** Repowise's own benchmark:
*the strongest defect predictors were evolutionary, not structural.* Our stack is structure-heavy
(Graphify, Glean, Serena, AST everything) and evolution-light (little git-history intelligence).
So the highest-value borrows are the **evolutionary** signals — and the structural ones are
re-cast as *external-consumer credibility*, not internal risk inputs. This is a directional
correction to our stack, not just a feature list.

---

## 1. The ranked borrow-list (master table)

Priority = internal × external × fit, after the cheap-projection gate. CHIPS home = where it lands.

| # | Concept | Decision | Internal | External | Build cost | CHIPS home | Compute against |
|---|---------|----------|----------|----------|-----------|------------|-----------------|
| 1 | **Co-change + change entropy** | **Borrow** | High | High | New (small) | `g:co-change` subgraph + DRC severity | our git history |
| 2 | **Defect-calibrated severity score** | **Borrow** | High | High | New (med) | DRC arm → Signoff escalation | our bug-fix corpus |
| 3 | **ADR mining + supersession/conflict lineage** | **Borrow** | Med | High | New (med) | `g:decision` subgraph in Oxigraph | our git + PR history |
| 4 | **Structural health score (25 biomarkers)** | **Borrow (external)** | Low | High | Cheap projection | Dashboard / demo layer | AST we already parse |
| 5 | **Git intelligence (hotspots, ownership, bus factor, reviewer-suggest)** | **Borrow (partial)** | Med | High | Cheap–med | severity + CASL governance | our git |
| 6 | **Cross-repo API-contract extraction** | **Borrow (concept)** | Med | Med | Absorb into slots/SR | contract graph (existing) | our repos |
| 7 | **Security posture as first-class artifact** | **Absorb** | Med | High | Cheap (over Semgrep) | DRC `touches_security` + demo | Semgrep we already run |
| 8 | **Multi-repo federated workspace/MCP** | **Defer** | Med | Med | New (large) | CHIPS sidecar (later) | our repos |
| 9 | **`get_risk` directive schema (will_break/missing_*)** | **Borrow (schema)** | High | — | Cheap (reference) | Signoff review output shape | — |
| 10 | **Freshness `_meta` envelope (index_age/stale_warning)** | **Already have** | — | — | — | dispatch freshness rule | — |
| 11 | **Task-shaped MCP tools (batch targets, one round-trip)** | **Borrow (design)** | Med | — | Cheap (design note) | CHIPS MCP surface | — |
| 12 | **Auto-docs / C4 / system-map** | **Absorb good ideas** | Low | Med | Overlap | existing Code dashboard | — |
| 13 | Dead-code detection | **Reject** | Low | Low | Overlap (Semgrep) | — | — |
| 14 | `distill` output compression | **Reject** | — | — | Overlap (RTK/lowfat/Headroom) | — | — |
| 15 | RAG search / wiki / CLAUDE.md gen | **Reject** | Low | Low | Overlap | — | — |
| — | *Determinism / reproducibility discipline* | **Confirm** | — | — | — | principle | — |

---

## 2. Tier 1 — borrow now (high value, both consumers, fills a real gap)

### 2.1 Co-change + change entropy → `g:co-change` subgraph + severity

**What it is.** Two distinct git-derived metrics, additive:
- **Co-change pairs** — files that change together in commits → *hidden coupling* no AST or
  trace sees (edit the validator, must edit the error-catalog; no static or runtime link).
- **Co-change entropy** — Shannon entropy over a file's co-change distribution. Low entropy =
  changes with one stable partner (benign). High entropy = changes with many scattered files
  (fragile). The literature validates this as a defect predictor (≈Pearson 0.54 to defect
  counts; combined with change entropy, significant AUROC gains).

**Why it's #1.** It's the one borrow that scores high on *both* consumer axes and fills a named
gap. Internal: it's the missing edge class in blast radius and a *validated* severity signal,
not a hand-wave. External: "we track hidden coupling and change-risk empirically" is a
sophistication story most vendors can't tell.

**CHIPS home.** A `g:co-change` named graph in Oxigraph (edges = co-change pairs above a support
threshold), confidence-tagged **below** contracts/traces but **above** pure associative — it's
behavioral evidence, weaker than a registered contract, stronger than an embedding guess. The
per-node **co-change entropy** becomes a *severity scalar* feeding the DRC arm: a fire whose
reach includes high-entropy files escalates the Signoff tier even at equal edge count.

**Implement against:** our own git log. Mine commit co-occurrence, compute entropy per file,
materialize edges + scores in the CI-fast clock (incremental per push, like the other extractors).
ORM/generated files need a filter (generated code co-changes spuriously).

### 2.2 Defect-calibrated severity score → DRC escalation input

**What it is.** A per-file/region risk score whose weights are *learned from a real defect
corpus* (bug-fix commits over a forward window), not hand-tuned. Repowise reports cross-project
mean ROC AUC ≈0.74 (up to 0.90), surviving a control for file size, out-discriminating raw churn
(+0.10) and prior-defect history (+0.12).

**Why it matters for CHIPS.** Blast radius answers *what a fire reaches*; this answers *how
dangerous the territory it reaches is*. Same edge count, very different risk if the reach is
three high-churn scattered-ownership regions vs three pristine ones. It's the **severity weight**
on blast radius — the dimension we don't currently have (mutation score in `g:mutation` is
narrower and costs test-suite runs; this is cheap and broader).

**The key discipline:** calibrate against **our own** bug-fix history, not repowise's OSS weights.
Our failure modes are enterprise/on-prem/conversational — different from general OSS. We have the
corpus by construction (our fix commits), same dogfooding advantage as everywhere else.

**CHIPS home.** A computed severity scalar per code region, read by the DRC arm at fire-time
(precomputed, CI-fast clock), escalating Signoff when high-severity regions are in the reach.
Depends on §2.1 evolutionary capture being underway (churn/co-change are its strongest inputs).

### 2.3 ADR mining + supersession/conflict lineage → `g:decision` subgraph

**What it is.** Architectural decisions mined from git history (commit messages, PRs, code
patterns — repowise cites ~8 sources), each tagged by evidence strength (verified / fuzzy /
unverified), linked to graph nodes, connected by **`supersedes` / `refines` / `conflicts_with`**
edges, and tracked for **staleness**.

**Why it's the strongest *external* asset in the repo.** Look at the vocabulary — it's *our
provenance model applied to decisions*. We provenance-tag code-structure edges; this is the same
discipline for the *why*. Almost nobody has it, and "every architectural decision is captured,
evidence-backed, linked to code, and tracked for staleness/conflict" is exactly the governance-
maturity story enterprise buyers and technical due-diligence want. It also has real internal
value: a chip's blast radius can surface **governing decisions** on the code it touches ("this
region is governed by ADR-014, since superseded — fire with caution").

**CHIPS home.** A `g:decision` named graph in Oxigraph — decisions as nodes, `supersedes`/
`refines`/`conflicts_with` as edges, evidence-strength + staleness as node attributes, linked to
the code nodes they govern. The "decision superseded but code still reflects the old one" and
"decision conflicts_with a later one" detections are drift checks in our existing idiom. Surfaced
at the Signoff review as a governance signal.

**Implement against:** our git + PR history. This is heuristic mining (verified/fuzzy/unverified
tiers handle the uncertainty honestly — same declared-confidence discipline as our edge tiers).

---

## 3. Tier 2 — borrow for the external consumer (cheap projections of data we have)

### 3.1 Structural health score (25 biomarkers) — the demo centerpiece

**The 25 biomarkers** (structural + evolutionary mixed): McCabe complexity, deep nesting, brain
methods, class cohesion (LCOM4), god classes, Rabin–Karp clone/duplication detection, untested
hotspots, function-level churn, code-age volatility, ownership dispersion, change entropy,
co-change scatter, prior-defect history, primitive obsession, developer congestion, knowledge
loss, blame-based function hotspots, test-quality smells, and more → one **1–10 score per file**,
with **trend snapshots** and **declining-/predicted-decline alerts**.

**Honest internal verdict:** low. It's the *weaker* defect predictor (Rule 3), and we have
mutation testing for the gate. Do **not** wire the structural score into the Signoff gate as a
primary input — that would be cargo-culting the demo metric into the safety path.

**Honest external verdict:** high, and legitimately so. A *defect-validated*, deterministic,
reproducible 1–10 score with trend lines is the single most demo-able artifact in the repo.
"Our platform scores its own code health against real defect history, deterministically, every
commit" is a credibility multiplier in exactly the language enterprise evaluators use. It passes
the cheap-projection gate because it falls out of the AST we already parse + git we already have.

**CHIPS home.** The Code dashboard / demo layer, **not** the gate. Compute it; show it; don't
let it escalate a fire. The evolutionary biomarkers within it (churn, co-change scatter, entropy)
*do* feed §2.1/§2.2 — so build the evolutionary ones for the gate and get the structural ones
nearly free for the dashboard from the same AST pass.

### 3.2 Git intelligence (hotspots, ownership, bus factor, reviewer-suggestion)

- **Hotspots (churn × complexity):** feeds §2.2 severity. Internal med, external high.
- **Ownership % / dispersion / bus factor:** low internal signal *now* (small team), rising as
  you grow; the *governance* angle is real — scattered ownership on a chip's reach is where the
  Signoff tier should be stickier, mapping onto your Keycloak/CASL personal→team gate.
- **Reviewer-suggestion** ("this PR touches a high-churn file owned by X → add X as reviewer"):
  maps directly onto CASL governance — a cheap, useful internal feature.
- **Bus-factor / contributor profiles:** classic due-diligence questions ("key-person risk?") —
  pre-computed answers are a strong external signal.

**CHIPS home:** severity inputs + CASL governance hints + dashboard. All cheap projections of
git we already have.

### 3.3 Cross-repo API-contract extraction — absorb into existing slots/SR work

Repowise extracts cross-repo API contracts and cross-repo co-change in workspace mode. The
*concept* aligns tightly with work you already have: slots.json, Redpanda SR + buf, Pact. So
don't adopt theirs — recognize that **cross-repo contract extraction is a thing you're already
building**, and the borrow is to make sure it's *graph-visible* (contract edges in Oxigraph
spanning repos) the way repowise makes co-change cross-repo. Med/med; absorb, don't build new.

### 3.4 Security posture as a first-class artifact — absorb over Semgrep

Repowise's security layer (local pattern scan, CVE-aware dependency risk, security anti-patterns)
is **partly overlap** — you run Semgrep and have stack security tooling. The *new concept* is
surfacing security as a **first-class posture score/artifact for demos and the DRC
`touches_security` flag**, not just a CI gate that passes silently. External value is high
(security posture is enterprise table-stakes). Build the *presentation/aggregation* layer over
tools you already run; don't adopt repowise's scanner.

---

## 4. Tier 3 — borrow the schema/design, defer the infrastructure

### 4.1 `get_risk` directive schema — borrow as a reference for Signoff-review output

Repowise's `get_risk(targets, changed_files)` returns a **directive block**:
`will_break` / `missing_cochanges` / `missing_tests` / `governance_risk`. That is *literally a
blast-radius gate output*. Borrow the **schema shape** as a reference for what your Signoff
review surfaces — it's a well-thought-out enumeration of "what the human needs to see before
approving," and it maps onto your DRC arms (will_break ≈ contract/structural violation,
missing_cochanges ≈ `g:co-change` gap, missing_tests ≈ coverage/mutation, governance_risk ≈
`g:decision`). Cheap; a design reference, not a build.

### 4.2 Task-shaped MCP tools — borrow the design principle

Repowise's tools are "designed around tasks, not entities" — pass multiple targets in one call,
get complete context back, collapse search→read→reason into one round-trip (their benchmark:
−70% tool calls, −89% file reads). This is a **design principle** for your CHIPS MCP surface:
`chips.search`/`chips.dispatch` and any blast-radius tool should be task-shaped and batch-capable,
not entity-shaped. Cheap design note; you're already MCP-native.

### 4.3 Multi-repo federated workspace / MCP — defer

SpaceMate *is* multi-repo (NestJS, FastAPI, Flutter, emitter, shared libs), so the concept fits
better than most — cross-repo co-change and federated queries are genuinely relevant. But it's a
*scaling* concern, not a first-vertical concern, and it's where complexity explodes (federated
MCP infrastructure). Defer the infrastructure; pull only the cross-repo *contract* thread (§3.3)
now. This is a `/simplify`-adjacent decision: don't build federation until single-repo CHIPS has
run a vertical.

---

## 5. Reject or absorb (overlap, not gap)

- **Dead-code detection** — Semgrep-adjacent; reject as a new build.
- **`distill`** — output compression; you've chosen RTK/lowfat/Headroom. Reject.
- **RAG search / auto-wiki / CLAUDE.md generation** — your stack (Qdrant/Meilisearch/txtAI) +
  not your need. Reject; absorb the *freshness-scoring / regenerate-on-commit / evidence-linking*
  ideas into the existing Code dashboard rather than as new features.
- **C4 / architecture dashboard** — overlaps your existing system-map/Code dashboard. Absorb the
  good ideas (evidence-linked, current-on-commit), don't rebuild.
- **Determinism / reproducibility discipline** ("zero-LLM, same input → same output, every
  comment reproducible") — not a feature, a *confirmation* of your determinism-first principle.

---

## 6. The capture-now imperative

The same logic as the conversation audit record: **the evolutionary signals are mined from git
history that is accumulating whether or not you compute them — but the *derived* co-change graph
and, critically, the *defect-calibration corpus* are things you want building from today.**

- The **bug-fix corpus** (which commits fixed defects, linked to the files they touched) is the
  training set for §2.2's calibrated weights. If you start labeling fix-commits now, you have a
  calibration corpus in months; if you wait, you reconstruct it painfully from log archaeology.
- The **co-change graph** (§2.1) is cheap to compute incrementally from each push; start the
  extractor early so the severity model has data when you wire it.

Neither requires the scorer to exist yet. Capture/label now, compute later — same discipline as
the audit record's "get the raw material right before you know exactly how you'll use it."

---

## 7. What this addendum deliberately does NOT do (investigation discipline)

Per the anti-sprawl rule and the "investigate deeply ≠ investigate endlessly" caution:

- It does **not** expand the architecture. Every Tier-1/2 borrow lands in an *existing* CHIPS
  structure (Oxigraph named graph, DRC arm, Signoff escalation, dashboard) — no new subsystem.
- It does **not** adopt any repowise code (AGPL + overlap). Concepts and formulas only,
  implemented against our own git/defect corpus.
- It does **not** treat external-consumer value as a blank cheque. Every demo metric passed the
  cheap-projection gate or it was rejected.
- It produces a *decision per concept*, not a list of admirations — the failure mode of a deep
  dive is increasing the option space; this closes it.

---

## 8. Open decisions to discuss (before building any of the above)

1. **Calibration cadence for §2.2.** The defect-risk weights need periodic re-fit against the
   growing fix corpus — same slow clock as mutation testing (nightly/weekly)? And the staleness
   threshold past which weights are flagged?
2. **Co-change support threshold (§2.1).** How many co-occurrences before an edge is "real" vs
   noise — and the generated-code filter so ORM/scaffolded files don't create spurious coupling.
3. **ADR-mining confidence gate (§2.3).** Verified/fuzzy/unverified is the right tiering — but
   does a `conflicts_with` between a fuzzy and a verified decision surface at the Signoff review,
   or only verified-vs-verified conflicts?
4. **External-metric surface boundary.** Which metrics live in the *demo/partner* dashboard vs
   the *internal* CHIPS gate — drawn explicitly, so a vanity metric never silently becomes a gate
   input (the §3.1 structural-score trap).
5. **Priority order to actually build.** Recommended: §2.1 (co-change capture) → §2.2 (calibrated
   severity, once corpus exists) → §2.3 (ADR mining) → §3.1 structural (nearly free off the same
   AST). The first is the foundation the rest depend on.
