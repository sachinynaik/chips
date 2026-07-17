#!/usr/bin/env bash
# One-shot CHIPS harvest backfill for ONE target repo into ONE dedicated Postgres DB.
#
# Why a dedicated DB per repo: the harvester's since-pointer
# (`PostgresHarvesterStore.latest_ingested_sha`) is a global
# `SELECT sha ... ORDER BY committed_at DESC LIMIT 1` with no repo/tenant filter,
# so two repos sharing one `cortex_git_commits` table would corrupt each other's
# incremental cursor. Until the harvest path is tenant-scoped end to end
# (follow-up), isolate each repo in its own database.
#
# Why a container: Docker is native to WSL2 here (NAT), WSL's system Python is
# 3.12 (project needs 3.13), and the faithful env comes from `uv sync` off
# uv.lock. --network host lets the container reach both the prod Postgres
# (127.0.0.1:5498) and the local Ollama server (127.0.0.1:11434) over loopback.
#
# Usage (from the chips repo root; wsl inherits the translated cwd):
#   wsl -d Ubuntu-24.04 -- bash scripts/ops/harvest-in-wsl-docker.sh <target-repo-wsl-path> <db-name>
# Env overrides: CHIPS_PROD_PG_PORT (5498), OLLAMA_BASE_URL, OLLAMA_MODEL
#   (nomic-embed-text), BACKFILL_LIMIT (100000), SKIP_BACKFILL (unset).
set -euo pipefail

CHIPS_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_REPO="${1:?usage: harvest-in-wsl-docker.sh <target-repo-wsl-path> <db-name>}"
DB_NAME="${2:?usage: harvest-in-wsl-docker.sh <target-repo-wsl-path> <db-name>}"
PORT="${CHIPS_PROD_PG_PORT:-5498}"
OLLAMA_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-nomic-embed-text}"
BACKFILL_LIMIT="${BACKFILL_LIMIT:-100000}"
SKIP_BACKFILL="${SKIP_BACKFILL:-}"

# Alembic (SQLAlchemy) wants the +psycopg driver; psycopg.connect() wants plain libpq.
MIGRATE_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:${PORT}/${DB_NAME}"
HARVEST_URL="postgresql://postgres:postgres@127.0.0.1:${PORT}/${DB_NAME}"

docker run --rm --network host \
  -v "${CHIPS_REPO}":/app -w /app \
  -v "${TARGET_REPO}":/repo:ro \
  -v chips-uv-cache:/root/.cache/uv \
  -e MIGRATE_URL="${MIGRATE_URL}" \
  -e HARVEST_URL="${HARVEST_URL}" \
  -e OLLAMA_BASE_URL="${OLLAMA_URL}" \
  -e OLLAMA_MODEL="${OLLAMA_MODEL}" \
  -e BACKFILL_LIMIT="${BACKFILL_LIMIT}" \
  -e SKIP_BACKFILL="${SKIP_BACKFILL}" \
  -e TMPDIR=/tmp \
  python:3.13-bookworm bash -euc '
apt-get update -qq && apt-get install -y -qq git >/dev/null
# The mounted repo is owned by a different uid; let git read it anyway.
git config --global --add safe.directory /repo
pip install -q uv
uv sync --extra dev

# 1. Migrate the dedicated DB to head (idempotent).
DATABASE_URL="$MIGRATE_URL" uv run python -m chips.ops.migrate
echo "MIGRATE_COMPLETE db from HARVEST_URL"

if [ -n "$SKIP_BACKFILL" ]; then
  echo "SKIP_BACKFILL set — migration only, no harvest."
  exit 0
fi

# 2. One-shot backfill: build the daemon and run_once with a large limit so
#    since_sha=None does not silently cap at the newest 100 commits. No poll loop.
uv run python - <<PY
import os
from chips.ops.harvest import build_daemon

daemon = build_daemon(
    database_url=os.environ["HARVEST_URL"],
    repo_path="/repo",
    ollama_base_url=os.environ["OLLAMA_BASE_URL"],
    ollama_model=os.environ["OLLAMA_MODEL"],
)
n = daemon.run_once(limit=int(os.environ["BACKFILL_LIMIT"]))
print(f"BACKFILL_COMPLETE repo=/repo memories={n}")
PY
'
