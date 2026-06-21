from __future__ import annotations

from chips.harvester.enrichment.models import AnalyzerStatus

class JoernAnalyzer:
    """Stub. Full implementation requires Joern CPG server (JVM)."""

    def __init__(self) -> None:
        self._last_status = AnalyzerStatus.SKIPPED.value

    @property
    def last_status(self) -> str:
        return self._last_status

    def analyze(self, file_paths: list[str]) -> list[dict]:
        self._last_status = (
            AnalyzerStatus.SKIPPED.value if not file_paths else AnalyzerStatus.NOT_INSTALLED.value
        )
        return []
