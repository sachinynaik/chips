from __future__ import annotations

import json
import subprocess

_SEVERITY_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}


class BanditAnalyzer:
    """Run Bandit (Python security linter) against changed Python files.

    Complements SemgrepAnalyzer: Bandit is purpose-built for Python security
    anti-patterns (shell=True, pickle.loads, hardcoded passwords, weak crypto,
    SQL string interpolation, etc.).
    """

    def __init__(self, severity_threshold: str = "LOW") -> None:
        """
        Args:
            severity_threshold: Minimum severity level to report.
                                 One of 'LOW', 'MEDIUM', 'HIGH'.
                                 Findings below this level are discarded.
        """
        self._threshold = severity_threshold.upper()

    def analyze(self, file_paths: list[str]) -> list[dict]:
        """Return security findings for the given files.

        Only .py files are passed to Bandit. Non-.py files are silently skipped.

        Args:
            file_paths: Paths to changed files.

        Returns:
            List of finding dicts with keys:
                file, line, test_id, test_name, severity, confidence, message
        """
        py_files = [f for f in file_paths if f.endswith(".py")]
        if not py_files:
            return []

        try:
            result = subprocess.run(
                ["bandit", "-f", "json", "--severity-level", "low"] + py_files,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except FileNotFoundError:
            return []
        except subprocess.TimeoutExpired:
            return []
        except Exception:
            return []

        try:
            data = json.loads(result.stdout)
        except (json.JSONDecodeError, ValueError):
            return []

        raw_results = data.get("results", [])
        findings = []
        threshold_rank = _SEVERITY_ORDER.get(self._threshold, 0)

        for item in raw_results:
            severity = item.get("issue_severity", "LOW").upper()
            if _SEVERITY_ORDER.get(severity, 0) < threshold_rank:
                continue
            findings.append({
                "file": item.get("filename", ""),
                "line": item.get("line_number", 0),
                "test_id": item.get("test_id", ""),
                "test_name": item.get("test_name", ""),
                "severity": severity,
                "confidence": item.get("issue_confidence", "LOW").upper(),
                "message": item.get("issue_text", ""),
            })

        return findings
