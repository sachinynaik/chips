# OpenInference — Decision-Grade Assessment for CHIPS CORTEX

**Author:** Research engineering pass (Claude, co-reviewed with Codex)
**Date:** 2026-06-02
**Scope:** `Arize-ai/openinference` (Apache-2.0) evaluated against CHIPS (deterministic context-compiler; sidecar; Python 3.13; already emits OTel traces + Prometheus metrics + DuckDB export). Priorities: **(1) determinism, (2) local-first, (3) simplicity, (4) sidecar-not-inline.**

Sibling notes: `open-bias-assessment.md`, `re-gent-assessment.md`, `gap-tool-map.md`. Companion design: `02_06_observability_analysis_architecture.md` (where this layer plugs in). Sources fetched 2026-06-02.

---

## 1. Executive Summary

**OpenInference — Verdict: ADOPT THE CONVENTIONS (emit spans manually); SKIP the auto-instrumentors; Phoenix-independent.**

OpenInference is *"a set of conventions and plugins complementary to OpenTelemetry to enable tracing of AI applications"* — i.e. **both** (a) OTel **semantic conventions** (a standardized span-attribute vocabulary) and (b) **instrumentation libraries**. It is **vendor-neutral**: *"natively supported by arize-phoenix, but can be used with any OpenTelemetry-compatible backend."* It defines span kinds incl. `LLM` / `RETRIEVER` / `RERANKER` / `EMBEDDING` / `TOOL` / `CHAIN` / `AGENT`, supports **manual instrumentation via decorators/helpers** (not only auto-instrumentors), Apache-2.0, Python-first (also TS/Java/Go), ~1,000★, actively released.

Why this is the right shape for CHIPS:
- The **conventions** are the asset. CHIPS already emits OTel; the win is replacing ad-hoc span-attribute names with a **standard schema** for its `RETRIEVER`/`RERANKER`/`EMBEDDING` work — making traces portable to *any* AI-aware backend (Grafana/Tempo now, Phoenix later if ever wanted) at near-zero lock-in.
- The **auto-instrumentors are not the asset.** They target third-party LLM client libs (OpenAI/LangChain/LlamaIndex) that CHIPS **does not use in the hot path** (CHIPS bars LLM generation in the core path, §North-star). So installing them buys nothing; emit OpenInference-conventioned spans **manually** from CHIPS's own retriever/reranker/embedding code.
- **Phoenix is NOT required** — confirmed. This is exactly what lets CHIPS adopt the trace vocabulary while **dropping Phoenix** (see `open-bias`/roadmap §7.3): OpenInference is the *wire format*; Phoenix is just one optional consumer.

**Net:** adopt the OpenInference **semantic conventions** as a thin attribute-naming standard for CHIPS's retriever/reranker/embedding/tool/chain spans; emit manually; keep CHIPS-domain concepts (constraints, evidence bundles, mastery) under **namespaced custom attributes** (OpenInference has no vocabulary for those). Do not install the auto-instrumentors. Determinism/local-first: both PASS (tracing is orthogonal to determinism; vendor-neutral OTLP is local-first).

---

## 2. Mechanics (verified 2026-06-02)

- **What it is:** OTel semantic conventions + instrumentation libs ("conventions and plugins... complementary to OpenTelemetry").
- **Vendor-neutral:** any OTLP-compatible backend; Phoenix is "one possible consumer," not required.
- **Span kinds / conventions:** `LLM`, `RETRIEVER`, `RERANKER`, `EMBEDDING`, `TOOL`, `CHAIN`, `AGENT` (folders also reference `reasoning`/`tool`/`agent` specs).
- **Instrumentation modes:** **both** auto-instrumentors (OpenAI/LangChain/LlamaIndex/…) **and** manual via decorators/helpers.
- **License / language / maturity:** Apache-2.0; Python 67% (+ TS/Java/Go); ~1,000★, 248 forks, ~1,889 commits, active releases.

---

## 3. Fit vs CHIPS

| Dimension | CHIPS | OpenInference | Implication |
|---|---|---|---|
| **Layer** | Already emits OTel + Prometheus | The *vocabulary* for those spans | Borrow the schema, not a new pipeline |
| **LLM span kinds** | LLM barred in hot path | LLM/AGENT conventions | Mostly N/A — use RETRIEVER/RERANKER/EMBEDDING/TOOL/CHAIN only |
| **Auto-instrumentors** | Doesn't use OpenAI/LangChain/etc. in core | Target those libs | **Skip** — emit manually instead |
| **Determinism** | Hard requirement | Tracing is orthogonal (observes, doesn't decide) | ✅ |
| **Local-first** | Cloud barred in core | Vendor-neutral OTLP, self-host any backend | ✅ |
| **Lock-in** | Avoids product lock-in | Open convention; keeps Phoenix optional | ✅ — strategic fit |
| **Domain concepts** | constraints, evidence bundles, mastery | no vocabulary for these | Use namespaced custom attributes alongside |

---

## 4. Borrow boundary

- **ADOPT:** the semantic-convention attribute names for `RETRIEVER` (query, retrieved docs, scores), `RERANKER` (input/output ordering, scores), `EMBEDDING` (model, dimensions), `TOOL` (MCP tool name/args/result), `CHAIN` (the brief-build span). Emit via OTel SDK with OpenInference attribute keys.
- **SKIP:** the auto-instrumentor packages (no target libs in the hot path); the LLM/AGENT span kinds (CHIPS isn't an LLM app).
- **ADD (CHIPS-specific):** namespaced custom attributes (e.g. `chips.constraint.*`, `chips.evidence_bundle.*`, `chips.repo.mastery`) for concepts OpenInference doesn't model — these ride the same spans.

---

## 5. Mapping onto CHIPS

| CHIPS operation | OpenInference span kind | Key attributes (standard + custom) |
|---|---|---|
| Brief build (top-level) | `CHAIN` | repo, tenant, scope, task-kind (`chips.*`) |
| Embedding step | `EMBEDDING` | model, dimensions |
| Candidate retrieval | `RETRIEVER` | query, retrieved IDs, scores |
| flashrank rerank | `RERANKER` | input/output order, scores |
| MCP tool call | `TOOL` | tool name, args summary, result summary |
| Governor / structural / evidence-bundle | `CHAIN` child + `chips.*` custom | decision, signals, bundle summary |
| Decision/reward (bandit) | span event + `chips.policy.*` / `chips.reward.*` | action, propensity, reward (CB design §2) |

This makes the **bandit decision/reward loop debuggable on the existing OTel→Grafana/Tempo surface** without Phoenix (CB design §5.2 cross-ref).

---

## 6. Recommendations

| # | Recommendation | Type | Determinism | Local-first |
|---|---|---|---|---|
| 1 | Adopt OpenInference **semantic conventions** for CHIPS's retriever/reranker/embedding/tool/chain spans; emit **manually** via the OTel SDK | Borrow (conventions) | PASS | PASS |
| 2 | Carry CHIPS-domain concepts (constraints, evidence bundle, mastery, policy/reward) as **namespaced custom attributes** (`chips.*`) on the same spans | Build | PASS | PASS |
| 3 | **Do NOT** install the auto-instrumentor packages (no target libs in the hot path) | Skip | — | — |
| 4 | Treat the convention as a **thin attribute-naming standard**, not a hard dep — pin/snapshot the attribute keys CHIPS uses so an upstream spec change doesn't churn CHIPS | Borrow (guarded) | PASS | PASS |

---

## 7. Open Questions / Risks

1. **Spec churn.** OpenInference conventions evolve; coupling span schema to a moving spec has minor churn risk → mitigate by snapshotting the specific attribute keys CHIPS uses (Rec #4), treating it as convention not dependency.
2. **Partial fit.** OpenInference models LLM-app shapes; CHIPS's domain (constraints/evidence/mastery) has no standard vocabulary → the `chips.*` custom-attribute namespace must be designed deliberately (do it in the observability design doc).
3. **No backend by itself.** OpenInference is only the vocabulary — it does not provide dashboards/analysis. Those come from Grafana/Tempo/Superset (`02_06_observability_analysis_architecture.md`).
4. **Manual-emission discipline.** Without auto-instrumentors, span coverage depends on CHIPS code emitting them consistently — needs a small helper module + review-gate check so spans don't silently go missing.

---

### Source references
- OpenInference: `Arize-ai/openinference` (Apache-2.0; conventions + instrumentors; vendor-neutral, Phoenix optional; span kinds LLM/RETRIEVER/RERANKER/EMBEDDING/TOOL/CHAIN/AGENT; manual + auto instrumentation; Python-first; ~1,000★). github.com/Arize-ai/openinference.
- CHIPS internal: `open-bias-assessment.md` (Phoenix relationship), roadmap §7.3 (observability architecture, Phoenix dropped), `02_06_contextual_bandit_design.md` §2/§5.2 (decision/reward spans, mastery surfacing), `02_06_observability_analysis_architecture.md`.
