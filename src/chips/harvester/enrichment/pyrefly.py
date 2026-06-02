from __future__ import annotations

import json
import subprocess

from chips.harvester.enrichment.models import AnalyzerStatus


class PyreflyAnalyzer:
    """Layer 1 enricher: type errors and annotation coverage via Pyrefly.

    Calls ``pyrefly check`` and ``pyrefly coverage report`` as subprocesses.

    Evidence > Guessing: the returned dict carries a ``status`` key
    (:class:`AnalyzerStatus` value) so a non-result is never mistaken for a
    clean result. ``not_installed`` (binary missing), ``timed_out``,
    ``failed`` (crash / unparseable output) are reported explicitly; ``ok``
    means pyrefly actually ran and its output was parsed (errors may be empty
    — that is a genuine clean result). Config path is forwarded to both
    commands when provided.
    """

    def __init__(self, repo_path: str, config_path: str | None = None) -> None:
        self._repo_path = repo_path
        self._config_path = config_path

    def analyze(self, file_paths: list[str]) -> dict:
        py_files = [f for f in file_paths if f.endswith(".py")]
        if not py_files:
            return {
                "errors": [],
                "coverage": {},
                "backend": "pyrefly",
                "status": AnalyzerStatus.SKIPPED.value,
            }

        errors, status = self._check_errors(py_files)
        # Coverage is best-effort. It does not run when the check itself never
        # ran (e.g. binary missing), and a coverage hiccup does not downgrade
        # an otherwise-ok status.
        coverage = self._check_coverage(py_files) if status == AnalyzerStatus.OK.value else {}
        return {
            "errors": errors,
            "coverage": coverage,
            "backend": "pyrefly",
            "status": status,
        }

    def _check_errors(self, file_paths: list[str]) -> tuple[list[dict], str]:
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
        except FileNotFoundError:
            return [], AnalyzerStatus.NOT_INSTALLED.value
        except subprocess.TimeoutExpired:
            return [], AnalyzerStatus.TIMED_OUT.value

        # pyrefly uses exit 0 (clean) and exit 1 (type errors found); both mean
        # it ran. Any other return code is a crash/usage error → failed.
        if result.returncode not in (0, 1):
            return [], AnalyzerStatus.FAILED.value

        errors = self._parse_errors(result.stdout)
        if errors is None:
            return [], AnalyzerStatus.FAILED.value
        return errors, AnalyzerStatus.OK.value

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
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return {}
        return self._parse_coverage(result.stdout)

    def _parse_errors(self, stdout: str) -> list[dict] | None:
        """Parse pyrefly check JSON. Returns None on unparseable output.

        Accepts both shapes pyrefly has shipped: a top-level JSON list of
        diagnostics, and an object ``{"errors": [...]}`` (pyrefly 1.x). Each
        diagnostic is normalised to ``{code, message, path, line}`` regardless
        of which field layout it arrived in (``code``/``message``/``range`` vs
        ``name``/``description``/flat ``line``).
        """
        if not stdout.strip():
            return []
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return None
        if isinstance(data, dict):
            raw = data.get("errors")
        elif isinstance(data, list):
            raw = data
        else:
            raw = None
        if not isinstance(raw, list):
            return None
        return [self._normalize_error(e) for e in raw if isinstance(e, dict)]

    @staticmethod
    def _normalize_error(e: dict) -> dict:
        # Diagnostic code/name: legacy uses "code" (str); pyrefly 1.x uses a
        # human "name" plus a numeric "code", so prefer "name" when present.
        code = e.get("name") or e.get("code") or "unknown"
        # Message: legacy "message"; pyrefly 1.x "description".
        message = e.get("message") or e.get("description") or ""
        # Line: legacy nested range.start.line; pyrefly 1.x flat "line".
        line = e.get("range", {}).get("start", {}).get("line")
        if line is None:
            line = e.get("line", 0)
        return {
            "code": code,
            "message": message,
            "path": e.get("path", ""),
            "line": line,
        }

    def _parse_coverage(self, stdout: str) -> dict:
        if not stdout.strip():
            return {}
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return {}
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
