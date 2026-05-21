from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path


_MAX_RESULTS = 20


class JscpdAnalyzer:
    """Run jscpd (multi-language clone detector) to find code duplication."""

    def __init__(
        self,
        repo_path: str,
        min_lines: int = 5,
        min_tokens: int = 50,
    ) -> None:
        self._repo_path = repo_path
        self._min_lines = min_lines
        self._min_tokens = min_tokens

    def analyze(self, file_paths: list[str]) -> list[dict]:
        """Return list of clone findings (capped at 20).

        Each dict: {
            "file_a": str,
            "start_a": int,
            "end_a": int,
            "file_b": str,
            "start_b": int,
            "end_b": int,
            "lines": int,
            "tokens": int,
            "language": str,
        }
        """
        if not file_paths:
            return []

        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                report = self._run_jscpd(file_paths, tmp_dir)
                return self._parse_report(report)
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Protected — tests can monkeypatch this
    # ------------------------------------------------------------------

    def _run_jscpd(self, file_paths: list[str], output_dir: str) -> dict:
        """Invoke jscpd and return the parsed JSON report dict."""
        cmd = [
            "jscpd",
            "--reporters", "json",
            "--output", output_dir,
            "--min-lines", str(self._min_lines),
            "--min-tokens", str(self._min_tokens),
        ] + list(file_paths)

        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )

        report_path = Path(output_dir) / "jscpd-report.json"
        return json.loads(report_path.read_text(encoding="utf-8"))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_report(self, report: dict) -> list[dict]:
        duplicates = report.get("duplicates", [])
        results = []
        for dup in duplicates[:_MAX_RESULTS]:
            first = dup.get("firstFile", {})
            second = dup.get("secondFile", {})
            results.append(
                {
                    "file_a": first.get("name", ""),
                    "start_a": first.get("start", 0),
                    "end_a": first.get("end", 0),
                    "file_b": second.get("name", ""),
                    "start_b": second.get("start", 0),
                    "end_b": second.get("end", 0),
                    "lines": dup.get("lines", 0),
                    "tokens": dup.get("tokens", 0),
                    "language": dup.get("format", ""),
                }
            )
        return results
