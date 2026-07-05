from __future__ import annotations

import fnmatch
from pathlib import Path

from chips.harvester.enrichment.models import AnalyzerStatus


_CODEOWNERS_LOCATIONS = [".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"]


class CodeownersParser:
    """Parse CODEOWNERS file (GitHub format) to determine file ownership."""

    def __init__(self, repo_path: str) -> None:
        self._repo_path = Path(repo_path)
        self._codeowners_path: Path | None = self._find_codeowners()
        self._last_status: str = AnalyzerStatus.SKIPPED.value

    @property
    def last_status(self) -> str:
        return self._last_status

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, file_paths: list[str]) -> dict:
        """Return ownership info for the given changed files.

        Returns:
            {
                "codeowners_available": bool,
                "owners_by_file": {path: list[str]},
                "cross_team_change": bool,
                "all_owners": list[str],
            }
        """
        available = self._codeowners_path is not None

        if not available:
            self._last_status = AnalyzerStatus.SKIPPED.value
            return {
                "codeowners_available": False,
                "owners_by_file": {},
                "cross_team_change": False,
                "all_owners": [],
            }

        try:
            rules = self._parse_rules()
        except Exception:  # noqa: BLE001
            self._last_status = AnalyzerStatus.FAILED.value
            return {
                "codeowners_available": True,
                "owners_by_file": {},
                "cross_team_change": False,
                "all_owners": [],
            }

        owners_by_file: dict[str, list[str]] = {}
        for fp in file_paths:
            owners_by_file[fp] = self._match_owners(fp, rules)

        all_owners_set: set[str] = set()
        for owners in owners_by_file.values():
            all_owners_set.update(owners)

        owner_sets = [frozenset(v) for v in owners_by_file.values()]
        cross_team = len(set(owner_sets)) > 1 if owner_sets else False

        self._last_status = AnalyzerStatus.OK.value
        return {
            "codeowners_available": True,
            "owners_by_file": owners_by_file,
            "cross_team_change": cross_team,
            "all_owners": sorted(all_owners_set),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_codeowners(self) -> Path | None:
        for rel in _CODEOWNERS_LOCATIONS:
            candidate = self._repo_path / rel
            if candidate.exists():
                return candidate
        return None

    def _parse_rules(self) -> list[tuple[str, list[str]]]:
        """Return list of (pattern, owners) tuples in file order."""
        assert self._codeowners_path is not None
        rules: list[tuple[str, list[str]]] = []
        for line in self._codeowners_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = stripped.split()
            pattern = parts[0]
            owners = parts[1:]
            rules.append((pattern, owners))
        return rules

    def _match_owners(self, file_path: str, rules: list[tuple[str, list[str]]]) -> list[str]:
        """Apply rules in order; last match wins (GitHub behaviour)."""
        matched: list[str] = []
        for pattern, owners in rules:
            if self._pattern_matches(pattern, file_path):
                matched = owners
        return matched

    def _pattern_matches(self, pattern: str, file_path: str) -> bool:
        """Match a CODEOWNERS-style glob pattern against file_path.

        Rules:
        - If pattern contains no '/', use fnmatch against the basename AND
          the full path (so '*.py' matches 'src/module.py').
        - If pattern contains '/', match against the full path via fnmatch.
        """
        # Normalise to forward slashes
        fp = file_path.replace("\\", "/")
        pat = pattern.rstrip("/")

        if "/" not in pat:
            # Match against basename or any path segment
            return fnmatch.fnmatch(fp, pat) or fnmatch.fnmatch(fp, f"*/{pat}") or fnmatch.fnmatch(fp, f"{pat}/*")

        # Pattern contains slash — match against full path
        # Allow leading wildcard for relative patterns
        if fnmatch.fnmatch(fp, pat):
            return True
        # Also try with a leading wildcard so "src/*" matches "src/foo.py"
        return fnmatch.fnmatch(fp, f"*/{pat}")
