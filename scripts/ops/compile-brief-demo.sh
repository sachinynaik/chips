#!/usr/bin/env bash
# Compile a ContextBrief for a task against ONE harvested repo database and print
# it readably. The end-to-end "CHIPS compiles focused context/status" demo:
# embed task -> pgvector retrieve over harvested memories -> rank -> compress
# (qwen2.5-coder:1.5b) -> govern. Read-only against the harvested data.
#
# Usage (from the chips repo root):
#   wsl -d Ubuntu-24.04 -- bash scripts/ops/compile-brief-demo.sh <db-name> "<task>"
set -euo pipefail

CHIPS_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DB_NAME="${1:?usage: compile-brief-demo.sh <db-name> \"<task>\"}"
TASK="${2:?usage: compile-brief-demo.sh <db-name> \"<task>\"}"
PORT="${CHIPS_PROD_PG_PORT:-5498}"
OLLAMA_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"
HARVEST_URL="postgresql://postgres:postgres@127.0.0.1:${PORT}/${DB_NAME}"

docker run --rm --network host \
  -v "${CHIPS_REPO}":/app -w /app \
  -v chips-uv-cache:/root/.cache/uv \
  -e HARVEST_URL="${HARVEST_URL}" \
  -e OLLAMA_BASE_URL="${OLLAMA_URL}" \
  -e BRIEF_TASK="${TASK}" \
  -e TMPDIR=/tmp \
  python:3.13-bookworm bash -euc '
pip install -q uv >/dev/null 2>&1
uv sync --extra dev >/dev/null 2>&1
uv run python - <<PY
import os, psycopg
from chips.compiler.builder import BriefBuilder
from chips.harvester.embedding import OllamaEmbedder
from chips.compiler.compressor import OllamaCompressor
from chips.compiler.policy import PolicyLoader

task = os.environ["BRIEF_TASK"]
conn = psycopg.connect(os.environ["HARVEST_URL"])
embedder = OllamaEmbedder(base_url=os.environ["OLLAMA_BASE_URL"], model="nomic-embed-text")
compressor = OllamaCompressor(base_url=os.environ["OLLAMA_BASE_URL"], model="qwen2.5-coder:1.5b")
policy = PolicyLoader.from_file("cortex_policy.yaml")
builder = BriefBuilder(conn, embedder, compressor, policy)

# build_and_log is the production chokepoint: it persists the brief (cortex_briefs)
# AND records the Foundation decision row (cortex_decision_log) — compile-AND-observe,
# one decision row per brief. build() alone would persist the brief but skip the observation.
brief = builder.build_and_log(task=task)

print("============================================================")
print(" CHIPS ContextBrief")
print("============================================================")
print("task        :", brief.task)
print("task_kind   :", brief.task_kind)
print("latency_ms  :", brief.latency_ms)
print("retrieved   :", len(brief.retrieved.memories), "memories (pgvector similarity)")
print("ranked      :", len(brief.ranked_signals), "signals")
print("governor    :", brief.governor_decision)
cc = brief.compressed_context
print("compressed  : type=%s len=%s" % (type(cc).__name__, len(cc) if hasattr(cc, "__len__") else "n/a"))
print()
print("-- top retrieved memories -------------------------------------")
for i, m in enumerate(brief.retrieved.memories[:5], 1):
    content = getattr(m, "content", None) or (m.get("content") if isinstance(m, dict) else str(m))
    print("  %d. %s" % (i, str(content)[:90].replace(chr(10), " ")))
print()
print("-- compressed context (preview) -------------------------------")
print(str(cc)[:800])
PY
'
