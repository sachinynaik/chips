# CHIPS — Reversible Compression Note (v1.0, 2026-06-20)

> **What this is.** A target-lineage design note for CHIPS' reversible compression contract.
> Governed by `A0-architecture-reconciliation.md` for built-vs-target reading and by the
> 2026-06-20 execution decision to finalize compression before Track 1 feature code. This note
> records the purity boundary, the allowed projection mechanics, and the companion-tool posture
> (Headroom/RTK/zap/lean-ctx) without committing CHIPS core to any external compression dependency.

---

## §0 — Purity boundary (load-bearing; this section precedes all mechanics)

CHIPS may emit compressed, lossy, agent-facing projections for context economy, but it must never
treat compressed material as evidence-grade truth. Any gate, assay, audit, replay, or evaluation
path must resolve through the original lossless artifact, not the compressed projection.
Compression is permitted on the wire; truth is always read from the source. Reversible pointer
tokens are therefore not merely an efficiency mechanism but a **safety boundary**: they permit
aggressive projection without allowing lossy representations to contaminate deterministic evidence,
policy decisions, or evaluation results. Compression is a projection-layer optimization, never a
truth-layer primitive — the same law that governs the Materials layer (a projection has its own,
lower purity and never overrides the versioned source) applied to the wire.

**Ban (negative invariant).** No persisted decision, score, fault signature, fragility value,
assay result, verifier outcome, or evaluation result may cite compressed text as its source
artifact. It may cite a stable original artifact ID or a pointer that dereferences to one — never
the compressed projection itself.

**Testable invariant (positive).** Every compressed projection used in a brief must be
dereferenceable to a stable original artifact ID. If dereference fails, the projection is invalid
for production use and must not enter any gate, assay, or audit path — it fails closed, not open.
Dereferenceability is verified at point of use, not only at compression time; a pointer that was
valid when written but dangles when read fails closed at the moment of resolution.

**Identity rule.** Pointer tokens are transport handles, not canonical evidence identities. The
canonical identity of any compressed projection remains the original artifact ID; the pointer
exists only to resolve the projection back to that identity at point of use.

---

## 1. Role in the architecture

Reversible compression belongs to the **projection layer** only:

- **Allowed:** agent-facing brief/context projections, shell/tool-output projections, log snippets,
  and compact context tiers where token economy matters.
- **Forbidden:** any truth path where CHIPS must reason over certified, evidence-grade material.

This note does not authorize a new truth store, a memory subsystem, or a wire-level proxy that
re-compresses already-compiled CHIPS briefs. It defines how projections remain safe.

---

## 2. The CHIPS-native mechanism

CHIPS should prefer a native reversible-compression contract over adopting an external platform.

### 2.1 Projection form

When compression drops or summarizes material, the emitted brief may replace the dropped region with
a compact **evidence-pointer token** whose semantics are:

1. this projection omits or compacts content for context economy;
2. the omitted content has a stable original artifact ID;
3. the projection can be dereferenced on demand back to the original, lossless artifact.

The pointer token format is an implementation detail; the contract is not. Any token format must be
content-addressed or otherwise stable enough that the dereference path is deterministic and auditable.

### 2.2 Resolution path

The pointer is resolved through a CHIPS-owned path:

- brief/projection cites pointer token;
- pointer token resolves to original artifact ID;
- original artifact ID resolves to the lossless artifact via CHIPS storage/tooling;
- the caller reads the original when truth is required.

This is compatible with an MCP dereference tool and with future operator tooling, but the
resolution contract is CHIPS-owned even if a companion tool inspires the pattern.

### 2.3 Source of truth

The original artifact remains authoritative:

- files remain truth for code/document artifacts;
- versioned state remains truth for Materials-layer facts;
- evidence/artifact IDs remain truth for brief evidence;
- compressed projections are disposable and reproducible.

---

## 3. Enforcement rules

### 3.1 Point-of-use hard stop

Any path that consumes evidence-grade material must resolve pointers at read time and hard-fail if
resolution fails. This includes:

- gate inputs;
- assay reads;
- audits and replay;
- verifier/evaluation inputs;
- any persisted decision or score computation.

There is no warning-only mode for these consumers.

### 3.2 Projection-only consumers

Agent-facing consumers may read compressed projections without immediate dereference when the task is
context economy rather than truth evaluation. If such a consumer needs fidelity beyond the
projection, it must dereference explicitly rather than treating the projection as complete.

### 3.3 No double-compression of compiled briefs

Once CHIPS has deterministically compiled a brief, no secondary proxy may re-compress that brief on
the wire in a way that mutates its semantics or breaks its pointer contract. Any external
compression tooling must either:

- operate **inside** the CHIPS-controlled compression step, or
- be confined to operator-loop outputs that are outside the truth path.

---

## 4. Tool posture (pattern vs dependency)

### 4.1 Headroom

What CHIPS keeps now:

- reversible compression / CCR-style pointer pattern;
- content-addressed dereference;
- lossy-on-wire / lossless-end-to-end discipline.

What CHIPS defers:

- Headroom as a library dependency inside `_compress`.

That dependency is revisited only if a concrete brief-size failure proves that the current CHIPS
compression path underperforms and a native pointer contract is insufficient.

### 4.2 lean-ctx

Borrow-only footnote. Relevant ideas:

- quality-gated lossy compression;
- stub-and-expand behavior;
- reproducible benchmark harnesses.

No dependency, no standalone ADR, and no direct authority over CHIPS compression decisions.

### 4.3 RTK / zap

These are companion tools for operator-loop output compaction, not CHIPS-core truth-path tools.
Their role is governed by ADR-003's bake-off and sits outside this note's core mechanism.

### 4.4 Pi

Not a compression tool for CHIPS core. Recorded only as a possible future **second CHIPS-brief
consumer** once the first vertical is proven, which makes it a test of agent-agnosticism rather
than a compression dependency.

---

## 5. Open implementation hooks

The first implementation questions are intentionally narrow:

1. pointer token shape and hash/ID scheme;
2. dereference API/tool surface;
3. where original artifacts are stored and how retention is governed;
4. which brief sections may legally emit pointers;
5. what production tests prove the fail-closed invariant.

This note locks the safety property before any of those mechanics are built.

---

## 6. Non-goals

- No external compression platform adoption by default.
- No proxy-layer double compression of compiled CHIPS briefs.
- No use of compressed material as a truth-path input.
- No auto-promotion or “learning” side effects from compression tools into CHIPS truth/memory.

---

## 7. Relationship to the rest of the architecture

This note is the compression-layer instance of the same architectural law used elsewhere:

- files are truth; indexes are derived;
- versioned state is truth; projections are derived;
- lossless artifacts are truth; compressed projections are derived.

Compression therefore does not introduce a new exception to the architecture. It extends the
existing purity law to one more derived layer.
