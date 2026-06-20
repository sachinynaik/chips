# Chips — Command-Chip Spec (v0.3 sketch)

> **v0.3 changes:** added the **placement principle** (what lives in Git vs CRDT/AFFiNE);
> added **context compression** as a dispatch/context stage (compress for the agent, keep
> originals for audit), with the Headroom/RTK/lowfat/lean-ctx stack; corrected Pi as a
> harness (not compression); extended Credits + Watchlist.
>
> **v0.2 changes:** added the memory architecture (Graphify + Cognee + Zenith + AGE,
> with ownership rules); made runtime/dispatch **OS-aware** (PowerShell-first on Windows);
> wired Graphify/Cognee in as retrieval signals; added Helix as the edit/trigger surface;
> added Credits + a Watchlist to track prior art over time.

A **chip** is a unit of *executable* knowledge: a parameterized CLI command or an
agent prompt, stored as a markdown file, retrievable in one call, fireable through a
single contract, and fed back from real traces. This is the part the LLM-Wiki crowd
(Curator, link, matryca) does **not** do — they store knowledge, Chips stores commands.

Design stance (non-negotiables):

1. **Files are truth.** A chip is a `.md` file with YAML frontmatter in a git repo. The
   index (Meilisearch / pgvector / AGE) is a *derived, reconstructable cache* — same
   posture as Zenith over your trace store. Nuke the index, re-derive from files.
2. **One fire path.** Human CLI, MCP server, and every harness call the same
   `chip.dispatch` contract. Trust-tiering, provenance stamping, OS-aware shell
   selection, and audit logging live there once — not per surface.
3. **Harness mirrors are generated, never hand-edited.** `~/.claude/skills/<n>/SKILL.md`,
   `~/forge/commands/<n>.yaml`, etc. are *projections* of chips. Source of truth is the
   chip repo.
4. **Placement principle — convergence-tolerant → CRDT/AFFiNE; correctness-gated → Git.**
   CRDTs guarantee *convergence*, not *correctness*: concurrent edits always merge with no
   conflict, which for code means a silent, build-breaking, unreviewed result. A Git merge
   conflict is a *feature* — the system refusing to guess and forcing a human to reconcile.
   So prose, design docs, and whiteboards (worst case: an awkward sentence) live in CRDT
   surfaces like AFFiNE; Dockerfiles, configs, and **chips-as-files** live in Git, where you
   get the conflict gate, the reviewable commit, line blame, and CI. Chips are git-files for
   the same reason Dockerfiles are. (CRDT is fine as the *live transport* during pairing — à
   la Zed — but never as the *system of record* for correctness-gated content.)

---

## 0. Memory architecture — where chips get their memory

Four sources, **strict ownership**, so nothing fights:

| Source | Owns | Update semantics | Feeds |
|---|---|---|---|
| **Graphify** (+ Serena/Semble) | *what the code IS now* — symbols, refs, deps, call graph | derived, recomputed on change, **no history** | `structural` retrieval signal |
| **Cognee** | *what we LEARNED over time* — decisions, gotchas, rationale, failure modes | accumulated, evolving (remember/recall/forget/improve) | `recall` retrieval signal |
| **Zenith** | *what actually fired* — raw tool-call traces | append, FTS over `tool_name`/`tool_io_text` | the source chips are **promoted from** |
| **Apache AGE** | *chip ↔ chip edges only* | derived from chip `links` | `chip.context` neighborhood |

**The seam rule (the thing to get right):** Graphify reflects HEAD and is *ephemeral*;
Cognee is *cumulative*. **Never let Cognee ingest Graphify's raw structural dump** — it
will "remember" code that was refactored away. Cognee remembers decisions and learnings;
Graphify reflects current structure. A chip anchors to **both**: a structural anchor
(symbols/files it touches → Graphify) and accumulated wisdom (when/why it failed → Cognee).

**Compounding-with-time, concretely:** Cognee's Claude Code plugin hooks tool calls into
its knowledge graph at session end — so the learned-memory layer feeds itself automatically
as you work. Zenith stays the raw cache you *promote* curated chips from. The loop:
**Zenith (observe) → promote → curate → fire → Zenith (observe) → Cognee (learn).**

Keep AGE to chip-relations only; Graphify and Cognee are queried as **external signal
providers at retrieval time**, not as the chip store. That preserves "files are truth,
indexes are derived."

---

## 1. The chip

A chip is `chips/<project>/<name>.md`:

```markdown
---
id: 01J9Z3...                       # UUIDv7 (your correlation-ID standard)
kind: cli                           # cli | prompt | composite
name: redpanda-reset-consumer-group
summary: Reset a Redpanda consumer group to earliest offset
tags: [redpanda, kafka, ops, reset]
project: spacemate                  # or `global`
status: curated                     # seed | curated | mature | deprecated

# --- executable payload (OS-aware) ---
runtime: shell                      # shell | claude-code | forge | codex
                                    # `shell` resolves to pwsh on Windows, bash on *nix
templates:                          # per-shell variants; dispatch picks by host OS
  pwsh: |
    rpk group seek {{group}} --to start --brokers {{brokers}}
  bash: |
    rpk group seek {{group}} --to start --brokers {{brokers}}
args:
  - { name: group,   required: true,  hint: "consumer group id" }
  - { name: brokers, required: false, default: "localhost:9092" }
allowed_tools: [Bash(rpk:*)]        # for prompt/composite chips routed to a harness
trust_tier: surgeon                 # safe | augmented | surgeon  (gates firing)

# --- provenance (made_by:: analog) ---
made_by:
  author: agent:claude-opus-4-8     # human:sachin | agent:<model> | agent:<harness>:<agent>
  origin: trace                     # trace | manual | imported
  source_trace_id: 01J9Y...         # Zenith trace this was promoted from
confidence: high                    # high | medium | low

# --- anchors (into the memory layer) ---
code_anchor: [src/ingest/occupancy.py#seek]   # Graphify symbols/files this touches
recall_tags: [offset-replay, idempotency]     # Cognee concepts to pull learnings from

# --- stats (maintained by dispatch) ---
created_at: 2026-06-15T...
updated_at: 2026-06-15T...
last_fired_at: 2026-06-12T...
fire_count: 7
success_count: 7

links: [01J9A..., 01J9B...]         # related chips (graph edges, AGE)
---

## What it does
Seeks a consumer group back to the earliest offset so a stalled pipeline can replay.

## When to use / caveats
Surgeon-tier: rewinds offsets and forces reprocessing. Never fire on a prod group
without confirming the downstream is idempotent.

## Examples
`group=ingest-occupancy brokers=redpanda-0:9092`
```

`kind`:
- **cli** — fires as a shell command (`runtime: shell`, OS-resolved).
- **prompt** — an agent prompt/skill; `runtime` routes it to a harness (`claude-code` → a
  generated `SKILL.md`, `forge` → a generated `:command`).
- **composite** — a prompt whose body fires CLIs via `allowed_tools` (the Claude-Code
  `allowed-tools: Bash(...)` + `!` pattern). The bridge between the two halves. *(V1)*

**Windows note:** `runtime: shell` resolves to **pwsh on your box**. The `templates`
map lets one chip carry both `pwsh` and `bash` variants where they differ — so the
"agent handed me a Linux command on Windows" failure is encoded out of existence: the
correct command is authored once, dispatch never asks the model to remember the OS.

---

## 2. Contracts

Four operations. Everything else composes from these.

### 2.1 `chip.compile(source) -> {created|updated, chip_id, diff}`  — capture → curate

Idempotent merge (Curator's compile-to-wiki). Source is a conversation span, a Zenith
trace, or raw text.

- Extract candidate command + args + intent; capture both shell variants if relevant.
- **Semantic dedup** against existing chips (pgvector). Near-duplicate → *update* it
  (bump stats, refine template) rather than create a sibling.
- Re-compiling unchanged input is a **no-op** (compare normalized templates + args).
- Returns a diff for human review before commit (mandatory gate for `surgeon`-tier
  merges, à la Curator's semantic-merge gate).

### 2.2 `chip.context(query, ctx) -> packed_context`  — retrieve (single call)

link's `get_context`: one call returns the best chips **and** their graph neighborhood,
budget-packed (ContextSlice). `ctx` carries current project/repo/host-OS/harness.

Multi-signal score (signal sources in brackets):

```
score =
    0.40 * semantic_sim   # [pgvector / txtAI]  query embedding vs chip
  + 0.18 * lexical_bm25   # [Meilisearch]       name/tags/summary/template
  + 0.15 * structural     # [Graphify]          is code_anchor near ctx's current code?
  + 0.10 * recall         # [Cognee]            learned relevance for recall_tags
  + 0.10 * recency        #                     exp decay over last_fired_at
  + 0.07 * success_rate   #                     success_count / max(fire_count, 1)
```

Top-K packed under a token budget → emit `.chips.md` (ContextSlice's output artifact)
for injection, or structured JSON for MCP. *(Graphify/Cognee signals are V1; MVP ships
the semantic+lexical+recency+success blend.)*

### 2.3 `chip.dispatch(chip_id, args, ctx) -> {result, trace_id}`  — fire (single plane)

The only place anything executes. Human CLI, MCP, and harnesses all route here.

1. Bind args; validate required.
2. **OS-aware shell select**: pick `templates.pwsh` on Windows, `templates.bash` on *nix;
   error loudly if the required variant is missing rather than silently running the wrong one.
3. **Trust gate**: `safe` → fire; `augmented` → fire + notice; `surgeon` → explicit
   confirm every time, even over MCP.
4. Route by `runtime`: `shell` → execute in the resolved shell; `claude-code`/`forge` →
   inject the generated command/skill into that harness.
5. **Compress the output (projection).** Run the result through the compression layer
   (§2.5) before it returns to an agent — RTK/lowfat for shell output, Headroom for
   JSON/files/logs — and redact secrets. The **full, uncompressed** output is what gets
   logged and traced; the **compressed projection** is what the agent sees.
6. **Stamp + log the original.** Append the *full* output to `log.jsonl` (append-only audit)
   **and** emit an OTel span (`chip.fire`, correlation_id = fire UUIDv7,
   `chip_id`/`project`/`tenant_id`/`host_os` in W3C baggage) → SigNoz. Update
   `fire_count`/`success_count`/`last_fired_at`.
7. Return the compressed result + the new `trace_id` (the fire is itself queryable in
   Zenith → Cognee; the original is retrievable from the audit log / Headroom CCR cache).

### 2.4 `chip.promote(trace_id) -> chip.compile(...)`  — close the loop

Pull a high-value tool call out of Zenith (`tool_name`/`tool_io_text` already FTS-indexed)
and feed it to `compile`. `source_trace_id` is stamped for back-reference. In parallel,
Cognee's Claude Code plugin is accumulating the same sessions into learned memory — so
promotion (curated, executable) and recall (learned, semantic) grow from the same stream.

### 2.5 Context compression — the projection layer

Compression sits between a chip's output and the agent's context. The governing rule is the
same as the placement principle: **compress for the agent, keep the original for the audit
trail.** The full output is truth (→ `log.jsonl` / Zenith / Headroom's CCR cache); the
compressed version is a *projection* the LLM reads. Nothing is lost — originals are
retrievable on demand.

Two insertion points:

- **Dispatch output** (`chip.dispatch` step 5) — the big win. A `cli` chip's output is the
  noisiest thing an agent reads. Route it through:
  - **RTK** — mature, 100+ dev commands, filter/group/truncate/dedup, tee-on-failure keeps
    the full log. Best default for shell output.
  - **lowfat** — composable pipe-based processors with per-command `.lowfat` pipelines,
    conditional on exit/size, and **built-in secret redaction** (pairs with your Presidio/
    DataBunker posture). Best when you want to hand-tune what survives per command.
  - **Headroom** — the umbrella: also compresses JSON, files, logs, and RAG chunks (not just
    shell), is **reversible (CCR)**, and aligns provider KV-cache prefixes. Use it as the
    outer layer; it already ships RTK and can delegate CLI context to **lean-ctx**.
- **Context packing** (`chip.context`) — Headroom's IntelligentContext / token-budget is an
  off-the-shelf alternative to hand-rolling the budget-packer in §2.2.

**Why this sidesteps your Windows caveat:** RTK/lowfat's *auto-rewrite hooks* need WSL on
native Windows. But Chips owns the fire path — `chip.dispatch` pipes output through the
compressor **programmatically**, so you get the savings on PowerShell without the agent-hook
mechanism. The single-fire-plane decision pays off again here.

**Redaction belongs in this stage too:** secrets get stripped from the projection before it
reaches the agent, while the (access-controlled) original retains them for audit.

---

## 3. Storage & index (mapping to your stack)

| Layer | Tech (yours) | Role |
|---|---|---|
| Source of truth | `chips/` markdown in git (`~/chips/` global + per-project) | the only durable write surface |
| Lexical | **Meilisearch** | BM25 over frontmatter + body |
| Semantic | **pgvector** (+ txtAI for embedding) | `semantic_sim` signal |
| Code structure | **Graphify** (Serena/Semble) | `structural` signal; resolves `code_anchor` |
| Learned memory | **Cognee** | `recall` signal; compounding cross-session memory |
| Chip graph | **Apache AGE** | chip `links` only; 1–2 hop neighborhood for `chip.context` |
| Trace cache | **Zenith** | promotion source |
| Audit / telemetry | **append-only `log.jsonl`** + **OTel → SigNoz** | every fire is a span |
| Harness mirrors | generated `SKILL.md` / `.yaml` | projections, regenerated on chip change |
| Workers | **DBOS** workflows | durable compile/promote/reindex (resume on crash) |

The index is rebuildable from files (`chip.reindex`), so an alpha-format change or a
corrupt vector store is a re-derive, not a data-loss event — the same insurance Zenith
gives you as a cache over the trace store.

---

## 4. Surfaces (who does what)

- **Helix** — human **surgical-edit** surface over `chips/` and coding notes (tree-sitter,
  LSP, ripgrep, fuzzy picker), plus a key-bound **CLI trigger** that shells out to the
  `chips` CLI. *Not* the brain, *not* the runtime — the keyboard. Fixes the things agents
  miss (the stray semicolon; the wrong-OS command) by hand.
  ```toml
  # config.toml — fire the chip on the current line via the chips CLI
  [keys.normal.space]
  c = ":pipe-to chips dispatch --stdin"
  ```
- **Claude Code / Forge / Codex** — agent harnesses; consume mirrored chips as skills/commands.
- **MCP server** — exposes `chip.context` + `chip.dispatch` to any MCP client; same fire plane.

---

## 5. Trust tiers (matryca) — what fires without a human

| Tier | Allows | Fire behavior |
|---|---|---|
| 🟢 safe | read-only / dry-run | fire silently |
| 🟠 augmented | reversible side effects | fire + notice |
| 🔴 surgeon | destructive (`rm`, drops, offset resets, restarts) | explicit confirm **every** fire, even via MCP |

Tier is on the chip, enforced in `dispatch`. MCP clients cannot bypass it.

---

## 6. Lifecycle

```
seed  ──(human reviews/edits)──▶  curated  ──(fire_count ≥ N & success_rate ≥ τ)──▶  mature
  │                                                                                     │
  └──────────────────────────── deprecated ◀──(superseded / success_rate < floor)──────┘
```

- **seed**: auto-promoted from a single trace, unverified. Never `surgeon`-fires without confirm.
- **curated**: human-reviewed.  **mature**: earned by use (auto).  **deprecated**: hidden from `context`, kept for audit.

---

## 7. Scope — MVP vs V1 (cut hard)

**MVP (prove the loop, Claude Code + Windows first):**
- Chip files, `kind: cli | prompt`, OS-aware `templates` (pwsh + bash).
- `chip.compile` — manual source only, idempotent merge + semantic dedup, review-diff gate.
- `chip.context` — Meilisearch + pgvector + recency + success_rate (**no** Graphify/Cognee/AGE yet).
- `chip.dispatch` — `shell` (pwsh/bash) + `claude-code` routing, OS select, trust gate, `log.jsonl` + OTel span.
- One harness mirror: `~/.claude/skills/`.  Helix trigger keybind.

**V1 (earn it):**
- `chip.promote` worker over Zenith; Cognee CC-plugin recall + Graphify structural signals.
- AGE neighborhood + single-call packed `chip.context` → `.chips.md`.
- `composite` chips; Forge/Codex mirrors; background maintenance daemon (matryca-style).

**Explicitly *not* doing:** a new notes UI, a bespoke datastore, or re-implementing the
LLM-Wiki knowledge layer. Adopt a wiki (link/Curator) if you want one; Chips is only the
executable layer on top, with Graphify/Cognee as its memory.

---

## 8. Open questions

1. **Arg typing** — freeform `{{var}}` vs typed args with validators (enum, path, regex).
   Typed buys safer `surgeon` fires + better autocomplete; costs schema weight. (Your
   Prisma/scaffolder instincts probably say typed.)
2. **Cross-project conflict** — when `compile` finds a near-duplicate across two projects,
   promote to `global` or keep siloed? (Curator silos by domain.)
3. **Mirror staleness** — push (regenerate on write) vs pull (mirror reads chips at harness
   startup). Push is simpler; pull avoids a generate step in the fire path.
4. **Cognee ↔ AGE boundary** — do learned relations ever get written back as chip `links`,
   or does Cognee stay a read-only recall signal? (Recommend read-only signal to start.)

---

## 9. Credits & prior art

This design borrows liberally. Sources, with what was taken:

**Conceptual origin**
- Karpathy "LLM Wiki" — https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f (the compounding-markdown-memory idea four of the repos below build on)

**Idea sources folded into this spec**
- The Curator — https://github.com/talirezun/the-curator (compile-conversation→permanent-page; graph-topology MCP; semantic-merge gate)
- link — https://github.com/gowtham0992/link (harness-agnostic install; single-call `get_context`; provenance + confidence + append-only log)
- ContextSlice — https://github.com/llcortex/ContextSlice (multi-signal scoring; token-budget packing)
- matryca-plumber — https://github.com/MarcoPorcellato/matryca-plumber (single mutation plane; `made-by::` authorship; trust tiers; OCC; background daemon)
- FrameCode-VibeWork — https://github.com/Sistema2D/FrameCode-VibeWork (artifact lifecycle states; ADR/troubleshooting-as-reusable-memory; snippets library)

**Agent harnesses referenced**
- aidermacs — https://github.com/MatthewZMD/aidermacs (transient-menu / command-palette inspiration)
- ForgeCode — https://github.com/tailcallhq/forgecode (`:`-prefix shell palette; `:suggest` NL→command; commands+skills file substrate)
- Helix — https://github.com/helix-editor/helix (edit/trigger surface) · Steel plugin (watch): https://github.com/mattwparas/steel
- Pi — https://github.com/earendil-works/pi (self-extensible coding-agent harness: unified LLM API + agent loop + TUI; another mirror target, *not* a compressor)

**Context compression** (the §2.5 projection layer)
- Headroom — https://github.com/chopratejas/headroom (umbrella layer: tool outputs, logs, RAG, files, history; reversible CCR; KV-cache align; `headroom learn`)
- RTK — https://github.com/rtk-ai/rtk (mature CLI-output compressor, 100+ commands, tee-on-failure)
- lowfat — https://github.com/zdk/lowfat (composable pipe-based CLI reducer; per-command `.lowfat` pipelines; built-in secret redaction)
- lean-ctx — https://github.com/yvgude/lean-ctx (CLI + MCP + editor-rules context tool; Headroom-delegatable)

**Memory / notes substrate**
- Cognee — https://github.com/topoteretes/cognee (the compounding learned-memory layer)
- SilverBullet — https://github.com/silverbulletmd/silverbullet · AI plug — https://github.com/justyns/silverbullet-ai
- Reor — https://github.com/reorproject/reor
- Anytype — https://github.com/anyproto/anytype-ts (org: https://github.com/anyproto)
- Foam — https://github.com/foambubble/foam
- TriliumNext — https://github.com/TriliumNext/Trilium
- Khoj — https://github.com/khoj-ai/khoj

**Cortex Chips foundation**
- Zenith — https://github.com/Polarityinc/zenith (filtered trace cache)
- Zap — https://github.com/bitan-del/zap (token-efficient hook output)

**Your existing code-intelligence tooling** (add canonical repo links yourself; Graphify/Semble may be private)
- Graphify · Serena · Semble

---

## 10. Watchlist (track over time)

What to watch in each, and why it matters to Chips. *(Not auto-monitored — re-check on demand.)*

| Project | Watch for | Why it matters |
|---|---|---|
| Helix | Steel plugin system merging to **mainline stable** | unlocks real scripting → a proper `:chip-fire` UX instead of shell-out only |
| Cognee | CC-plugin capture fidelity; self-host staying first-class; UI maturity | it's your compounding-memory layer; capture quality = recall quality |
| Zenith | retention/eviction; a log record type; on-disk format stabilizing | it's your promotion source and trust depends on it being a safe cache |
| link | stays stdlib-only? adds more harness installers? | the harness-agnostic install + single-call context are patterns you'd borrow |
| The Curator | compile-to-wiki + MCP graph-tool evolution | the capture→curate loop reference |
| matryca-plumber | generalizing beyond Logseq | the daemon + single-mutation-plane + authorship patterns |
| ForgeCode | **PowerShell-native** `:` integration | would remove the WSL/zsh caveat on your box |
| Headroom | reversible CCR maturity; `headroom learn` (failure-mining → CLAUDE.md/AGENTS.md) | the umbrella compressor; `learn` is basically an auto-`chip.promote` you'd want to study |
| RTK | **native-PowerShell** hook (vs WSL-only auto-rewrite) | removes the Windows hook caveat; you call it from dispatch anyway, but a native hook helps raw harness use |
| lowfat | composable-pipeline + secret-redaction maturity (very early) | the hand-tunable per-command reducer; redaction overlaps your PII posture |
| ContextSlice | maturity (very early) | the scoring/packing approach you're adapting |
| Anytype / Foam / TriliumNext / Khoj / SilverBullet | AI + graph maturity | fallback human-facing wiki if you ever want one over the chip files |
