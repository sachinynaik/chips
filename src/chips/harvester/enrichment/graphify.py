from __future__ import annotations
import subprocess

from chips.harvester.enrichment.models import AnalyzerStatus


class GraphifyEnricher:
    def __init__(self, repo_path: str) -> None:
        self._repo_path = repo_path
        self._last_status: str = AnalyzerStatus.SKIPPED.value

    @property
    def last_status(self) -> str:
        return self._last_status

    def enrich(self, scope: str) -> str | None:
        self._last_status = AnalyzerStatus.SKIPPED.value
        if not scope or scope == "general":
            return None
        try:
            result = subprocess.run(
                ["graphify", "query", scope],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self._repo_path,
            )
            output = result.stdout.strip()
            self._last_status = AnalyzerStatus.OK.value
            return output if output else None
        except FileNotFoundError:
            self._last_status = AnalyzerStatus.NOT_INSTALLED.value
            return None
        except Exception:
            self._last_status = AnalyzerStatus.FAILED.value
            return None
