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

# Number of commit contents sent to the embedder per embed_batch() call. Keeps
# a huge backfill from sending one giant HTTP request while still collapsing
# what used to be one round-trip per commit into a handful of round-trips.
_EMBED_BATCH_SIZE = 64


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

    def run_once(self, limit: int = 100) -> int:
        """Process new commits since last run. Returns count of memories written.

        `limit` bounds `git log --max-count`. The default matches the poll
        loop's per-cycle expectations; pass a much larger value for a
        one-time backfill call so `since_sha=None` doesn't silently cap at
        the newest 100 commits and skip everything older.
        """
        since_sha = self._last_ingested_sha()

        reader = GitReader(self._repo_path)
        commits = reader.commits_since(since_sha=since_sha, limit=limit)

        if not commits:
            return 0

        GitIngestion(self._harvester_store).ingest_commits(commits)

        repo = MemoryRepository(self._conn)
        records = []
        for commit in commits:
            record = self._extractor.extract(commit)
            if record is None:
                continue
            records.append(record)

        for start in range(0, len(records), _EMBED_BATCH_SIZE):
            chunk = records[start : start + _EMBED_BATCH_SIZE]
            embeddings = self._embedder.embed_batch([r.content for r in chunk])
            for record, embedding in zip(chunk, embeddings):
                record.embedding = embedding

        for record in records:
            repo.insert(record)

        self._conn.commit()
        return len(records)

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
