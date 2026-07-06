# CHIPS — Stack Role Inventory (Draft)

**SIGNED OFF (owner decision, 2026-07-06 — recorded as amendment A13).** Rulings, after
grounding the register rows the draft couldn't read (`chips-component-decision-register.md`
§4.7/§4.8): **Dolt** = target-adopt (role stands: versioned ground-truth for Materials),
gated on "Materials projection work begins" (same gate as A5 #12). **Meilisearch** = CHIPS
keeps its claimed Cortex-Retrieve lexical role; the running instance is machine-shared
substrate. **txtAI** = REMOVED from the whole stack (owner statement 2026-07-06) —
superseded by the unified chat/search architecture (shared retrieval core also serving
video-analytics text embeddings; diagrams in `~/Downloads/combined_unified_chat_search_
architecture.svg` + search/chat pipeline SVGs). **Redpanda** = REPLACED by NATS JetStream
(owner statement 2026-07-06); event-bus remains target-only, gated; the schema-registry
half of register §4.8 becomes an open row (buf gating stands alone). **Timescale** =
unchanged (OLAP fallback behind DeltaX, gated on #12). Register rows updated in place with
dated notes.

*(Original draft header: DRAFT — for owner sign-off (A5 #6). Drafted 2026-07-05.)*

> Scope: register OD-8, closed per `chips-component-decision-amendments.md` A5 #6 as
> "inventory pass against A0." This document only inventories claimed roles against the
> read set below and A0's built/target split — it does not adjudicate adopt/reject.
> Read set for this pass: `docs/adr/A0-architecture-reconciliation.md`,
> `docs/design_docs/18_06/chips-execution-decision-sheet.md`,
> `docs/design_docs/05_07/chips-component-decision-amendments.md`,
> `docs/implementation_tracking.md`. The component decision *register*
> (`docs/design_docs/18_06/chips-component-decision-register.md`, the actual source of OD-8's
> row) was **not** in the allowed read set for this pass — several rows below are therefore
> marked "not grounded in read set" rather than cited to a doc this pass didn't open.

## Stop-condition check

A5 #6 (in `chips-component-decision-amendments.md`, line 143) reads:

> `| 6 | Stack-role verification — Dolt/Timescale/Meilisearch/txtAI/Redpanda: CHIPS-specific vs SpaceMate-wide | register OD-8 | inventory pass against A0 |`

This matches the task framing given to this pass exactly (tool list, CHIPS-vs-SpaceMate
framing, "inventory pass against A0" as the closing action). No contradiction found between
A5 #6 and the assigned framing — proceeding to write.

## Inventory table

| Tool | Claimed role in CHIPS docs (cite doc + section) | CHIPS-specific or SpaceMate-wide substrate concern | Current reality per A0 built-vs-target split | Recommended disposition (repo vocabulary) |
|---|---|---|---|---|
| **Dolt** | Not grounded in read set — no mention in A0, the 18_06 execution decision sheet, the 05_07 amendments, or `implementation_tracking.md`. | Unknown from this read set. | **Not-mentioned** — absent from A0 §4's target→current mapping and from `implementation_tracking.md`'s layer map. | **Defer** — no claim to evaluate until the source doc (register OD-8 row, or wherever Dolt was originally proposed) is located and read. |
| **Timescale** | `chips-component-decision-amendments.md` A5 gated-queue item **#12**: *"DeltaX vs Timescale (OLAP slot)"*, gate = *"Materials projection work begins"* (line 154). Framed as an OLAP-slot candidate for the Materials layer, not a general-purpose store. | **CHIPS-specific** as claimed (Materials/Assay projection work is a CHIPS-owned layer per the 18_06 decision sheet's "Materials layer priority" row and `implementation_tracking.md` L2's "early yield/fragility/assay substrate"). | **Target-only** — no Timescale instance runs on this machine (coordinator-verified); A0 §4 lists no OLAP store as built; Materials projection itself is not yet active (18_06 sheet: "Assay after V1.1/V1.2 signals exist"). | **Defer** — explicitly gated in A5 on "Materials projection work begins," which per the 18_06 sheet has not started. Do not evaluate DeltaX-vs-Timescale early. |
| **Meilisearch** | Not grounded in read set — no CHIPS doc in this read set claims a role for Meilisearch. | **SpaceMate-wide substrate concern**, not CHIPS-specific, per coordinator-verified machine context: a Meilisearch container runs today for `spacemate_chat_system`. | **Not-mentioned** in CHIPS's A0 target→current mapping; running on this machine, but for a different repo/product, not for CHIPS. | **Reject (as a CHIPS component)** — no CHIPS role is claimed or grounded; it is SpaceMate's search substrate, out of CHIPS's scope as currently documented. |
| **txtAI** | Not grounded in read set — no CHIPS doc in this read set claims a role for txtAI. | **SpaceMate-wide substrate concern**, not CHIPS-specific, per coordinator-verified machine context: a txtai image runs today for `spacemate_chat_system`. | **Not-mentioned** in CHIPS's A0 target→current mapping; running on this machine, but for a different repo/product, not for CHIPS. | **Reject (as a CHIPS component)** — same basis as Meilisearch: no grounded CHIPS role, already SpaceMate's tool. |
| **Redpanda** | Not grounded in **this** read set (not present in A0, the 18_06 sheet, the 05_07 amendments, or `implementation_tracking.md`). Per coordinator-supplied machine context, Redpanda appears elsewhere in CHIPS docs as a **target event-bus vocabulary item** — but that source doc was outside this pass's allowed files, so no citation is given here. | Claimed as CHIPS-specific (target event-bus role) per coordinator context, but unverified by this pass's read set. | **Target-only** by extrapolation from A0's general rule (§1.1: everything in `docs/design_docs/` not in the built-lineage table is target vocabulary, not running code) — no event-bus is listed as built anywhere in A0 §4 or `implementation_tracking.md`'s layer map. | **Defer** — confirm the actual citing doc/section before any adoption discussion; nothing runs today either way. |

## Open rows for the owner

All five resolved at sign-off 2026-07-06 (rulings in the header; the register WAS read at
sign-off and did materially differ from this draft's read-set view — Dolt and Meilisearch
both had claimed roles the draft couldn't see, confirming open row 5's suspicion):

1. **Dolt** — grounded: register §4.7 "adopt (target) — role RESOLVED." Ruling: stands, gated on Materials.
2. **Redpanda** — grounded: register §4.7 (streaming) + §4.8 (schema registry). Ruling: replaced by NATS JetStream; registry slot open.
3. **Meilisearch / txtAI** — ruled: Meilisearch keeps its CHIPS role on shared substrate; txtAI removed stack-wide.
4. **Timescale** — unchanged; eval criteria still to be pre-registered when #12's gate approaches (the one live remainder of this list).
5. **Register divergence** — confirmed and reconciled; register rows carry dated owner notes.

**Open rows remaining: 1** (Timescale eval criteria pre-registration — optional, non-blocking).

---

*Drafted per coordinator instruction, scope limited to the four named read files plus
coordinator-verified machine context. Nothing here is a decision until the owner signs off
per A6 (spike/inventory verdict governance: the agent's role ends at reporting, the owner
records every verdict).*
