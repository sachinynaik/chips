from __future__ import annotations
import re
import subprocess

from chips.harvester.enrichment.models import AnalyzerStatus


class SembleEnricher:
    def __init__(self, repo_path: str) -> None:
        self._repo_path = repo_path
        self._last_status: str = AnalyzerStatus.SKIPPED.value

    @property
    def last_status(self) -> str:
        return self._last_status

    def enrich(self, files_changed: list[str], diff_content: str = "") -> list[dict]:
        self._last_status = AnalyzerStatus.SKIPPED.value
        results = []
        file_lines = self._extract_changed_lines(diff_content)
        for file_path in files_changed[:3]:
            line = file_lines.get(file_path, 1)
            try:
                result = subprocess.run(
                    ["semble", "find-related", file_path, str(line), self._repo_path],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=self._repo_path,
                )
                output = result.stdout.strip()
                if output:
                    for out_line in output.splitlines():
                        if out_line.strip():
                            results.append({"source_file": file_path, "related": out_line.strip()})
            except FileNotFoundError:
                self._last_status = AnalyzerStatus.NOT_INSTALLED.value
                return []
            except Exception:
                self._last_status = AnalyzerStatus.FAILED.value
                return []
        self._last_status = AnalyzerStatus.OK.value
        return results

    def _extract_changed_lines(self, diff_content: str) -> dict[str, int]:
        """Extract first changed line number per file from diff output."""
        mapping: dict[str, int] = {}
        current_file: str | None = None
        for line in diff_content.splitlines():
            if line.startswith("+++ b/"):
                current_file = line[6:]
            elif line.startswith("@@ ") and current_file:
                m = re.search(r"\+(\d+)", line)
                if m and current_file not in mapping:
                    mapping[current_file] = int(m.group(1))
        return mapping
