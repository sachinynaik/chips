# SpaceMate Harvester Deployment Plan (PROPOSED)

Status: PROPOSED — nothing in this document has been executed. Every command,
container, and unit file below is a recommendation for the owner to review
and apply by hand. This closes HANDOFF Gap A: the CHIPS harvester currently
runs nowhere on this machine, so zero SpaceMate commit history is being
captured.

Scope note: this plan was authored by reading only
`src/chips/harvester/daemon.py`, `src/chips/harvester/ingestion.py`
(signatures only), `src/chips/harvester/embedding.py`,
`alembic.ini` / `migrations/env.py`, and a one-level listing of
`C:\sachinynaik\`. No other files were read, no code was changed, and
nothing was deployed.

---

## 0. Discrepancy found (read this before anything else)

`alembic.ini` line 89 has a **hardcoded placeholder** DB URL:

```
sqlalchemy.url = driver://user:pass@localhost/dbname
```

`migrations/env.py` (both `run_migrations_offline` and
`run_migrations_online`) reads the URL exclusively via
`config.get_main_option("sqlalchemy.url")` / `engine_from_config(...)`. There
is **no environment-variable override and no `-x` argument handling** in
`env.py`. This means `alembic upgrade head` will silently try to connect to
`driver://user:pass@localhost/dbname` unless the operator does one of:

- **(a)** Temporarily edit the `sqlalchemy.url` line in `alembic.ini` to the
  real target DSN before running `alembic upgrade head`, then revert it
  (or keep a separate `alembic.chips-prod.ini` copy pointed at the real DB
  and pass it explicitly with `alembic -c alembic.chips-prod.ini upgrade
  head`).
- **(b)** A small code change to `env.py` to read `os.environ["DATABASE_URL"]`
  and call `config.set_main_option("sqlalchemy.url", ...)` before the engine
  is built. This is a real code change, not configuration — flagging per the
  "minting vs checking" distinction; it should get its own tiny
  design-checkpoint + TDD slice, not be improvised here.

Recommendation: use **(a)** with a dedicated `alembic.chips-prod.ini` (never
edit the checked-in `alembic.ini` in place) as the immediate unblock; file
**(b)** as a follow-up task since every future migration run against a real
DB will hit this same gap.

---

## 1. The DB question (gates everything)

Confirmed: no standing chips Postgres exists. The only chips DB seen is the
throwaway `chips-testdb` (pgvector, port 5499) created/destroyed by the test
harness. A shared `pg-shared` Postgres container (spacemate-postgres image,
pgcron) already runs in WSL2 Ubuntu-24.04 for other projects.

### Option A — Dedicated chips pgvector container (own volume, own port)

Run a new, standalone Postgres+pgvector container, e.g.
`chips-prod-postgres`, with its own named volume and its own published port
(anything free — e.g. 5498, since 5499 is the test harness's ephemeral
port and should stay free for test runs).

Tradeoffs:
- **Isolation**: highest. Chips schema/extension churn, migrations, and any
  accidental `DROP`/`TRUNCATE` during CHIPS development cannot touch
  `pg-shared`'s other tenants.
- **Backup**: chips owns its own volume and its own backup/retention policy
  (currently none exists for chips data — this plan does not design one;
  flagging as a gap the owner should decide on separately).
- **pgvector availability**: guaranteed — same image family already used for
  `chips-testdb`, so the extension is known-good.
- **Migration ownership**: clean — only `chips`'s `alembic upgrade head`
  ever touches this instance's `versions/` history. No risk of two repos'
  migration histories colliding in one `alembic_version` table.
- **Cost**: one more always-on container + volume in WSL2.

### Option B — A database inside `pg-shared`

Create a new logical database (e.g. `chips_prod`) inside the already-running
`pg-shared` container.

Tradeoffs:
- **Isolation**: lower — shares the Postgres server process, memory, and
  disk I/O with whatever else lives in `pg-shared`. A runaway chips query
  or lock can affect other tenants.
- **Backup**: piggybacks on `pg-shared`'s existing backup cadence, if any —
  saves setup work but means chips's retention policy is whatever
  `pg-shared`'s is, not chosen independently.
- **pgvector availability**: **must be verified** — `pg-shared` runs the
  "spacemate-postgres image," not the pgvector image chips's test harness
  uses. If that image doesn't ship the `pgvector` extension, this option
  is blocked until the image is rebuilt/extended. This plan does not verify
  the image contents (out of scope of the files read); the owner must check
  (`\dx` inside `pg-shared`, or inspect its Dockerfile) before choosing B.
- **Migration ownership**: `alembic_version` table lives in the
  `chips_prod` database (Postgres namespaces this per-database), so no
  actual collision risk with other logical DBs in the same server — but
  operationally it's one more schema history to track inside a container
  the owner didn't build for chips.
- **Cost**: zero new containers.

### Recommendation

**Option A (dedicated chips pgvector container).** The isolation and
guaranteed-pgvector arguments dominate for a harvester that will run
continuously and write derived tables (cochange, defect corpus, file
signals, embeddings) — this is exactly the kind of write-heavy, schema-
evolving workload that should not share blast radius with `pg-shared`'s
other tenants. Option B only wins on "zero new containers," which is a weak
argument against an unverified pgvector dependency.

**Before the daemon starts**, migrations must be run to head against
whichever DB is chosen:

```
alembic -c alembic.chips-prod.ini upgrade head
```

(using the discrepancy-(a) workaround from Section 0).

---

## 2. Daemon placement

`HarvesterDaemon.__init__` (src/chips/harvester/daemon.py:19-33) takes:

```python
HarvesterDaemon(conn: psycopg.Connection, embedder: OllamaEmbedder,
                 repo_path: str, poll_interval: int = 60, ...)
```

This confirms the established fact: **one instance per repo_path**, no
multi-repo loop exists in the code. `run()` (line 60) polls forever with
`time.sleep(poll_interval)` and swallows all exceptions per cycle
(`except Exception: logger.exception(...)`), so a transient DB or Ollama
outage does not crash the process — it just logs and retries next cycle.
This makes the daemon itself fairly tolerant of dependency flakiness, which
matters for placement below.

### Recommendation: WSL2 container per repo (not a bare systemd unit)

Given the substrate already runs everything through WSL2 Ubuntu-24.04
Docker (per the machine-wide CI/Docker setup), keep the harvester there
rather than introducing a second process-management story (systemd units in
WSL are usable but this machine's convention is containers):

- One container per SpaceMate repo, e.g. `chips-harvester-superapp`,
  `chips-harvester-chat-system`, each with:
  - The repo bind-mounted read-only-except-`.git` (the daemon only reads
    git history via `GitReader`, plus writes to Postgres — it does not
    need write access to the working tree).
  - `restart: unless-stopped` (survives WSL/Docker restarts, does not
    fight manual `docker stop` during maintenance).
  - `depends_on` the chips Postgres container (Option A) with a
    healthcheck-gated start.
  - Logs to Docker's default json-file driver (`docker logs
    chips-harvester-<repo> -f`) — no separate log shipping designed here;
    flag as a future improvement if volume warrants it.
- Entry point: a tiny wrapper script (not present in the codebase today,
  a config artifact not a code change) that builds the `psycopg.Connection`,
  `OllamaEmbedder`, and `repo_path`, then calls `HarvesterDaemon(...).run()`.

### Embedder dependency (Ollama) — flagged as a hard runtime requirement

`OllamaEmbedder.embed()` (src/chips/harvester/embedding.py:11-18) calls
`resp.raise_for_status()` after POSTing to `{base_url}/api/embed`, with no
try/except around the HTTP call. If Ollama is down or unreachable:

- `httpx` raises a connection error (or `raise_for_status()` raises
  `httpx.HTTPStatusError` on a non-2xx) **inside `run_once()`**.
- That exception propagates up through `HarvesterDaemon.run_once()` →
  caught by the blanket `except Exception` in `run()` (daemon.py:68) →
  logged via `logger.exception(...)` → daemon sleeps `poll_interval` and
  retries next cycle.

Net effect: **Ollama being down does not crash the daemon**, but it does
mean **zero commits get harvested for that entire cycle** — and because
`_last_ingested_sha()` is only advanced via successful ingestion, the next
cycle will retry the same commits once Ollama comes back (no data loss, no
duplicate rows expected given idempotent backfill design — but this was not
verified against `ingestion.py`'s upsert logic beyond a signature skim).
**Ollama must be running and reachable at daemon-container network scope**
for capture to actually happen — treat it as a hard runtime dependency, and
make sure the harvester container can reach Ollama's port from inside WSL2
(same Docker network, or `host.docker.internal` / bridge routing if Ollama
runs on the Windows host).

---

## 3. Backfill procedure

Backfill is idempotent (confirmed fact — deterministic extraction over
commit messages), so it is safe to run repeatedly without dedup logic.

1. **Measure size first** — don't guess commit counts. For each target repo:
   ```
   git -C <repo_path> rev-list --count HEAD
   ```
2. **Run the daemon's first cycle as the backfill.** `run_once()`
   (daemon.py:35-58) already handles "no prior state" — `_last_ingested_sha()`
   returns `None` when the store has nothing, and `GitReader.commits_since(since_sha=None)`
   is expected to return full history (verify this specifically in
   `git_reader.py` before relying on it — not read in this task, flagging
   as a pre-flight check the owner should do rather than assume).
3. For a large repo, the first `run_once()` may take longer than the
   60s `poll_interval` default — that's fine, `run()` just calls `run_once()`
   synchronously and sleeps after it returns, so a long first cycle simply
   delays the second cycle, it does not overlap or double-run.
4. Re-running backfill (e.g. after a container restart) is safe: it will
   re-derive from `_last_ingested_sha()` and pick up only new commits since
   the last successfully ingested one.

---

## 4. Multi-repo reality

Confirmed: chips + N SpaceMate repos ⇒ **N+1 daemon instances** with the
current constructor (one `repo_path` per `HarvesterDaemon`). Candidate
SpaceMate repos observed under `C:\sachinynaik\` (one-level listing only,
`.git` presence not verified — owner should confirm each before wiring a
container):

`spacemate_superapp`, `spacemate_chat_system`, `spacemate_backend`,
`spacemate_ai_backend`, `spacemate_dashboard`, `spacemate_search`,
`spacemate_infra`, `spacemate_staec`, `spacemate_unified_access`,
`spacemate_energy_optimization`, `spacemate_home_and_building_integration`,
`spacemate_data_privacy_fairness_and_governance`,
`spacemate_demo_roadmap_onboarding_feedback`,
`spacemate_evals_text_classification`, `spacemate_gtm_stack`,
`spacemate_ui`, `spacemate-company-website`, `spacemate-otel`.

(`spacemate-postgres` is the Postgres image/container directory, not a code
repo to harvest — exclude it. Several other `spacemate-*` / `sm_*` /
`sm-*` directories look like worktrees, backups, or PR staging copies —
exclude those from harvesting to avoid ingesting duplicate/divergent
history; the owner should pick the canonical clone per logical repo.)

Running a full N+1 fleet of always-on daemon containers today is real
operational overhead (N+1 containers, N+1 log streams, N+1 things that can
silently stall on an Ollama outage). **A small multi-repo loop inside
`HarvesterDaemon` (or a thin wrapper that iterates a list of `repo_path`s
per poll cycle) would remove this N+1 problem — but that is a code change,
not a deployment config, and is out of scope for this plan.** Flagging it
as the natural next CHIPS slice if/when more than 2-3 repos need coverage;
for an initial rollout, starting with a single high-value repo (or two) as
separate containers is the low-risk path.

---

## 5. Verification checklist

Once deployed, confirm capture is actually live:

**Daemon logs** (per container):
```
docker logs chips-harvester-<repo> --since 10m
```
Expect either silence (no new commits since last cycle — fine) or lines
matching `Harvested %d memories` (daemon.py:67). Absence of any
`Harvester error` lines over a full observation window is a good sign;
presence means check Ollama reachability and DB connectivity first (see
Section 2).

**Row-count probes** (run against the chosen chips DB from Section 1) —
before/after comparison across a few poll cycles confirms rows are growing,
not just present once from an old test:

```sql
SELECT count(*) FROM cortex_git_commits;      -- ingestion.py truth table
SELECT count(*) FROM <defect_corpus_table>;   -- rebuild_defect_corpus_for_shas target
SELECT count(*) FROM <cochange_pairs_table>;  -- merge_cochange_pairs target
SELECT count(*) FROM <file_signals_table>;    -- upsert_file_signal target
SELECT count(*) FROM <memory_table>;          -- MemoryRepository.insert target (has embeddings)
```

(Exact table names were not verified in this task — `HarvesterStore`'s
concrete table names were out of scope; the owner should confirm them from
`src/chips/harvester/storage.py` before running these probes, or simply
run `\dt` in the target DB and match against the four operations listed
above.)

A clean confirmation is: commit count in `cortex_git_commits` for a repo
matches (or is trending toward) that repo's `git rev-list --count HEAD`
from Section 3, and the embedding-bearing memory table's row count is
increasing across poll cycles with no corresponding growth in
`Harvester error` log lines.
