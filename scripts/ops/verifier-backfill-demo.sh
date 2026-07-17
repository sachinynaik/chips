#!/usr/bin/env bash
# Phase-3 verifier — durability backfill demo (SHADOW; nothing is consumed).
# Runs the deterministic verifier (adverse_events_for_files + durability_label) over a repo's
# harvested git history and prints the good/bad/unknown label distribution. This is the
# reward's ground-truth signal computed from data we already have — a real labeled corpus.
# It does NOT touch composite_reward (turning on reward consumption is a separate, owner-gated
# ledger activation, per docs/02_06_execution_ledger.md).
#
# Usage (from the chips repo root):
#   wsl -d Ubuntu-24.04 -- bash scripts/ops/verifier-backfill-demo.sh <db-name> [window_days]
# e.g. chips_backend | chips_chat | chips_staec | chips_bproxy
set -euo pipefail

CHIPS_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DB_NAME="${1:?usage: verifier-backfill-demo.sh <db-name> [window_days]}"
WINDOW_DAYS="${2:-14}"
PORT="${CHIPS_PROD_PG_PORT:-5498}"
HARVEST_URL="postgresql://postgres:postgres@127.0.0.1:${PORT}/${DB_NAME}"

docker run --rm --network host \
  -v "${CHIPS_REPO}":/app -w /app \
  -v chips-uv-cache:/root/.cache/uv \
  -e HARVEST_URL="${HARVEST_URL}" \
  -e VERIFIER_WINDOW_DAYS="${WINDOW_DAYS}" \
  -e TMPDIR=/tmp \
  python:3.13-bookworm bash -euc '
pip install -q uv >/dev/null 2>&1
uv sync --extra dev >/dev/null 2>&1
uv run python - <<PY
import os
from collections import Counter
from datetime import timedelta
import psycopg
from chips.verifier.durability import durability_label
from chips.verifier.adverse_events import adverse_events_for_files

W = int(os.environ["VERIFIER_WINDOW_DAYS"])
conn = psycopg.connect(os.environ["HARVEST_URL"])
now = conn.execute("SELECT max(committed_at) FROM cortex_git_commits").fetchone()[0]
rows = conn.execute(
    "SELECT sha, committed_at, files_changed FROM cortex_git_commits "
    "WHERE files_changed IS NOT NULL ORDER BY committed_at"
).fetchall()
dist = Counter()
bad = []
for sha, t, files in rows:
    files = list(files or [])
    events = adverse_events_for_files(conn, files, t, t + timedelta(days=W))
    label = durability_label(files, t, events, now, window_days=W)
    dist[label["status"]] += 1
    if label["status"] == "bad" and len(bad) < 5:
        ev = label["evidence"][0]
        bad.append((sha[:8], ev["kind"], ev["file_path"], ev["ref"][:8]))
total = sum(dist.values())
print(f"=== durability labels over {total} harvested commits (window W={W}d) ===")
for s in ("good", "bad", "unknown"):
    n = dist.get(s, 0)
    print(f"  {s:8}: {n:6}  ({(100.0*n/total if total else 0):4.1f}%)")
print("=== sample bad (guided change reverted/hotfixed within window) ===")
for sha, kind, fpath, ref in bad:
    print(f"  {sha}  {kind} touching {fpath}  (by {ref})")
PY
'
