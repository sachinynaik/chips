# CHIPS demo runbook — 2026-07-17

How to demonstrate CHIPS harvesting real repos and compiling focused context, for the two
target uses: tracking emitter-codegen work (spacemate-backend #385) and tracking chat/FAQ work
(chat_system #464 + staec + building_proxy).

## What CHIPS is (the honest framing)

CHIPS is a **sidecar** that *harvests* a repo's git history + signals and *compiles a focused
ContextBrief* on demand. It **retrieves and focuses** the relevant work — it does not judge
"is the codegen deterministic" or run the chat itself. For #385 it accelerates the triage; for
the chat repos it lets you track/understand the work. It is not in either serving path.

## Prerequisites (already set up on this machine)

- **Ollama** running natively in WSL on the GPU (RTX 4070 Ti SUPER): `ollama serve` on
  `127.0.0.1:11434`, models `nomic-embed-text` (embeddings) + `qwen2.5-coder:1.5b` (compression).
- **chips-prod-postgres** container (port 5498) with one database per repo (one DB per repo —
  see known_limitations L13: the harvest cursor is global, so repos can't share a DB yet).
  **Harvested and demo-ready:** `chips_backend` (181 commits), `chips_staec` (216),
  `chips_bproxy` (298). **`chips_chat` is provisioned but not yet harvested** —
  spacemate_chat_system is large (1.1k commits) and its harvest is deferred; the N+1
  cochange-entropy query pathology that made it crawl is fixed (memoized per-file read), so a
  re-harvest is fast when we return to it. The chat/FAQ (#464) use case is already shown below
  via staec (parking) + bproxy (building) + backend.
- Pre-warm the compressor once before compiling briefs (first call cold-loads the model):
  `curl -s http://127.0.0.1:11434/api/generate -d '{"model":"qwen2.5-coder:1.5b","prompt":"warm","stream":false}' >/dev/null`

## Demo 1 — "CHIPS is tracking these repos" (harvest status)

Per-repo readout: commits ingested, memories compiled, history span, top contributors, recent work.

```
wsl -d Ubuntu-24.04 -- bash scripts/ops/chips-harvest-status.sh chips_staec
wsl -d Ubuntu-24.04 -- bash scripts/ops/chips-harvest-status.sh chips_backend
wsl -d Ubuntu-24.04 -- bash scripts/ops/chips-harvest-status.sh chips_bproxy
```

## Demo 2 — "CHIPS compiles a focused brief on demand" (the marquee)

Embed the task → pgvector-retrieve the most relevant harvested commits → rank → compress → govern.

Use-case 1 (spacemate-backend #385 — emitter codegen determinism):
```
wsl -d Ubuntu-24.04 -- bash scripts/ops/compile-brief-demo.sh chips_backend \
  "V4 to V5 emitter-based deterministic code generation"
```

Use-case 2 (chat / building domains):
```
wsl -d Ubuntu-24.04 -- bash scripts/ops/compile-brief-demo.sh chips_staec \
  "parking floorplan occupancy colour modes"
wsl -d Ubuntu-24.04 -- bash scripts/ops/compile-brief-demo.sh chips_bproxy \
  "IFC building-proxy corpus and mesh-to-asset resolution"
```

Each prints: the task, its classified kind, retrieval latency, the exact commits pgvector
surfaced, the governor decision, and the qwen-compressed context summary. The strong point to
show: **the retrieved commits are semantically on-target for the task**, and the summary is
focused, not a raw dump.

## Live querying (optional) — the MCP server

`chips.mcp.bus` exposes the tools (memory search, git, brief, diffs, contracts, …) over ONE
database. Point `CHIPS_DB_URL` at a repo's DB and connect an MCP client (Claude Code itself):
```
CHIPS_DB_URL=postgresql://postgres:postgres@127.0.0.1:5498/chips_backend \
OLLAMA_BASE_URL=http://127.0.0.1:11434 uv run python -m chips.mcp.bus
```

## Known boundaries to state up front

- Retrieval/compile only — CHIPS does not verify determinism or run chat (sidecar, by design).
- One DB per repo until the harvest path is tenant-scoped (known_limitations L13).
- Harvest is per-commit signal computation + batched embed. Two large-repo pathologies were
  fixed this cycle: co-change pairing is capped at 100 files/commit (a bulk/generated commit
  no longer explodes into tens of millions of O(N²) pairs), and per-file co-change entropy is
  memoized per batch (no more N+1 re-reads). Both are what make big repos harvestable.
