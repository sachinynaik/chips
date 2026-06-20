# CHIPS - Dolt Harvester Spike Memo (2026-06-20)

> Purpose: decide whether CHIPS should accelerate Dolt for the **harvester substrate** now, instead of continuing to deepen the current Postgres-only implementation for git-history-shaped data. This memo is governed by `A0-architecture-reconciliation.md` for built-vs-target reading and should be read alongside `chips-execution-decision-sheet.md` and `chips-component-decision-register.md`.

---

## 1. Current state

### 1.1 Built today

The current Track-1 vertical is implemented on **Postgres**:

- `cortex_git_commits`
- `cortex_defect_corpus`
- `cortex_cochange_pairs`
- `cortex_file_signals`
- `cortex_file_signal_snapshots`

The write/read path is real:

- harvester ingestion writes commit history, defect evidence, co-change pairs, file signals, and snapshots
- retrieval reads those tables to compose defect history, defect density, fragility inputs, yield, and assay
- tests and migrations are all wired through Alembic + psycopg + temporary Postgres databases

### 1.2 Target language already in the design set

The 18_06 design set already resolved Dolt as a **target** store for versioned ground-truth state. The repo has **not** implemented that decision yet. Today’s code is still entirely Postgres-based for the harvester lane.

This means there is a real built-vs-target gap:

- **built today:** Postgres tables as both operational store and versioned-history stand-in
- **target language:** Dolt as the versioned truth substrate for state that benefits from commit/branch/diff semantics

---

## 2. The immediate trigger

### 2.1 What just happened

During verification of the first real Track-1 vertical, the code landed successfully and the broad suite went green. The unstable part was the **DB-backed test harness path**:

- temp database lifecycle
- migration ordering in targeted reruns
- repeated timed-out pytest subprocesses contaminating the session
- increasingly unreliable DB-backed verification once the session became dirty

### 2.2 What this does and does not prove

This does **not** prove that Postgres is the wrong data model for `cortex_git_commits`.

It **does** surface a useful strategic question:

> If the harvester lane is eventually supposed to become versioned, diffable, branchable ground-truth state, should CHIPS keep extending the Postgres-only path, or is this the correct moment to test Dolt on the narrowest useful slice?

So the motivation for doing this now is **not** “Postgres failed, therefore Dolt.” The motivation is:

1. the first meaningful harvester vertical now exists in real code
2. the data model is now concrete enough to evaluate, not hypothetical
3. every additional feature built on the Postgres harvester path increases migration cost later
4. the recent test friction is a forcing function to inspect whether the storage model itself should now move closer to the target

---

## 3. Why Dolt is plausible for this lane

The harvester substrate is unusually well-shaped for Dolt because it is **history-native** and **rebuild-oriented**.

### 3.1 The CHIPS harvester data has git-like semantics

These tables are not generic application state. They are all projections over repository history:

- raw commit facts
- extracted defect evidence
- co-change edges
- file-level evolutionary signals
- versioned snapshots of derived score fields

CHIPS repeatedly applies the same architectural law:

> files are truth; indexes and graphs are derived, reconstructable caches

Dolt fits that law better than ordinary Postgres because it gives a relational model with:

- table versioning
- commit semantics
- branchable state
- diffability between states
- point-in-time reconstruction as a first-class primitive

### 3.2 The specific CHIPS benefits

If Dolt is used only for the harvester substrate, the expected benefits are:

1. **Versioned score history becomes native rather than simulated.**
   Today versioned score snapshots are tables plus timestamps. In Dolt, the underlying state can itself be committed and diffed.

2. **Rebuildability is easier to prove.**
   CHIPS cares about derived-vs-truth boundaries. Dolt makes “what changed between harvest states?” and “can this view be reconstructed?” much more natural to inspect.

3. **Branch-and-compare becomes cheap.**
   Experimental harvest logic, widened defect-label queries, or alternative signal formulas can be computed on a branch and compared without mutating the baseline.

4. **Git-history-shaped storage and git-history-shaped reasoning align.**
   The substrate for commit-derived signals stops pretending to be generic operational state.

5. **Potentially simpler local repro for stateful harvesting experiments.**
   A repo-local, versioned SQL substrate may prove easier to reason about than spinning fresh temporary Postgres databases for every isolated experiment.

### 3.3 Why this is a better fit for harvester tables than for the whole system

This argument does **not** apply equally to all CHIPS state.

Memories, briefs, constraints, learning scores, and MCP operational data are application/ops state. The harvester substrate is different: it is temporal, reconstructable, commit-shaped, and heavily derived from repository history.

That is why a **split-store** architecture is plausible here:

- Dolt for versioned harvester truth
- Postgres remains for operational/transactional CHIPS state

---

## 4. Why Dolt should not be adopted as a panic response

Dolt is not a free fix for the current flaky verification path.

It may improve the long-term substrate for git-history-shaped data, but it will not automatically remove:

- bad pytest process cleanup
- hung sessions
- local subprocess contamination
- harness mistakes in fixture sequencing

If CHIPS chooses Dolt, it should do so because Dolt is better for the **harvester substrate’s semantics**, not because a dirty test session became frustrating.

That distinction is load-bearing. Otherwise the repo risks confusing:

- a **tooling/harness problem**
with
- a **storage-model decision**

---

## 5. Recommended scope for a Dolt spike

Keep the spike narrow. Do **not** migrate all of CHIPS.

### 5.1 Move only the harvester substrate

Candidate Dolt tables:

- `cortex_git_commits`
- `cortex_defect_corpus`
- `cortex_cochange_pairs`
- `cortex_file_signals`
- `cortex_file_signal_snapshots`

### 5.2 Keep these in Postgres

Remain in Postgres for now:

- `cortex_memories`
- `cortex_briefs`
- `cortex_brief_outcomes`
- `cortex_constraints`
- `cortex_memory_feedback_scores`
- `cortex_decision_log`
- any observability/ops-facing relational tables and views

### 5.3 Why this boundary is the right one

This split respects the real shape of the data:

- **Dolt side:** versioned, derived-from-repo-history, branchable analytical truth
- **Postgres side:** operational state, vectors, transactional app records, MCP-serving data

It also avoids dragging pgvector, memory retrieval, or constraints into the spike.

---

## 6. Concrete questions the spike must answer

The spike is successful only if it answers these specific questions.

### 6.1 Can Dolt represent the current write path cleanly?

The current harvester needs:

- append/update commit rows
- upsert defect evidence by SHA
- increment co-change frequencies
- update file-signal rows
- persist snapshot rows

The spike must show that this path is straightforward and deterministic in Dolt, not awkwardly simulated.

### 6.2 Can CHIPS rebuild the first vertical with equal or better integrity?

The current vertical already computes:

- high-precision defect history
- defect density
- co-change entropy
- generated/scaffolded tagging
- fragility inputs and score
- yield
- read-only assay

The Dolt spike must reproduce this vertical without reducing clarity or recoverability.

### 6.3 Does Dolt improve developer ergonomics for history-shaped experiments?

This is a real part of the decision. If Dolt is architecturally elegant but makes local iteration worse, the timing is wrong.

The spike must assess:

- local setup friction
- test/repro ergonomics
- branch/compare workflow for alternative harvest rules
- inspectability of rebuilds and state transitions

### 6.4 Does the split-store complexity stay tolerable?

CHIPS should not accept Dolt if it creates a second system with unclear boundaries.

The spike must prove the boundary can stay simple:

- Dolt owns harvester truth
- Postgres owns operational/app state
- crossing between them is explicit and narrow

---

## 7. Success criteria

The spike is a **go** only if all of the following hold:

1. The five harvester tables above can be modeled and queried cleanly in Dolt.
2. The Track-1 vertical can be rebuilt against Dolt with no loss of determinism or recoverability.
3. The rebuild/compare/branch workflow is materially better than the current Postgres-only harvester path.
4. The split-store boundary remains understandable and narrow.
5. The migration path does not force immediate rewrites of memory retrieval, vectors, constraints, or MCP surfaces.

---

## 8. Failure criteria

The spike is a **no-go for now** if any of these happen:

1. Dolt complicates the current write/read path more than it clarifies it.
2. Local/dev/test ergonomics get worse overall.
3. The split-store boundary becomes muddy and starts pulling app-state tables into the experiment.
4. The benefits are mostly aesthetic and not operationally meaningful.
5. The main gain appears to be “different infrastructure” rather than a better truth model for repository-history state.

---

## 9. Migration shape if the spike succeeds

If the spike is successful, the likely migration shape is:

1. Freeze new feature growth on the Postgres harvester lane.
2. Rebuild the five harvester tables in Dolt.
3. Repoint harvester ingestion to Dolt.
4. Expose a thin read boundary back into CHIPS retrieval/computation paths.
5. Leave operational CHIPS state and pgvector memory retrieval in Postgres.
6. Only after this boundary is stable, consider broader Materials-layer alignment around Dolt.

This keeps the adoption incremental and reversible.

---

## 10. Recommendation

**Recommendation: run a bounded Dolt spike now for the harvester substrate only.**

Not because Postgres “failed,” but because:

- the first real vertical now exists
- the target role for Dolt is already present in the 18_06 design language
- the migration cost will only increase from here
- the harvester substrate is the cleanest, highest-signal place to validate the choice

**Do not** treat Dolt as a rescue for flaky pytest behavior. Treat it as a deliberate evaluation of whether CHIPS should stop using Postgres as the long-term stand-in for versioned git-history state.

---

## 11. Immediate next step

If approved, the next artifact should be a **Dolt spike plan** with:

- exact schema mapping for the five harvester tables
- ingestion/write-path translation
- retrieval/query translation for the current Track-1 vertical
- local/dev/test workflow
- explicit rollback criteria

That spike plan should be implementation-facing and time-boxed. It is the correct next document before any Dolt code lands.
