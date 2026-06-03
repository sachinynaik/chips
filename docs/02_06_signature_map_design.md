# Signature-Map Compact Context — Design

**Status:** STAGED PROGRAM (proposal). Governed by `02_06_execution_ledger.md`. Restructured 2026-06-02 per Codex sign-off into Foundation → Activation → Optimization, with the `02_06_design_pressure_test.md` blocking fixes folded in. **Does not touch Slice A4.**
**Readiness:** Foundation (normalization contract + extractor decision + renderer spike) = **active**; Activation (compact-context tier) = **blocked on the spike proving value**; Optimization (public anchors, staleness) = **blocked**.

---

## 1. Purpose

Give CHIPS a **deterministic, compact projection of code** — symbol signatures without bodies — as a budget-efficient context tier and a deterministic fallback for the A4 flag-off world (when experimental retrieval layers are OFF). Pure-static, no LLM. CHIPS does not edit code (sidecar); it only *renders* and *references* it compactly.

## 2. Scope (phase-local)

**In scope (this program):** a closed normalization contract; a single extractor decision; a bodyless renderer (proved via spike); later, a compact-context tier, public hash anchors, and staleness feeds.

**Out of scope for the current (Foundation) phase:** the public `sig:` anchor and hash-anchoring (moved to Optimization — no consumer exists yet); multi-language support (Python-first); citable-evidence status (sigmap is context, not evidence — see §11). Preserved, not deleted.

## 3. Capability map

| Capability | Layer | Status | Prerequisite | Unlock evidence | Test gate |
|---|---|---|---|---|---|
| `normalization_contract` | Foundation | **active** | — | conformance matrix | cross-OS env-pinned golden tests |
| `extractor_decision` | Foundation | **active** | — | choose griffe **or** tree-sitter (not both) | n/a (decision) |
| `bodyless_renderer_spike` | Foundation (spike) | **spike** | normalization_contract | spike report: token win vs latency | byte-identical golden across 2 runs |
| `compact_context_tier` | Activation | **blocked** | spike proves net value | measured token win without latency regression | budget-precedence test (no double-count vs file-signals) |
| `sig_public_anchor` | Optimization | **blocked** | a real consumer + frozen contract | consumer exists (mastery churn feed) | anchor-stable-across-cosmetic-edits test |
| `staleness_feeds` | Optimization | **blocked** | public anchor + cache/trigger policy | latency budget defined | staleness-cost test |

## 4. Foundations (buildable now)

- **Normalization contract (the prerequisite for everything).** A **closed conformance matrix**: one input construct → one exact canonical output. Must enumerate: **symbol ordering** (define it — e.g. source order), whitespace, **line-endings + Unicode NFC**, type-annotation stance (decide `List` vs `list` vs `from __future__` stringization), default-arg handling, decorators, `@overload` (one anchor or many), PEP 695 generics, async / varargs / positional-only `/` / keyword-only `*`, return types, docstring-first-line rule. This is the GREEN for the spike's byte-identical test — **no rendering code before the matrix exists.**
- **Extractor decision.** Pick **griffe OR tree-sitter**, not both (two models with no tie-breaker = nondeterminism by ambiguity). If griffe: explicitly justify promoting a **dev-dep to the runtime/brief path** (it currently is dev-only per L10), and pin its version; scope **synthesized members** (dataclass/pydantic) in or out (they are griffe-version-dependent → hash churn). Forbid environment-dependent resolution (sys.path/load-order) or pin the resolvable surface — verified by a cross-OS golden.
- **Bodyless renderer spike.** Time-boxed: first test whether a **`bodies=False` toggle on the existing structural/compression renderer** suffices (avoid a new subsystem). Output a spike report: token win vs latency cost (griffe whole-module loads may cost more wall-clock than tokens saved — hold to the ranx-style "measure it" bar).

## 5. Activation path (what turns it on)

If the spike proves a **net token win without latency regression**, promote `compact_context_tier`:
- sigmap renders the **same selection** the existing structural/graph layer already produced (it does **not** add a retrieval source — selection stays single-owner).
- Integrated under the existing tiktoken-exact budget as a cheaper tier, with **one precedence rule** so sigmap (symbol-level) and file-signals (file-level) **never double-count the same file**.
- In the A4 flag-off world, this tier is the deterministic fallback projection (depends on the *core* structural pass surviving flag-off — verify).

## 6. Optimization path (later, each gated)

- **`sig_public_anchor`** — a stable `sig:<content-hash>` anchor for churn-durable references. **Only when a real consumer exists** (the CB mastery freshness feed is the first) **and** the normalization contract is frozen. **Namespaced so it can never be mistaken for the citable `find:` ID family** (sigmap is non-citable context, §11).
- **`staleness_feeds`** — re-extract + diff hashes to detect changed signatures, feeding CB freshness/churn. Requires a **trigger + cache-invalidation policy** (content-hash-keyed cache; grammar/griffe bump = cache-invalidating) and a **latency budget** (no per-brief full-module re-parse in the hot loop).

## 7. Dependency graph

| Dependency | Required by | Blocking condition if absent |
|---|---|---|
| `normalization_contract` (closed matrix) | bodyless_renderer → compact_tier → public anchor → staleness | non-deterministic projection; anchors churn on cosmetic edits |
| `extractor_decision` (one extractor, pinned) | renderer | ambiguity/version drift → non-reproducible hashes |
| spike proof (token win) | compact_context_tier | tier may cost more latency than it saves tokens |
| a real consumer (CB freshness) | sig_public_anchor | anchor has no use; premature spec risk |
| cache/trigger + latency budget | staleness_feeds | hot-path re-parse blows latency |

## 8. Invariant table

| Invariant | Why | Mechanism | Proof |
|---|---|---|---|
| Byte-identical projection (same input → same output) | flagship determinism claim | normalization conformance matrix + version pinning | cross-OS env-pinned golden tests |
| No environment-dependent resolution | cross-machine reproducibility | forbid sys.path/load-order dependence; pin resolvable surface | golden differs ⇒ fail |
| sigmap is context, not evidence | provenance clarity (consistent with A2a) | non-citable; anchor namespaced away from `find:` | review gate + naming check |
| No budget double-count | correct compaction | one precedence rule sigmap vs file-signals | budget-precedence test |

## 9. Data contract

- **Output:** a deterministic bodyless render per selected symbol; an **internal content hash** (cache/dedup) in Foundation. The **public `sig:` anchor is Optimization-only** (§6).
- **Versioning:** record extractor + grammar versions; a bump invalidates the cache and (later) re-anchors.
- **Non-Python contract:** **"no sigmap tier"** (explicit), not vague graceful degradation — mixed-language repos get consistent, signalled behaviour.
- **Sparse/edge:** dynamic/synthesized members scoped per §4; symbols the extractor can't resolve → excluded deterministically, not silently varied.

## 10. Failure modes

| Failure | How | Detection | Fallback |
|---|---|---|---|
| Non-deterministic hash | unspecified normalization / env-dependent griffe | cross-OS golden | block on conformance matrix; pin env |
| Cosmetic-edit churn | under-normalized (annotations/decorators) | anchor-stability test | tune normalization; anchor is Optimization-only |
| Useless hash | over-normalized (drops real signature change) | golden over real signature change | conformance matrix balances both |
| Budget double-count | sigmap + file-signal same file | budget-precedence test | precedence rule |
| Latency regression | griffe full-module re-parse in hot loop | spike latency measurement | toggle-only / cache; abandon if negative |
| Silent partial maps | non-Python ambiguity | "no tier" contract | explicit no-tier |

## 11. Decision log

- **Accepted:** sigmap = compaction **MODE**, not a citable EvidenceKind (consistent with A2a file-signals); pure layer (no builder/MCP coupling); single extractor; normalization contract precedes any code.
- **Deferred:** public `sig:` anchor, hash-anchoring, staleness feeds, multi-language, mastery integration.
- **Rejected:** griffe + tree-sitter both (no tie-breaker); `find:` as the normalization precedent (it hashes raw bytes, not a semantic projection); vague "graceful degradation"; minting a public `sig:` ID that mimics the citable `find:` family.

## 12. Implementation sequence (each step ends with an artifact + test gate)

1. **Normalization conformance matrix** → *artifact:* the matrix doc; *gate:* it is the defined GREEN for step 3.
2. **Extractor decision + version pinning + synthesized-member scope** → *artifact:* decision record; *gate:* cross-OS resolution golden.
3. **Bodyless renderer spike** (try `bodies=False` toggle first) → *artifact:* renderer + spike report; *gate:* byte-identical golden across 2 runs + 2 OSes; token-win-vs-latency measured.
4. *(Activation — blocked on spike value)* compact_context_tier + budget precedence → *gate:* no-double-count test.
5. *(Optimization — blocked)* public anchor (on consumer) → staleness feeds (on cache/latency policy).

## 13. Readiness exit criteria

- **Foundation → Activation:** conformance matrix closed; extractor chosen + pinned; **cross-OS byte-identical goldens pass**; spike shows **net token win without latency regression**.
- **Activation → Optimization (anchor):** a real consumer exists (CB freshness) **and** the normalization contract is frozen.
- **Optimization (staleness):** cache-invalidation + trigger policy + latency budget defined and tested.

### Cross-references
`02_06_execution_ledger.md` (authority), `02_06_design_pressure_test.md` §3 (findings folded in), `02_06_contextual_bandit_design.md` §9.3 (freshness consumes staleness), `research/gap-tool-map.md` (sigmap/dirac borrow), A2a decision (file-signals non-citable precedent).
