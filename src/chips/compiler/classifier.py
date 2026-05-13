from __future__ import annotations

from enum import StrEnum


class TaskKind(StrEnum):
    bugfix = "bugfix"
    feature = "feature"
    refactor = "refactor"
    docs = "docs"
    test = "test"
    migration = "migration"
    unknown = "unknown"


_RULES: list[tuple[TaskKind, frozenset[str]]] = [
    (TaskKind.bugfix,    frozenset({"fix", "bug", "error", "crash", "broken", "failing", "issue", "broken"})),
    (TaskKind.migration, frozenset({"migrate", "migration", "alembic", "schema", "alter", "column"})),
    (TaskKind.refactor,  frozenset({"refactor", "clean", "restructure", "rename", "move", "extract"})),
    (TaskKind.test,      frozenset({"test", "tests", "spec", "coverage", "assert"})),
    (TaskKind.docs,      frozenset({"document", "docs", "readme", "comment", "explain", "docstring"})),
    (TaskKind.feature,   frozenset({"add", "implement", "create", "new", "build", "feature"})),
]


def classify_task(task: str) -> TaskKind:
    words = set(task.lower().split())
    for kind, keywords in _RULES:
        if words & keywords:
            return kind
    return TaskKind.unknown
