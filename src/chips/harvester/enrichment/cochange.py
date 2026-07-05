from __future__ import annotations

from chips.harvester.enrichment.models import AnalyzerStatus


class CochangeFetcher:
    def __init__(self) -> None:
        self._last_status: str = AnalyzerStatus.SKIPPED.value

    @property
    def last_status(self) -> str:
        return self._last_status

    def fetch(self, conn, files: list[str], limit: int = 10) -> list[dict]:
        self._last_status = AnalyzerStatus.SKIPPED.value
        if not files:
            return []
        try:
            rows = conn.execute(
                """
                SELECT file_a, file_b, frequency
                FROM cortex_cochange_pairs
                WHERE file_a = ANY(%s) OR file_b = ANY(%s)
                ORDER BY frequency DESC
                LIMIT %s
                """,
                (files, files, limit),
            ).fetchall()
            self._last_status = AnalyzerStatus.OK.value
            return [{"file_a": r[0], "file_b": r[1], "frequency": r[2]} for r in rows]
        except Exception:
            self._last_status = AnalyzerStatus.FAILED.value
            return []
