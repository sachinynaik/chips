from __future__ import annotations

from chips.harvester.enrichment.models import AnalyzerStatus

class LizardAnalyzer:
    def __init__(self) -> None:
        self._last_status = AnalyzerStatus.SKIPPED.value

    @property
    def last_status(self) -> str:
        return self._last_status

    def analyze(self, file_paths: list[str]) -> list[dict]:
        self._last_status = AnalyzerStatus.SKIPPED.value
        if not file_paths:
            return []
        try:
            import lizard
        except ImportError:
            self._last_status = AnalyzerStatus.NOT_INSTALLED.value
            return []
        results = []
        status = AnalyzerStatus.OK.value
        for fp in file_paths:
            try:
                analysis = lizard.analyze_file(fp)
                for func in analysis.function_list:
                    results.append({
                        "file": fp,
                        "function": func.name,
                        "cyclomatic_complexity": func.cyclomatic_complexity,
                        "nloc": func.nloc,
                    })
            except Exception:
                status = AnalyzerStatus.FAILED.value
        self._last_status = status
        return results
