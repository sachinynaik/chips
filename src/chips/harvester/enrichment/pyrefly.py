from __future__ import annotations

import json
import subprocess


class PyreflyAnalyzer:
    """Layer 1 enricher: type errors and annotation coverage via Pyrefly.

    Calls `pyrefly check` and `pyrefly coverage report` as subprocesses.
    Graceful empty return when Pyrefly is not installed.
    Config path is forwarded to both commands when provided, allowing
    per-project pyrefly.toml to be used or swapped in as needed.
    """

    def __init__(self, repo_path: str, config_path: str | None = None) -> None:
        self._repo_path = repo_path
        self._config_path = config_path

    def analyze(self, file_paths: list[str]) -> dict:
        py_files = [f for f in file_paths if f.endswith(".py")]
        if not py_files:
            return {"errors": [], "coverage": {}, "backend": "pyrefly"}

        errors = self._check_errors(py_files)
        coverage = self._check_coverage(py_files)
        return {"errors": errors, "coverage": coverage, "backend": "pyrefly"}

    def _check_errors(self, file_paths: list[str]) -> list[dict]:
        cmd = ["pyrefly", "check", "--output-format", "json"] + file_paths
        if self._config_path:
            cmd.extend(["--config", self._config_path])
        try:
            result = subprocess.run(
                cmd,
                cwd=self._repo_path,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return self._parse_errors(result.stdout)
        except Exception:
            return []

    def _check_coverage(self, file_paths: list[str]) -> dict:
        cmd = ["pyrefly", "coverage", "report", "--json"] + file_paths
        if self._config_path:
            cmd.extend(["--config", self._config_path])
        try:
            result = subprocess.run(
                cmd,
                cwd=self._repo_path,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return self._parse_coverage(result.stdout)
        except Exception:
            return {}

    def _parse_errors(self, stdout: str) -> list[dict]:
        if not stdout.strip():
            return []
        try:
            data = json.loads(stdout)
            if not isinstance(data, list):
                return []
            return [
                {
                    "code": e.get("code", "unknown"),
                    "message": e.get("message", ""),
                    "path": e.get("path", ""),
                    "line": e.get("range", {}).get("start", {}).get("line", 0),
                }
                for e in data
            ]
        except (json.JSONDecodeError, Exception):
            return []

    def _parse_coverage(self, stdout: str) -> dict:
        if not stdout.strip():
            return {}
        try:
            data = json.loads(stdout)
            files = data.get("files", {})
            if not isinstance(files, dict):
                return {}
            return {
                path: {
                    "annotation_completeness": info.get("annotation_completeness", 0.0),
                    "type_completeness": info.get("type_completeness", 0.0),
                }
                for path, info in files.items()
            }
        except (json.JSONDecodeError, Exception):
            return {}
