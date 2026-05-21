from __future__ import annotations

from collections import Counter

from chips.compiler.classifier import TaskKind, classify_task
from chips.harvester.enrichment.models import EnrichmentResult
from chips.harvester.enrichment.pipeline import EnrichmentPipeline
from chips.harvester.git_reader import CommitRecord
from chips.harvester.summarizer import DiffSummarizer
from chips.memory.models import MemoryRecord, MemoryType


class CommitMemoryExtractor:
    def __init__(
        self,
        enricher: EnrichmentPipeline | None = None,
        summarizer: DiffSummarizer | None = None,
    ) -> None:
        self._enricher = enricher
        self._summarizer = summarizer

    def extract(self, commit: CommitRecord) -> MemoryRecord | None:
        if not commit.message or commit.message.startswith("Merge"):
            return None

        scope = _infer_scope(commit.files_changed)
        task_kind = classify_task(commit.message)
        tags = [str(task_kind)] if task_kind != TaskKind.unknown else []

        if self._enricher is not None and self._summarizer is not None:
            enrichment = self._enricher.enrich(commit, scope)
            content = self._summarizer.summarize(commit, enrichment)
        else:
            content = commit.message

        return MemoryRecord(
            type=MemoryType.LESSON,
            scope=scope,
            content=content,
            tags=tags,
            source=commit.sha,
            author=commit.author,
        )


def _infer_scope(files: list[str]) -> str:
    dirs = [f.split("/")[1] if f.count("/") >= 2 else f.split("/")[0]
            for f in files if "/" in f]
    if not dirs:
        return "general"
    return Counter(dirs).most_common(1)[0][0]
