#!/usr/bin/env bash
# Fast local runner for CHIPS DB-backed tests inside WSL Docker.
#
# Why: Docker is native to WSL2 here (NAT networking), so Windows pytest can't
# reach the WSL Docker Postgres, and WSL has only Python 3.12 (the project needs
# 3.13). This runs pytest in a stock python:3.13 container (faithful env via
# `uv sync` from uv.lock) talking to a pgvector container over the WSL host
# loopback (--network host) to avoid WSL2 user-defined-bridge DNS/MTU flakiness.
# Self-contained: no prebuilt image required; a uv cache volume keeps reruns fast.
#
# The authoritative CI is .github/workflows/ci.yml (run via `act`/`actgpu` and on
# the self-hosted runner). This script is the fast single-test inner loop.
#
# Portable: derives the repo root from this script's location; no hardcoded paths.
# Usage (from the repo root — wsl inherits the translated cwd):
#   wsl -d Ubuntu-24.04 -- bash scripts/test-in-wsl-docker.sh [PYTEST_ARGS...]
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${CHIPS_TEST_PG_PORT:-5499}"
DBURL="postgresql://postgres:postgres@127.0.0.1:${PORT}/postgres"
TEST_ARGS=("$@")
if [ ${#TEST_ARGS[@]} -eq 0 ]; then
  TEST_ARGS=("tests")
fi

# Fresh, deterministic Postgres on the WSL host loopback.
docker rm -f chips-testdb >/dev/null 2>&1 || true
docker run -d --name chips-testdb --network host \
  -e POSTGRES_PASSWORD=postgres pgvector/pgvector:pg16 \
  -c port="${PORT}" >/dev/null
for _ in $(seq 1 30); do
  docker exec chips-testdb pg_isready -U postgres -p "${PORT}" >/dev/null 2>&1 && break
  sleep 1
done

docker run --rm --network host \
  -v "${REPO}":/app -w /app \
  -v chips-uv-cache:/root/.cache/uv \
  -e CHIPS_TEST_DB_URL="${DBURL}" \
  -e TMPDIR=/tmp \
  python:3.13-bookworm bash -euc '
pip install -q uv
uv sync --extra dev
# Migrate the shared DB once (tests/unit and tests/compiler no-op apply_migrations
# but still open a real conn). Mirrors the CI workflow step.
uv run python - <<PY
import os
from alembic.config import Config
from alembic import command
cfg = Config("alembic.ini")
cfg.set_main_option(
    "sqlalchemy.url",
    os.environ["CHIPS_TEST_DB_URL"].replace("postgresql://", "postgresql+psycopg://", 1),
)
command.upgrade(cfg, "head")
PY
uv run pytest "$@"
' _ "${TEST_ARGS[@]}"
