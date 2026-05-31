# OpenKB & Forge — Decision-Grade Assessment for CHIPS CORTEX

**Author:** Research engineering pass
**Date:** 2026-05-31
**Scope:** Two OSS tools evaluated against CHIPS's actual architecture (deterministic context compiler; Python 3.13; pgvector + `nomic-embed-code` + flashrank + graphify + structural retrieval; Ollama local-first; Postgres/SQLAlchemy/Alembic). Priorities, in order: **(1) determinism, (2) local-first, (3) simplicity.**

Sources cited inline are the actual OpenKB/PageIndex/Forge source files and READMEs fetched during this assessment.

---

## 1. Executive Summary

**OpenKB / PageIndex — Verdict: BORROW IDEAS (skip the dependency).**
OpenKB (`VectifyAI/OpenKB`, Apache-2.0, v0.3.0, Python) is a CLI that compiles documents into a persistent markdown wiki and answers via two retrieval modes: full-text read for short docs, and **PageIndex** (its sibling package `VectifyAI/PageIndex`, MIT) — a *vectorless, LLM-reasoning tree search* — for long PDFs. PageIndex's core mechanic is sound and directly relevant to CHIPS's design-doc corpus, but **it is fundamentally non-deterministic and not local-first by default**: every retrieval is a multi-step agentic LLM traversal (5-6 LLM calls per query, 30s+ latency, default `gpt-4o`), which collides head-on with CHIPS priority #1 (determinism) and #2 (local-first). Adopting PageIndex as a runtime retriever would invert CHIPS's thesis. However, its **offline tree-index build** (a TOC-style hierarchical structure with node summaries, built once, citable by node ID) and OpenKB's **compile-once wiki / contradiction-flag / skills-export** ideas map cleanly onto real or near-term CHIPS gaps and are worth borrowing as *deterministic, pre-computed* artifacts.

**Forge / forge-guardrails — Verdict: DEFER + BORROW PATTERNS (revisit at Phase 4; do not add as a dependency now).**
Forge (`antoinezambelli/forge`, MIT, v0.7.2, **requires-python `>=3.12`, classifiers confirm 3.13 support**) is a reliability layer that makes small local models call tools accurately: a proxy/library that does deterministic **rescue parsing** of malformed tool JSON (fenced JSON, Mistral `[TOOL_CALLS]`, Qwen `<function>` XML → canonical `ToolCall`), **schema validation** of tool calls, a **synthetic `respond` tool** forcing the text-vs-toolcall decision, and a **WorkflowRunner** guardrail loop (StepEnforcer + ErrorTracker + ResponseValidator). It solves *zero* current CHIPS problems — CHIPS uses local models only for embeddings + compression, never tool-calling. But Phase 4 (Letta Coordinator + `cortex_submit_hypotheses`) implies a *local small model emitting structured output*, which is exactly Forge's domain. The single highest-value, lowest-risk piece — `rescue_tool_call` in `forge/prompts/templates.py` — is **pure deterministic regex/JSON parsing with no LLM call**, so it passes the determinism check and is a clean pattern to borrow. The proxy, WorkflowRunner, and `respond` tool are Phase-4-shaped and should be deferred, not adopted blindly.

---

## 2. OpenKB / PageIndex Deep-Dive

### 2.1 How PageIndex actually works (mechanics)

PageIndex is OpenKB's retrieval engine for long documents and a standalone package. It replaces embedding-similarity with **LLM reasoning over a document tree**. Two phases:

**Phase A — Offline tree-index build** (source: `pageindex/page_index.py`):
1. **TOC detection** — `find_toc_pages()` calls `toc_detector_single_page()` once per candidate page ("detect if there is a table of content in the given text").
2. **TOC extraction/transform** — `toc_transformer()` makes sequential LLM calls converting raw TOC text into structured JSON (with continuation calls for long TOCs).
3. **Page-index matching** — `toc_index_extractor()` maps TOC entries to physical pages.
4. **Verification/repair** — `verify_toc()` runs concurrent `check_title_appearance()` checks; failures trigger `single_toc_item_index_fixer()` per bad entry.
5. **Recursive structuring** — `process_large_node_recursively()` re-runs `generate_toc_init()`/`generate_toc_continue()` for oversized sections (defaults: max 10 pages/node, 20k tokens/node).
6. **Optional summaries** — `generate_summaries_for_structure()` + `generate_doc_description()` attach a summary to each node.

Build cost: **~5-20 LLM calls baseline, scaling with hierarchy depth and node count** (recursive splitting multiplies calls). Default model `gpt-4o-2024-11-20`; LiteLLM-pluggable. This is a one-time, amortizable cost — the resulting tree (titles + summaries + node IDs + text spans) is persisted.

**Phase B — Query-time tree search** (the non-deterministic part):
Retrieval is an **agentic loop**, not a single call. At each node the LLM is asked, given the query + path so far: "should I descend into this subtree?" It classifies nodes relevant/irrelevant, descends, fetches text from selected nodes, checks sufficiency, and may loop again. Measured characteristics from PageIndex's own writeups: **5-6 LLM calls for a query touching 5-6 nodes (≈5-6× a single vector retrieval + generation), and ≈30s+ latency per query**. Returns **node IDs + section titles** (high transparency / citable) rather than opaque top-k chunks. Claimed 98.7% on FinanceBench.

**Failure modes:**
- **Structure-dependence.** Quality hinges on a clean tree. Poorly-structured inputs (no headings, flat code files, malformed PDFs) degrade both build and traversal. TOC verification/repair exists precisely because extraction is error-prone.
- **Non-determinism.** Traversal is LLM-driven; same query can pick different branches across runs / model versions. No stable ranking guarantee.
- **Latency + cost.** 30s+ and 5-6 LLM calls/query make it unsuitable for an interactive context-compile hot path.
- **Cloud-by-default.** Requires an API key (`OPENAI_API_KEY` in examples); README shows no Ollama path. LiteLLM *can* point at a local endpoint, but a local 8B reasoning over a tree will be slower and less reliable at the relevance-classification step than `gpt-4o`.

### 2.2 Head-to-head vs CHIPS retrieval

CHIPS retrieval today: `nomic-embed-code` embeddings in pgvector → candidate recall → flashrank rerank, plus graphify (graph) and structural retrieval. All **deterministic given a fixed index**: same query + same index → same ranked results, sub-second, fully local.

**(a) Code corpus:**
- **Embeddings + structural + graph win decisively.** Code is not prose with a clean TOC. PageIndex's tree-build assumes heading/section structure; for source trees the "structure" is the call graph / module hierarchy — which CHIPS *already* captures deterministically via graphify and structural retrieval (and at build time via tree-sitter/griffe), with **zero per-query LLM cost**.
- PageIndex would **lose** here: it would re-derive, stochastically and slowly, a structure CHIPS already has precomputed and queryable.
- **Verdict (code): SKIP PageIndex.** No gap. CHIPS's structural + graph retrieval *is* the "reason over structure" idea, done deterministically.

**(b) Design-doc / long-form corpus:**
- This is where PageIndex's idea is strongest and where CHIPS is comparatively weak. Long design docs chunked into embeddings lose hierarchical context; a query about "the Phase 4 coordinator's write-back contract" benefits from knowing *where in the doc tree* the answer lives.
- But **runtime** PageIndex still fails the determinism + latency + local-first checks. A 30s, 5-6-LLM-call, possibly-cloud traversal does not belong in CHIPS's compile path.
- **The salvageable half is the offline tree.** Building a hierarchical TOC-with-summaries index over design docs **once**, persisting node IDs + summaries, is deterministic and local-first if built with `qwen2.5-coder` via Ollama. That artifact then feeds CHIPS's *existing* deterministic ranking — no per-query LLM traversal.
- **Verdict (design docs): BORROW the offline-tree idea; do NOT adopt runtime traversal.**

### 2.3 Hybrid worth considering — YES (recommended)

**Structural-tree candidates as an additional deterministic retrieval source feeding the existing reranker.**

Build (offline, during harvester enrichment) a hierarchical section tree over each long design doc: nodes = sections, each with a `qwen2.5-coder`-generated summary and a stable node ID (reuse the just-shipped `find:<content-hash>` ID scheme for stability). Persist in Postgres alongside existing artifacts. At retrieval time, emit **section-node candidates** (matched by embedding-similarity *of the node summary*, or by structural path) into the existing candidate pool, then let **flashrank** rank them against diff/file/memory candidates as usual.

Why this fits CHIPS:
- **Determinism preserved** — the tree is a precomputed artifact; query-time is still embed + rerank, no LLM traversal. Same query → same result.
- **Local-first preserved** — summaries generated locally via Ollama at build time.
- **Simplicity** — no new retrieval *paradigm*; just a new candidate *source* into an existing reranked pipeline. Blast radius is contained to the candidate-generation layer.
- Captures ~80% of PageIndex's design-doc benefit (hierarchical context + citable node IDs) at ~0% of its runtime cost/non-determinism.

This is explicitly *not* "adopt PageIndex." It is "borrow the offline hierarchical-summary-tree idea and wire it as a candidate source."

### 2.4 Other OpenKB ideas vs CHIPS gaps

- **Compile-once wiki ("knowledge compounds over time," `wiki/concepts/`, `wiki/summaries/`, `wiki/sources/`).** Directly aligned with CHIPS's *determinism* thesis (compile-once vs re-derive-per-query) and the harvester's enrichment model. CHIPS already compiles enriched artifacts; the *concept-synthesis* angle (one source touching 10-15 cross-linked concept pages) is a **partial gap** worth a design spike, but not a tool to adopt. **Borrow the pattern, not the code.**
- **Contradiction flagging.** Maps to a **real latent gap**: CHIPS has no mechanism to detect that two design docs / two findings disagree. With the new `find:<content-hash>` evidence IDs and the planned EvidenceBundle, a deterministic "flag findings whose claims conflict" pass is a natural future feature. OpenKB's implementation is undocumented (LLM-judged, so non-deterministic), so **borrow the concept; implement deterministically** (e.g., rule/assertion-level conflict detection over structured findings, not free-text LLM judgment). **Borrow.**
- **Skills export (`openkb skill new` → portable Anthropic Skill folders).** CHIPS already exposes capability to coding agents via the FastMCP bus; exporting a wiki/context subset as a portable Skill is a *distribution* feature, not a retrieval/determinism feature. Low strategic value for core CHIPS now. **Skip** (revisit only if CHIPS needs to ship portable context bundles to external agents).

---

## 3. Forge Deep-Dive

### 3.1 Mechanics (verified against source)

Forge is a reliability layer for self-hosted tool-calling. Three integration modes: **proxy** (drop-in OpenAI/Anthropic-API HTTP shim), **WorkflowRunner** (Python agent loop), **Guardrails middleware** (composable). Backends: Ollama, llama.cpp/llamafile, vLLM, Anthropic.

**Rescue parsing — `forge/prompts/templates.py::rescue_tool_call`** (the crown jewel):
Four sequential, **purely deterministic** strategies (regex + `json.loads`, **no LLM call**), returning canonical `list[ToolCall]`:
1. **Fenced JSON** — strips ```` ```json ```` fences (`re.sub(r"```(?:json)?\s*\n?", "", text)` then `re.sub(r"```", "", ...)`), brace-scans to isolate `{"tool": ..., "args": {...}}` (Forge + OpenAI shapes).
2. **Mistral** — `_MISTRAL_BRACKET_RE = re.compile(r"\[TOOL_CALLS\](\w+)\s*(?=\{)")`, then balanced-brace scan for args (handles nesting + escaped strings).
3. **Qwen XML** — `_QWEN_FUNCTION_RE = re.compile(r"<function=([^>\s]+)>(.*?)</function>", re.DOTALL)` + `_QWEN_PARAMETER_RE` for `<parameter=...>` values.
This function is the single most reusable, determinism-safe artifact in either repo.

**ResponseValidator** (`forge/guardrails/response_validator.py`): for a `TextResponse`, calls `rescue_tool_call(content, tool_names)`; on success returns canonical tool calls, else emits a `retry_nudge`. For a `ToolCall`, checks the name is in `tool_names`, else `unknown_tool_nudge`. Emits a `ValidationResult` (exactly one of `tool_calls` / `nudge`).

**Synthetic `respond` tool** (`forge/tools/respond.py`): a one-field Pydantic model `RespondParams(message: str)`. Injected when tools are present so a small model must *choose* `respond(message=...)` rather than emit bare text — "small local models (~8B) cannot be trusted to choose correctly between text and tool calls." In proxy mode it is injected automatically and stripped (converted to plain text) before the client sees it; in WorkflowRunner it is set explicitly as `terminal_tool`.

**WorkflowRunner** (`forge/core/runner.py`) + **Guardrails** (`forge/guardrails/guardrails.py`): the agent loop. Composes **ResponseValidator** (malformed output → retry), **StepEnforcer** (required steps / prerequisites before terminal tool), **ErrorTracker** (consecutive-failure / error-budget exhaustion). Two-method middleware contract: `check(response) → {execute|retry|step_blocked|fatal}` before execution, `record(executed) → done?` after. Failures are fed back as `MessageRole.TOOL` results ("tool failed → try something else") for self-correction. `run()` loops to `max_iterations`, raising `MaxIterationsError`.

**Integration shape:** proxy = zero-code, language-agnostic, runs as a separate HTTP service (operational surface); library (WorkflowRunner/Guardrails) = in-process Python, more control, more coupling.

### 3.2 Mapping onto CHIPS Phase 4 (Letta Coordinator + `cortex_submit_hypotheses`)

Phase 4 implies a **local small model emitting structured hypotheses** (and likely tool calls) into the EvidenceBundle write-back path. That is precisely the failure mode Forge addresses: small models produce malformed/non-canonical structured output. Component-by-component:

| Forge component | Phase-4 relevance | Determinism | Verdict |
|---|---|---|---|
| `rescue_tool_call` (regex/JSON repair) | **High** — repairs malformed structured output from local `qwen2.5-coder` into canonical form. Pure deterministic. | Deterministic ✅ | **Borrow the pattern now / adopt at Phase 4** |
| ResponseValidator (schema check + nudge) | **High** — validates `cortex_submit_hypotheses` payloads against schema; rejects unknown tools/fields. | Deterministic ✅ | **Borrow at Phase 4** |
| Synthetic `respond` tool | **Medium** — only relevant if the coordinator must choose text-vs-toolcall. If `cortex_submit_hypotheses` is the *only* sink (structured-output mode), this is unnecessary. | Deterministic ✅ | **Defer / likely skip** |
| WorkflowRunner (multi-step loop) | **Medium** — Letta itself is the orchestration layer; CHIPS may not want a *second* agent loop. Overlaps Letta's role. | Loop deterministic; model isn't | **Defer — evaluate vs Letta overlap** |
| StepEnforcer / ErrorTracker | **Medium** — useful budget/guardrail primitives if CHIPS runs its own loop; redundant if Letta owns the loop. | Deterministic ✅ | **Defer** |
| Proxy server | **Low** — adds a standalone HTTP service = operational surface, violates simplicity priority #3. CHIPS already calls Ollama directly. | N/A | **Skip** |

**Irrelevant to CHIPS:** the proxy's multi-protocol shim (OpenAI+Anthropic) — CHIPS is local-Ollama-direct; the Anthropic backend client — CHIPS bars cloud AI in the core path.

### 3.3 Recommendation

**Adopt-as-dependency:** No (not now, probably not ever). Forge is a young (v0.7.2), single-author project; pulling it in adds `pydantic`/`httpx`-level deps plus an evolving API surface for a problem CHIPS does not yet have.

**Borrow-the-patterns:** Yes — specifically the **`rescue_tool_call` deterministic-repair pattern** and the **validator+nudge retry contract**. These are small, well-isolated, MIT-licensed, and re-implementable in ~100-200 LOC tailored to CHIPS's exact `cortex_submit_hypotheses` schema. Vendoring the single `templates.py` rescue function (with attribution, MIT-compatible) is also acceptable if Phase 4 lands and the formats match CHIPS's local model output.

**Defer-until-Phase-4:** WorkflowRunner, StepEnforcer/ErrorTracker, `respond` tool, proxy — re-evaluate once the Letta Coordinator's actual structured-output contract exists, and specifically check for **loop-ownership overlap with Letta** before introducing WorkflowRunner.

**License / maturity / py3.13:** MIT ✅ (clean to vendor or depend on). Maturity: early, single-maintainer — argues for *borrow* over *depend*. **Python: `requires-python >=3.12` and classifiers list 3.13 → CHIPS's py3.13 requirement is satisfied** (verified in `pyproject.toml`). Deps minimal (`pydantic>=2`, `httpx>=0.27`).

---

## 4. Prioritized Recommendations

| # | Recommendation | Type | Rationale | Blast radius | Determinism check | Local-first check |
|---|---|---|---|---|---|---|
| 1 | **Build an offline hierarchical section-tree (TOC + per-node summary, stable `find:<hash>`-style IDs) over long design docs during harvester enrichment; feed nodes as a new candidate source into the existing flashrank rerank.** | Borrow (PageIndex idea) | Captures hierarchical-context + citable-node benefit for the doc corpus where embeddings are weakest, without a runtime LLM traversal. | Med (new harvester artifact + one new candidate source; ranking unchanged) | **PASS** — precomputed artifact; query-time is embed+rerank only, no LLM traversal | **PASS** — summaries via Ollama `qwen2.5-coder` at build time |
| 2 | **Borrow Forge's `rescue_tool_call` deterministic-repair pattern (regex/JSON, no LLM) for the future `cortex_submit_hypotheses` write-back.** | Borrow (defer activation to Phase 4) | Local small models emit malformed structured output; deterministic repair is the cheapest reliability win and is pure parsing. | Low (isolated parsing util; only on Phase-4 write-back path) | **PASS** — pure regex/JSON, no LLM, fully deterministic | **PASS** — operates on local model output |
| 3 | **Borrow Forge's schema-validate + retry-nudge contract for `cortex_submit_hypotheses` payloads.** | Defer (Phase 4) | Reject malformed/unknown-field hypotheses before write-back; bounded retries protect the EvidenceBundle. | Low | **PASS** — schema validation is deterministic | **PASS** |
| 4 | **Add deterministic contradiction-flagging over structured findings (conflict detection at the assertion level, NOT free-text LLM judgment).** | Borrow (OpenKB idea) | Real latent gap; aligns with new evidence IDs + EvidenceBundle. | Med (new analysis pass over findings) | **PASS** *only if* implemented as rule/structured comparison; **FAIL** if done by LLM judgment (OpenKB's likely approach) | **PASS** |
| 5 | **Treat "compile-once wiki / concept synthesis" as a design spike, not a tool adoption.** | Borrow (concept) | Reinforces CHIPS's compile-once thesis; concept cross-linking is a partial gap. | Low (design only) | N/A (design) | N/A |
| 6 | **Defer Forge WorkflowRunner / StepEnforcer / ErrorTracker / `respond` tool until the Letta Coordinator contract exists; check loop-ownership overlap with Letta first.** | Defer | Phase-4-shaped; risks a redundant second agent loop alongside Letta. | N/A | N/A | N/A |
| 7 | **Skip PageIndex as a runtime retriever.** | Skip | 5-6 LLM calls + 30s+/query + cloud-default = inverts determinism, local-first, and latency goals. CHIPS structural/graph retrieval already covers code structurally. | N/A | **FAIL** — stochastic LLM traversal | **FAIL** — cloud `gpt-4o` default |
| 8 | **Skip adopting OpenKB or Forge as runtime dependencies.** | Skip | Both young/single-maintainer; the value is in 1-3 isolated patterns, re-implementable with lower operational surface (priority #3). | N/A | — | — |
| 9 | **Skip OpenKB skills-export.** | Skip | Distribution feature; no core retrieval/determinism value now. FastMCP bus already serves agents. | N/A | — | — |

---

## 5. Open Questions / Validate Before Committing

1. **Design-doc tree value (Rec #1).** Run a small offline experiment: build section-trees over the existing CHIPS design docs with `qwen2.5-coder`, inject node-summary candidates into the reranker, and measure whether brief quality improves on doc-heavy tasks vs the current embeddings-only pool. If lift is marginal, drop it — embeddings + structural may already suffice.
2. **`qwen2.5-coder` summary quality for tree nodes.** Validate that local summaries are good enough for relevance ranking; PageIndex's results assume `gpt-4o`-grade summaries. Determinism note: even Ollama summary generation must be pinned (fixed model + seed/temperature 0) so the *artifact* is reproducible.
3. **Forge format coverage.** Confirm which malformed formats CHIPS's chosen Phase-4 local model actually emits. `rescue_tool_call` covers fenced-JSON / Mistral / Qwen; if CHIPS standardizes on a model with native structured-output (Ollama JSON mode / grammar-constrained decoding), rescue parsing may be **unnecessary** — grammar-constrained decoding is the *more deterministic* solution and should be evaluated first.
4. **Letta vs WorkflowRunner loop ownership.** Determine whether the Letta Coordinator owns the agent loop end-to-end. If yes, Forge's runner/enforcer/tracker are redundant; only the parsing + validation primitives (Rec #2/#3) survive.
5. **Contradiction flagging definition (Rec #4).** Define "contradiction" precisely over structured findings before building — a deterministic spec (conflicting assertions on the same entity/claim) is required to keep it out of LLM-judgment territory.
6. **License hygiene if vendoring.** If `rescue_tool_call` is vendored from Forge, retain the MIT notice/attribution; same for any PageIndex-derived tree-build code (MIT).

---

### Source references
- OpenKB: `VectifyAI/OpenKB` README (Apache-2.0, v0.3.0); commands `init/add/watch/lint/query/chat/skill new`; `wiki/{summaries,concepts,sources}`; `.openkb/config.yaml` LiteLLM `provider/model`.
- PageIndex: `VectifyAI/PageIndex` (MIT) README + `pageindex/page_index.py` (`find_toc_pages`, `toc_transformer`, `verify_toc`, `process_large_node_recursively`, `generate_summaries_for_structure`; defaults 10 pages/20k tokens per node; default `gpt-4o-2024-11-20`). Query-cost (5-6 LLM calls, 30s+) from PageIndex's own technical writeups.
- Forge: `antoinezambelli/forge` (MIT, v0.7.2, `requires-python >=3.12`, py3.13 classifier; deps `pydantic>=2`, `httpx>=0.27`). Files: `prompts/templates.py` (`rescue_tool_call`, `_MISTRAL_BRACKET_RE`, `_QWEN_FUNCTION_RE`, `_QWEN_PARAMETER_RE`), `guardrails/response_validator.py`, `guardrails/guardrails.py`, `tools/respond.py`, `core/runner.py`, `core/inference.py`, `proxy/handler.py`.
