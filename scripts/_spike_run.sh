#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
docker run --rm -v "${REPO}":/app -w /app \
  -v chips-uv-cache:/root/.cache/uv -e TMPDIR=/tmp \
  python:3.13-bookworm bash -euc '
pip install -q uv
uv sync --extra dev >/dev/null
uv run python scripts/spike_bodyless_renderer.py
'
