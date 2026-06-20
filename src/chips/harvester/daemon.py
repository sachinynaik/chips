from __future__ import annotations

import logging
import time

import psycopg

from chips.harvester.extractor import CommitMemoryExtractor
from chips.harvester.git_reader import GitReader
from chips.harvester.ingestion import GitIngestion
from chips.harvester.storage import HarvesterStore, PostgresHarvesterStore
from chips.harvester.embedding import OllamaEmbedder
from chips.memory.repository import MemoryRepository

logger = logging.getLogger(__name__)


class HarvesterDaemon:
    def __init__(
        self,
        conn: psycopg.Connection,
        embedder: OllamaEmbedder,
        repo_path: str,
        poll_interval: int = 60,
        extractor: CommitMemoryExtractor | None = None,
        harvester_store: HarvesterStore | None = None,
    ) -> None:
        self._conn = conn
        self._embedder = embedder
        self._repo_path = repo_path
        self._poll_interval = poll_interval
        self._extractor = extractor or CommitMemoryExtractor()
        self._harvester_store = harvester_store or PostgresHarvesterStore(conn)

    def run_once(self) -> int:
        """Process new commits since last run. Returns count of memories written."""
        since_sha = self._last_ingested_sha()

        reader = GitReader(self._repo_path)
        commits = reader.commits_since(since_sha=since_sha)

        if not commits:
            return 0

        GitIngestion(self._harvester_store).ingest_commits(commits)

        repo = MemoryRepository(self._conn)
        count = 0
        for commit in commits:
            record = self._extractor.extract(commit)
            if record is None:
                continue
            record.embedding = self._embedder.embed(record.content)
            repo.insert(record)
            count += 1

        self._conn.commit()
        return count

    def run(self) -> None:
        """Poll indefinitely, processing new commits each cycle."""
        logger.info("Harvester daemon started (interval=%ss)", self._poll_interval)
        while True:
            try:
                count = self.run_once()
                if count:
                    logger.info("Harvested %d memories", count)
            except Exception:
                logger.exception("Harvester error — will retry next cycle")
            time.sleep(self._poll_interval)

    def _last_ingested_sha(self) -> str | None:
        return self._harvester_store.latest_ingested_sha()
