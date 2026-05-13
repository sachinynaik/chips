from __future__ import annotations

from collections import Counter

from chips.compiler.classifier import TaskKind, classify_task
from chips.harvester.git_reader import CommitRecord
from chips.memory.models import MemoryRecord, MemoryType


class CommitMemoryExtractor:
    def extract(self, commit: CommitRecord) -> MemoryRecord | None:
        if not commit.message or commit.message.startswith("Merge"):
            return None

        scope = _infer_scope(commit.files_changed)
        task_kind = classify_task(commit.message)
        tags = [str(task_kind)] if task_kind != TaskKind.unknown else []

        return MemoryRecord(
            type=MemoryType.LESSON,
            scope=scope,
            content=commit.message,
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
