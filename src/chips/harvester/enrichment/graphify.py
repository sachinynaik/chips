from __future__ import annotations
import subprocess

class GraphifyEnricher:
    def __init__(self, repo_path: str) -> None:
        self._repo_path = repo_path

    def enrich(self, scope: str) -> str | None:
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
            return output if output else None
        except Exception:
            return None
