from __future__ import annotations
import json
import subprocess

class SemgrepAnalyzer:
    def __init__(self, config: str = "auto") -> None:
        self._config = config

    def analyze(self, file_paths: list[str]) -> list[dict]:
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
            return data.get("results", [])
        except (FileNotFoundError, json.JSONDecodeError, Exception):
            return []
