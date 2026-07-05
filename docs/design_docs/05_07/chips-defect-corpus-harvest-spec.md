# CHIPS — Defect Corpus Harvest Spec (GitHub-Issue Verified Labels)

**Date:** 2026-07-05
**Status:** DRAFT — extends the built capture path; does not replace it.
**Owner verdict (2026-07-05):** tiers T1–T4 (Gap C), the ~60% hygiene-audit link-rate
threshold (Gap D), and T4's exclusion from calibration until the audit passes are LOCKED.

---

## 1. What already exists (corrected record)

Contrary to the tracking docs, the raw-capture substrate is **built and wired**:

- `cortex_defect_corpus` (migration 009): per-commit evidence rows — issue refs
  (`#123` + `KEY-123` patterns), revert-of-sha, bug/defect/hotfix/incident keywords.
- `harvester/defect_corpus.py`: deterministic regex extraction;
  `is_high_precision_defect()` mirrors the locked labeling rule;
  `high_precision_defect_sql()` keeps **label = query over stored data** (locked).
- `storage.py` writes evidence on every commit ingest; `enrichment/defect.py` consumes it.
- `cortex_file_signal_snapshots` (migration 011): versioned score snapshots keyed to
  `basis_sha` — the capture-now snapshot imperative is implemented.

## 2. The actual gaps

### Gap A — Operational (the real capture-now item)
The corpus only accumulates where the harvester runs. **Owner confirmation needed:** is
the harvester/daemon running against the SpaceMate repo (not just chips)? If not, that
deployment — pointing ingestion at SpaceMate and backfilling its full git history — is
the single highest-value capture action available, and every week of delay is baseline
lost. Backfill is idempotent (evidence extraction is deterministic over commit messages).

> **Finding (2026-07-05, dev machine):** the harvester daemon is not running anywhere on
> this machine — no Windows process/scheduled task, no WSL systemd unit or crontab entry,
> no container. `HarvesterDaemon` (`src/chips/harvester/daemon.py`) also takes a single
> `repo_path`, so SpaceMate coverage needs its own deployment (or a multi-repo loop) plus
> full-history backfill. Deployment decision remains with the owner.

### Gap B — Labels are asserted, not verified
Today "issue-linked bugfix" means *the commit message contains `#123` and a bug keyword*.
The issue itself is never consulted: `#123` might be a feature request, a typo, or
closed-invalid. Verification requires harvesting issue metadata.

**New table (raw capture; label remains a query):**

```sql
CREATE TABLE cortex_issue_refs (
    ref              TEXT NOT NULL,            -- '#123' or 'KEY-123' as captured
    repo             TEXT NOT NULL,            -- owner/name
    issue_number     INT,
    tenant_id        UUID NULL,
    state            TEXT,                     -- open/closed
    labels           TEXT[] DEFAULT '{}',      -- raw GitHub labels, unmapped
    issue_type       TEXT,                     -- GitHub type field if present
    title            TEXT,
    closed_at        TIMESTAMPTZ,
    closed_by_pr     INT,
    fetched_at       TIMESTAMPTZ DEFAULT now(),
    fetch_status     TEXT NOT NULL             -- ok / not_found / rate_limited / failed / skipped
        CHECK (fetch_status IN ('ok','not_found','rate_limited','failed','skipped')),
        -- 'skipped' = non-GitHub ref (e.g. KEY-123): recorded, not fetchable here
    raw              JSONB,                    -- full API payload (files-are-truth: local copy)
    PRIMARY KEY (repo, ref)
);
```

Fetcher rules (purity-law-conformant):
1. Deterministic REST fetch (GitHub API / GitHub MCP), rate-limit aware, async batch —
   never blocks ingestion (ingestion keeps writing keyword-tier evidence regardless).
2. `fetch_status` is truthful (the L11 lesson): a failed fetch is recorded as failed,
   never as "no issue".
3. Missing/failed metadata **degrades the label tier, never blocks capture** — the
   asymmetry law applied to labels: verification can upgrade a label, absence of
   verification cannot delete evidence.
4. No LLM anywhere in the label path (locked: no LLM-as-judge).

### Gap C — Label precision tiers (extends, does not change, the locked rule)

| Tier | Definition | Use |
|---|---|---|
| T1 | issue-verified: ref resolves to issue with bug-class label/type, closed by linked PR | calibration numerator, highest weight |
| T2 | issue-linked + keyword (today's rule), unverified | calibration, standard weight |
| T3 | revert-linked (`revert_of_sha` resolves to a real prior commit) | calibration |
| T4 | keyword-only hotfix/incident | evidence, low weight; excluded from calibration until hygiene audit passes |

The tier is computed **in the query** (join corpus × issue_refs), not stored — broadening
or tightening a tier is an edit to the query + this doc, never a re-harvest.

### Gap D — Hygiene audit (one-time, before trusting T1/T2 volume)
Sample the last 50 SpaceMate bug-class fixes; measure: % with issue refs, % of refs that
resolve, % bug-labeled. If link-rate < ~60%, revert/hotfix patterns (T3/T4) must carry
more calibration weight and the team convention ("fixes #n" in every bugfix) becomes a
cheap process fix worth adopting. Audit result gets recorded here as an amendment.

### Gap E — Revert target resolution
`revert_of_sha` is captured but not resolved: the *reverted* commit's file-touch set is
the defect location (the revert is the fix). Resolution join: `cortex_defect_corpus.revert_of_sha
→ cortex_git_commits.sha → files_changed`, attributing defect credit to those files.
Pure SQL; no schema change.

## 3. Build order

1. **Gap A** — confirm/deploy SpaceMate ingestion + full-history backfill (owner).
2. **Gap E** — revert resolution query into `enrichment/defect.py` (small, no migration).
3. **Gap B** — migration 013 (`cortex_issue_refs`) + fetcher module + tests.
4. **Gap D** — hygiene audit once ≥ 50 SpaceMate bugfix commits are in the corpus.
5. **Gap C** — tier query lands with B; calibration weighting waits for D's result.

## 4. Non-goals
No LLM labeling. No broadening of "defect" beyond the locked high-precision rule without
a recorded amendment. No dependency on GitHub availability in the gate path — the corpus
is local; GitHub is a producer, not a runtime dependency.

---

*A hand-authored node under A0. Tier definitions LOCK on owner sign-off; tier weights
stay tunable pending the Gap D audit.*
