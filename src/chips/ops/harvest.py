"""Deploy entrypoint for one HarvesterDaemon instance against one repo.

One container per repo_path (HarvesterDaemon has no multi-repo loop). Runs a
one-time large-limit backfill before the normal 60s-poll loop, so the daemon
doesn't silently cap at the newest 100 commits on first start (see
fix(harvester): thread limit through HarvesterDaemon.run_once).
"""

from __future__ import annotations

import logging
import os

import psycopg

from chips.harvester.daemon import HarvesterDaemon
from chips.harvester.embedding import OllamaEmbedder

logger = logging.getLogger(__name__)


def build_daemon(
    database_url: str,
    repo_path: str,
    ollama_base_url: str,
    ollama_model: str,
    poll_interval: int = 60,
) -> HarvesterDaemon:
    conn = psycopg.connect(database_url)
    embedder = OllamaEmbedder(base_url=ollama_base_url, model=ollama_model)
    return HarvesterDaemon(conn, embedder, repo_path, poll_interval=poll_interval)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    daemon = build_daemon(
        database_url=os.environ["DATABASE_URL"],
        repo_path=os.environ["REPO_PATH"],
        ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=os.environ.get("OLLAMA_MODEL", "nomic-embed-text"),
        poll_interval=int(os.environ.get("POLL_INTERVAL", "60")),
    )
    backfill_limit = int(os.environ.get("BACKFILL_LIMIT", "100000"))
    backfilled = daemon.run_once(limit=backfill_limit)
    logger.info("Initial backfill: %d memories", backfilled)
    daemon.run()


if __name__ == "__main__":
    main()
