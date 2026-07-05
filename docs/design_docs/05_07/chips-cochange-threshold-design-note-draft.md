# Co-change Support Threshold + Generated-Code Filter — Design Note

**DRAFT — for owner sign-off (A5 #3). Drafted 2026-07-05. Decides nothing by itself.**

Source: register OD-2 (`chips-component-decision-register.md` §6, item 2) — "Co-change support
threshold + generated-code filter." Carried into `chips-component-decision-amendments.md` A5,
closable-now row #3: "short design note; blocks entropy quality."

---

## 1. What the code does today (grounded)

Two separate co-change surfaces exist, and only one of them has any generated-code awareness:

- **`cortex_cochange_pairs` (file_a, file_b, frequency)** — raw pair-frequency table.
  `CochangeFetcher.fetch()` (`src/chips/harvester/enrichment/cochange.py`) reads it directly:
  `ORDER BY frequency DESC LIMIT %s` with no minimum-frequency filter and no join against any
  generated/scaffolded tag. Any pair, however thin (frequency = 1) or however generated the files
  are, can surface in the top-N retrieval evidence.
- **`cortex_file_signals.cochange_entropy`** — a per-file entropy score computed at ingest time.
  `GitIngestion._compute_stored_cochange_entropy()` (`src/chips/harvester/ingestion.py`) already
  does two things OD-2 asks about, but only for this second surface: it classifies each file via
  `classify_generated_kind()` and, if the file is tagged `generated` or `scaffolded`, **hard-zeroes
  entropy to 0.0** rather than computing it from partner frequencies. There is no support
  threshold here either — `cochange_entropy_for_file()` runs against whatever partner-frequency
  data exists, however sparse.

So today: the entropy-adjacent signal has a generated-code exclusion (blunt: zero-out) and no
threshold; the retrieval-facing pair fetcher has neither. OD-2 needs to fix both gaps and make the
filter behavior consistent across the two surfaces.

The generated-tags substrate already exists: migration `011_add_generated_tags_and_signal_snapshots.py`
added `cortex_file_signals.generated_kind TEXT CHECK (... IN ('generated','scaffolded') OR NULL)`
and a `cortex_file_signal_snapshots` history table carrying the same column. This is the substrate
to build on rather than invent a second tagging mechanism.

---

## 2. Support threshold

**Problem:** neither surface has a minimum-support floor. A pair or a file's partner set built from
frequency = 1 is noise that still feeds coupling/entropy today.

**Candidate policies:**

1. **Fixed N (absolute minimum frequency, e.g. pairs/partners must reach count ≥ 3 before counting
   toward coupling/entropy).**
   - Failure mode: a magic constant tuned for a mature repo starves a young repo — commit volume
     low enough that almost nothing reaches N, so entropy/coupling reads as "no signal" everywhere
     (false negative, not "unknown").
   - Fit with current code: trivial to add — `cortex_cochange_pairs.frequency` and the partner-
     frequency counts feeding `cochange_entropy_for_file()` are already plain integers; a `WHERE
     frequency >= N` / a floor inside the entropy computation is a one-line change on each surface.

2. **Percentile-based (e.g. only pairs/partners in the top X% of the repo's own frequency
   distribution count).**
   - Failure mode: self-relative, so it adapts to repo size — but on a small or young repo the
     whole distribution is thin, and "top X%" of a population that is mostly frequency = 1 still
     admits noise; percentile needs a population-size floor underneath it to mean anything, which
     re-introduces a fixed-N-style component anyway.
   - Fit with current code: requires computing the distribution per repo/per query, not just a
     constant comparison — more work than (1), and no aggregate/window-function scaffolding for
     this exists in `cochange.py` or `ingestion.py` today.

3. **Time-decayed support (recency-weighted count — a pair that co-changed 5 times in the last
   month weighs more than 5 times spread across 3 years).**
   - Failure mode: needs calibrating a decay half-life (another arbitrary constant, just recast),
     and it changes the *meaning* of "frequency" mid-flight for a data source described elsewhere
     as a plain accumulate-forever counter.
   - Fit with current code: **not grounded as buildable without a schema change.** The read set
     shows `cortex_cochange_pairs` exposing only `file_a, file_b, frequency` — no per-pair
     timestamp or last-seen column was observed in the read files. Time-decay requires that
     dimension to exist first; it is not a drop-in query/threshold change like (1) or (2).

**Recommendation:** **Fixed N**, applied at the same query/computation boundary on both surfaces
(pair fetch and entropy input), with the floor exposed as a config constant rather than hardcoded,
so it is one knob to raise/lower rather than a schema change. It is the only policy of the three
buildable today without adding a new column, and its cold-start failure mode (young repos read as
"no signal") is the same shape already accepted elsewhere in this design: A7's declared shadow
phase treats missing/thin signal as advisory-only rather than a hard block until coverage crosses
a threshold. The same shadow-phase framing (not the same mechanism) can absorb Fixed N's
cold-start weakness — owner should confirm whether to reuse that pattern explicitly or treat it as
a separate open row.

---

## 3. Generated-code filter

**What to exclude:** the read set only confirms two tag values exist —
`generated_kind IN ('generated', 'scaffolded')` — used today to zero out entropy for a file. It
does not confirm what `classify_generated_kind()` (in `harvester/signals.py`, out of this note's
read set) actually classifies as `generated` vs `scaffolded` — whether lockfiles, vendored
directories, or migration files fall under either tag, or under neither, is not grounded here and
is listed as an open row below.

**Where — capture vs query time:** the current code is inconsistent, not principled: the tag
itself (`generated_kind`) is written once per file at capture time (raw classification, fine to
capture), but the *effect* of the tag — zeroing entropy to 0.0 — is also baked in at capture time,
inside `_compute_stored_cochange_entropy()`. That means `cortex_file_signals.cochange_entropy` for
a generated file is stored as 0.0 rather than storing the true computed value alongside the tag and
letting a reader decide whether to honor it. No explicit "capture stays raw, filters/labels live in
the query" principle was found verbatim in OD-2 or in migration 011 — the closest grounded anchor
is the register's general locked principle "files are truth; every index/graph is a derived,
reconstructable cache" (§2.5), which argues for the query-time direction but was not written
specifically about this pipeline.

**Recommended mechanism:** move filtering to query time, on top of the existing substrate:

- Keep `generated_kind` as the single source of truth (already built, migration 011 — no new
  tagging mechanism needed).
- Fix the entropy path so capture stores the *true* computed entropy plus the tag, and the
  generated-code exclusion is applied by the reader/consumer of `cochange_entropy` (query time),
  not baked into the stored value. This makes the raw signal reconstructable and lets a future
  consumer choose to include tagged files (e.g. for an audit) without recomputing.
- Fix `CochangeFetcher.fetch()` to `JOIN`/exclude against `cortex_file_signals.generated_kind` for
  both `file_a` and `file_b` at query time, rather than leaving the raw-pair fetch untouched as it
  is today.

This is a "recommend one direction" call, not a full spec — the exact join/exclusion SQL and
whether "exclude" means drop-the-pair vs down-weight-the-pair is left to implementation, gated on
owner sign-off of the direction.

---

## 4. Open rows — could not ground from the read set

1. `classify_generated_kind()`'s actual classification rules (lockfiles / vendored code /
   migrations / generated clients) — lives in `harvester/signals.py`, not in this note's read set.
2. `cochange_entropy_for_file()`'s entropy formula and what "partner frequencies" means precisely —
   same file, not read.
3. Whether `cortex_cochange_pairs` carries any column beyond `file_a, file_b, frequency` (e.g. a
   last-seen timestamp) — only the `SELECT` in `cochange.py` was observed, not the table's DDL/
   migration.
4. Whether a "capture raw, filter/label at query" principle is meant to govern this specific
   pipeline as a locked rule, versus the general derived-cache principle in the register being the
   only applicable anchor — owner call.
5. Calibration values (the Fixed-N floor; which repos/commit-volumes count as "young" for the
   shadow-phase carve-out) — needs real corpus data, not determinable from source alone.

**Open rows: 5.**
