## Design: `slots.json` as the contract between NestJS and the FastAPI chat backend

**TL;DR** — Per-domain `slots.json`, scaffolded by the emitter (sibling to `spec.json`), is the **single static contract** for what a domain's dialogue needs. It stays *total and dumb*: it declares the full slot vocabulary plus each slot's source/type/validation. Everything *conditional* (which slots are required for a given conversation) is resolved at runtime by rules, not baked into the file or smuggled into query params. Both backends conform to the generated artifact, and CI/BDD/fuzz/mutation gates fail loudly on drift. Dialogue = a typed FSM in FastAPI over the resolved slot set, terminating in our existing outcome codes.

The pattern here is deliberately the same one we're using for chips: a generated artifact as a boundary contract, files-are-truth, conformance enforced by gates that something independent can falsify.

---

### 1. Data layer — Prisma multiSchema (core + per-domain)

Backend-sourced slots resolve against a Postgres datasource split by schema, which also gives us the bounded-context client split we wanted for the 130+ model scaling problem.

```prisma
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
  schemas  = ["core", "valet", "visitor", "amenity"]
}

generator client {
  provider        = "prisma-client-js"
  previewFeatures = ["multiSchema"]
}

// shared, cross-domain entities
model Tenant   { /* ... */ @@schema("core")  }
model Building { /* ... */ @@schema("core")  }
model Vehicle  { /* ... */ @@schema("core")  }

// domain-specific
model ValetPass    { /* ... */ @@schema("valet") }
model ValetSession { /* ... */ @@schema("valet") }
```

- **`core`** holds entities every domain reads (tenant, building, vehicle, user).
- **Per-domain schemas** (`valet`, `visitor`, …) hold domain-only models.
- Each backend-sourced slot in `slots.json` names the schema/contract that provides it (see `provider.schema` below), so resolution is unambiguous: `tenant_id` → `core`, `has_pass` → `valet`. This is also what keeps domain clients bounded instead of one monolith client.

---

### 2. The typed `slots.json` artifact (emitter-generated, per domain)

The emitter scaffolds this with Claude Code from the upstream domain spec, exactly like `spec.json`. It is the **total static superset** for the domain. Note `otp` is *in the vocabulary* but its requiredness is governed by an activation **rule**, not by being present/absent.

```jsonc
{
  "domain": "valet",
  "version_number": 7,
  "generated_at": "2026-06-15T09:30:00Z",
  "emitter_spec_ref": "valet@3.2.0",          // upstream spec this was generated from
  "slots": {
    "vehicle_plate": {
      "type": "string",
      "source": "user",                        // ask the user
      "required": true,
      "validation": { "pattern": "^[A-Z]{2}[0-9]{1,2}[A-Z]{0,3}[0-9]{4}$" },
      "prompt_hint": "What's the vehicle number plate?"
    },
    "tenant_id": {
      "type": "string",
      "source": "backend-lookup",              // fetch, never ask
      "required": true,
      "provider": { "schema": "core", "contract": "TenantResolver.byContext" }
    },
    "has_pass": {
      "type": "boolean",
      "source": "backend-lookup",
      "required": true,
      "provider": { "schema": "valet", "contract": "ValetPass.lookup" }
    },
    "parking_charges": {
      "type": "money",
      "source": "computed",
      "required": false,
      "provider": { "schema": "valet", "contract": "ValetBilling.quote" }
    },
    "otp": {
      "type": "string",
      "source": "user",
      "required": false,                       // FLOOR — actual requiredness is rule-driven
      "activation": { "engine": "gorules", "rule": "valet.otp_required" },
      "validation": { "length": 6, "numeric": true }
    }
  },
  "outcomes": [
    "valet.checkout.success.completed",
    "valet.checkout.failure.backend_unavailable",
    "valet.checkout.failure.otp_exhausted"
  ]
}
```

Key fields, and why each exists:

- **`source: user | backend-lookup | computed`** answers the original open question ("how are slots retrieved"). The FSM uses it to decide **ask vs. fetch**: it asks for `vehicle_plate`, but *fetches* `tenant_id`/`has_pass` and *computes* `parking_charges`. A fetch failure is its own dialogue branch (`backend_unavailable`), never "ask the user for the parking charges."
- **`provider.{schema,contract}`** ties each backend slot to the Prisma schema + service contract that serves it — the link into the multiSchema layout above.
- **`validation`** is the runtime value contract, not just a name. This is what catches a backend that keeps the field name but starts returning the wrong shape.
- **`activation`** is how conditional requiredness stays *out* of the static file: a GoRules rule evaluated against live state. (`otp.required: false` is the floor; the rule can raise it.)
- **`outcomes`** map terminal FSM states to our `domain.action.result_class.condition` codes, so inputs (`slots`) + transitions (FSM) + outputs (outcomes) are three faces of one domain contract.

---

### 3. Query parameters — what belongs there (and what doesn't)

Query params select among **precomputed static variants of the total vocabulary**. They must never carry conditional business logic. The OTP example actually contains *two different things*, and they go to two different mechanisms:

✅ **Static per-place/tenant variant → query param** (the emitter generates the variant):
```
GET /slots/valet.json?building=BLDG_B      // BLDG_B variant: otp.activation statically disabled
GET /slots/valet.json?channel=whatsapp     // surface variant: which slots are askable on this channel
GET /slots/valet.json?locale=hi-IN         // locale variant
```

❌ **Runtime/conditional logic → NOT a query param** — this is a GoRules rule:
```
// "require OTP while handling more vehicles during checkout"
// depends on LIVE volume, not identity → valet.otp_required decision table, evaluated per session.
// Encoding this as ?otp=true smuggles a business rule into URL branching no gate can see.
```

Rule of thumb: if the variation is derivable from *identity/place/channel*, it's a static variant (query param OK). If it depends on *live state*, it's a rule.

---

### 4. Session hydration into Redis

On conversation start, the backend resolves the contract once and hydrates a session object in Redis keyed by `conversation_id`. The FastAPI FSM reads/writes this each turn instead of re-fetching — metadata is loaded once, not per-message.

```jsonc
// redis key: chat:session:{conversation_id}
{
  "conversation_id": "01J9X…",            // UUIDv7
  "domain": "valet",
  "slots_version": 7,                      // PINNED at session start (see §5)
  "tenant_id": "tnt_…", "building_id": "bld_…",
  "resolved_required": ["vehicle_plate","tenant_id","has_pass","otp"],  // AFTER GoRules activation
  "slot_values": { "tenant_id": "tnt_…", "has_pass": true },            // fetched backend slots, cached
  "fsm_state": "AWAITING_PLATE",
  "started_at": "2026-06-15T09:31:04Z"
}
```

What gets loaded at init: resolved tenant config, the **GoRules-resolved required-set** (`resolved_required`), and the fetched/computed backend slot values. The FSM then derives the next valid state from `resolved_required` minus what's filled, asks/fetches accordingly, and loops until the job is done. Session carries a TTL.

---

### 5. Version-driven schema reload (`generated_at` / `version_number`)

The chat backend caches each domain's `slots.json`. On session start (or a poll/watch), it compares its cached `version_number` / `generated_at` against the served artifact:

- **Newer artifact served →** reload it and rebuild the in-memory slot schema + FSM definitions for *new* sessions.
- **In-flight conversations keep their pinned `slots_version`** (from the Redis session). A mid-flight regeneration does **not** change the required-set under an active dialogue.

This is the same version-skew discipline as in-flight DBOS workflows: pin the contract version at the start, let new work pick up the new version. Without pinning, a `slots.json` regen could silently mutate an active conversation's required slots.

---

### 6. The gates — ship changes with confidence

Four checks, each catching a different failure class. The first three are necessary; the fourth proves the others actually bite.

1. **CI conformance (bidirectional, loud failure).**
   - NestJS must *provide* every `backend-lookup`/`computed` slot the file declares (rename/remove → fail).
   - FastAPI must reference *only* slots present in `slots.json` (no state asks for an undeclared slot → fail).
   - Catches: static vocabulary drift between the two backends and the file.

2. **BDD conversation-flow suite (`pytest-bdd` / behave).** Golden flows assert that the dialogue reaches the correct terminal **outcome code** given slot inputs.
   ⚠️ **The oracle must be independent of the emitter** — human-authored expected flows / golden transcripts, *not* regenerated from the same spec the slots come from. Generate the slots; don't generate the oracle, or it moves in lockstep with the bug and passes through it. This is our outside reference point.
   - Catches: slots present but flow deadlocks / wrong terminal state.

3. **Fuzz / property testing.**
   - **Schemathesis** against the NestJS slot-provider endpoints → fetched values conform to each slot's `validation` contract at runtime (not just names at build).
   - **Hypothesis** property tests on the FSM → *any* valid slot-value combination terminates in a declared outcome, never deadlocks.
   - **Conditional branches need their own scenarios:** `load-high → otp required → flow still terminates`. The OTP-by-load path only activates under load (i.e. exactly when it's hardest to debug) — without dedicated coverage it's a blind spot, same negative-space bias as cold paths.

4. **Mutation testing (nightly).** **Stryker** (NestJS/TS) + **mutmut** (FastAPI/Python) — proves the BDD + property suites actually *catch* breakage rather than merely execute. Guards against green-but-meaningless coverage. Nightly cadence; stale mutation score downgrades to coverage-only and that's declared, not silent.

---

### What this does NOT cover yet (declared residuals)

- **Live backend value drift beyond names** — a provider that keeps the field name but changes an enum's values. Mitigated by per-slot `validation` + Schemathesis, but flagged as a runtime risk class.
- **Conditional-branch coverage** — the activation-rule paths (OTP-by-load) are only as safe as their dedicated BDD/property scenarios. Static suite green ≠ conditional path tested.
- **Oracle independence** — the BDD suite only catches a *wrong generated artifact* if its source of truth is authored separately from the emitter. Holding this line is a discipline, not a check.

---

### One open fork to close before building

Which way does the emitter flow?

- **(A) Upstream domain spec → emits both** the NestJS DTO/controller contract **and** `slots.json` as two projections of one truth. They can't disagree by construction; CI conformance is a cheap backstop.
- **(B) `slots.json` is the root** the backend conforms to. Simpler, but only safe if the backend is also generated — otherwise the file becomes authoritative over hand-written backend code and can drift it.

Recommendation: **(A)** — same posture as harness mirrors being projections of chips. One truth, two projections, gates as backstop.
