# ADR-007: piia-engram — Reject as Dependency; Borrow the Admission-Gate Pattern

**Date:** 2026-06-05
**Status:** Rejected as dependency (pattern borrow recorded)
**Tool:** https://github.com/Patdolitse/piia-engram (local-first personal AI
identity/memory MCP server; Apache-2.0; 164★; solo author; 97 releases in months —
vanity versioning; self-reported metrics unverified)

## Context

piia-engram stores a developer's identity, preferences, standards, lessons, and
decisions as flat JSON/Markdown under `~/.engram/`, exposed via MCP so context follows
the user across tools (Claude Code, Cursor, Codex). It is *user-owned identity memory
above tools*; CHIPS is *repo/task/policy/evidence infrastructure*. Different layer.

## Decision

**Reject as a dependency** (wrong layer; solo-author maturity profile). Two patterns are
worth recording for future CHIPS work:

1. **Admission gate:** AI-suggested memory → human review → verified memory. Relevant
   if/when CHIPS builds human-in-the-loop review for write-back (cf. the Phase-1
   `cortex_submit_hypotheses` write-back path), where unverified model output must not
   become trusted evidence without an explicit promotion step.
2. **Cross-tool continuity as a companion:** it can coexist *alongside* CHIPS in the
   user workflow (user-owned preference memory) without touching CHIPS's evidence model.
   No CHIPS work required for that — it's a user-tooling choice.

## Timing & gates

Pattern 1 activates only if a human-in-the-loop memory-review surface is designed.
No standalone work item.

## Consequences

- + Layer boundary stays clean: CHIPS never absorbs user-identity memory concerns.
- − None (no dependency taken).
