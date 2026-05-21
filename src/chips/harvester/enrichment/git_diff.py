from __future__ import annotations
import subprocess

class GitDiffFetcher:
    def __init__(self, repo_path: str) -> None:
        self._repo_path = repo_path

    def fetch(self, sha: str) -> tuple[str, list[str]]:
        """Returns (diff_content, hunk_headers). Graceful empty on any failure."""
        try:
            result = subprocess.run(
                ["git", "show", sha],
                cwd=self._repo_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return "", []
            return self._parse(result.stdout)
        except Exception:
            return "", []

    def _parse(self, raw: str) -> tuple[str, list[str]]:
        hunk_headers = []
        for line in raw.splitlines():
            if line.startswith("@@"):
                parts = line.split("@@")
                if len(parts) >= 3:
                    context = parts[2].strip()
                    if context:
                        hunk_headers.append(context)
        return raw, hunk_headers
