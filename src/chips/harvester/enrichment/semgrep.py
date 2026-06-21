from __future__ import annotations
import json
import subprocess

from chips.harvester.enrichment.models import AnalyzerStatus

class SemgrepAnalyzer:
    def __init__(self, config: str = "auto") -> None:
        self._config = config
        self._last_status = AnalyzerStatus.SKIPPED.value

    @property
    def last_status(self) -> str:
        return self._last_status

    def analyze(self, file_paths: list[str]) -> list[dict]:
        self._last_status = AnalyzerStatus.SKIPPED.value
        if not file_paths:
            return []
        try:
            result = subprocess.run(
                ["semgrep", "--json", f"--config={self._config}"] + file_paths,
                capture_output=True,
                text=True,
                timeout=120,
            )
            data = json.loads(result.stdout)
            self._last_status = AnalyzerStatus.OK.value
            return data.get("results", [])
        except FileNotFoundError:
            self._last_status = AnalyzerStatus.NOT_INSTALLED.value
            return []
        except subprocess.TimeoutExpired:
            self._last_status = AnalyzerStatus.TIMED_OUT.value
            return []
        except (json.JSONDecodeError, Exception):
            self._last_status = AnalyzerStatus.FAILED.value
            return []
