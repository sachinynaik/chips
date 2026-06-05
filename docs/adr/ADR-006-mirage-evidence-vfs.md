# ADR-006: mirage — Watch for Heterogeneous Evidence Ingestion

**Date:** 2026-06-05
**Status:** Deferred (watch; revisit at their v1.0)
**Tool:** https://github.com/strukto-ai/mirage (unified virtual filesystem for agents;
Python+TS SDKs; Apache-2.0; 3.1k★; org-backed; v0.0.1, ~1 month public)

## Context

mirage mounts heterogeneous backends (S3/GCS, Drive/Docs, Slack/Discord, GitHub/Linear/
Notion, Redis, Mongo, SSH) as one bash-like virtual filesystem, with a two-layer cache
(index cache + file/byte cache, RAM- or Redis-backed). Well-engineered and genuinely
popular, but pre-1.0 with API churn certain.

## Decision

**Watch.** Do not adopt now. A *live* VFS over mutable remote services is in tension
with CHIPS's deterministic-snapshot ethos — anything entering the compile path must be
snapshotted, not read live. Bluntly: **mirage is irrelevant to CHIPS until a concrete
cross-service evidence-ingestion requirement exists.** No such requirement exists or is
planned; this ADR is a bookmark, not a backlog item.

## Purpose & fit (conditional)

If CHIPS later harvests evidence from heterogeneous sources (Slack threads, Drive docs,
external repos) — the "cross-system evidence harvester" direction — mirage is a ready
access abstraction, used strictly behind a snapshot boundary: mirage reads → CHIPS
snapshots → the compiler sees only the snapshot.

## Borrow now

The **two-layer index+byte cache pattern** is independently useful as a design reference
for any future CHIPS caching layer (cf. `diskcache` in the 27_05 roadmap, item 5).

## Timing & gates

Revisit when (a) mirage reaches v1.0/API stability AND (b) a concrete CHIPS
heterogeneous-ingestion requirement exists. Prefer pip/uv install pinned to a version;
avoid their curl-pipe-sh installer.

## Consequences

- + No premature dependency on a churning pre-1.0 API.
- − If the harvester direction arrives sooner, integration starts from zero (accepted).
