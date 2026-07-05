from __future__ import annotations

from chips.harvester.enrichment.models import AnalyzerStatus


class ScopeMemoryFetcher:
    def __init__(self) -> None:
        self._last_status: str = AnalyzerStatus.SKIPPED.value

    @property
    def last_status(self) -> str:
        return self._last_status

    def fetch(self, conn, scope: str, limit: int = 5) -> list[dict]:
        self._last_status = AnalyzerStatus.SKIPPED.value
        if not scope:
            return []
        try:
            rows = conn.execute(
                """
                SELECT content, type, tags
                FROM cortex_memories
                WHERE scope = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (scope, limit),
            ).fetchall()
            self._last_status = AnalyzerStatus.OK.value
            return [{"content": r[0], "type": r[1], "tags": r[2] or []} for r in rows]
        except Exception:
            self._last_status = AnalyzerStatus.FAILED.value
            return []
