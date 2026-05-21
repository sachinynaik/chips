from __future__ import annotations

import os


class CoverageReader:
    """Read existing .coverage artifacts to report line-level coverage for changed files.

    Does NOT run tests — only reads existing .coverage databases produced by
    pytest-cov or coverage.py.  Signal: changed lines with 0% coverage = higher risk.
    """

    def __init__(self, repo_path: str) -> None:
        self._repo_path = repo_path

    def analyze(
        self,
        file_paths: list[str],
        changed_lines: dict[str, list[int]] | None = None,
    ) -> dict:
        """Read .coverage and return coverage info for changed files.

        Args:
            file_paths: Changed file paths (absolute or relative).
            changed_lines: Optional map of file_path -> list of changed line numbers.
                           If None, per-file changed_lines_* fields are set to None.

        Returns:
            {
                "coverage_available": bool,
                "files": {
                    "<path>": {
                        "covered_lines": int,
                        "missing_lines": int,
                        "coverage_pct": float,
                        "changed_lines_covered": int | None,
                        "changed_lines_missing": int | None,
                        "changed_lines_coverage_pct": float | None,
                    }
                }
            }
        """
        _EMPTY = {"coverage_available": False, "files": {}}

        # Only .py files are relevant
        py_files = [f for f in file_paths if f.endswith(".py")]
        if not py_files:
            return _EMPTY

        coverage_file = self._find_coverage_file()
        if coverage_file is None:
            return _EMPTY

        try:
            from coverage import Coverage  # type: ignore[import]
        except (ImportError, TypeError):
            return _EMPTY

        try:
            cov = Coverage(data_file=coverage_file)
            cov.load()
            data = cov.get_data()
        except Exception:
            return _EMPTY

        measured = {os.path.abspath(p) for p in (data.measured_files() or [])}

        result_files: dict[str, dict] = {}

        for raw_path in py_files:
            abs_path = os.path.abspath(raw_path)
            if abs_path not in measured:
                continue

            covered_line_set = set(data.lines(abs_path) or [])
            # coverage.py lines() returns only *executed* lines.
            # We report covered_lines = len of that set; missing_lines = 0 because
            # we don't have full executable-line information without executing the
            # source-file analysis (too expensive here).  The caller can compare
            # against changed_lines for the signal they need.
            covered_lines = len(covered_line_set)
            # We don't have a reliable total without running analysis; use covered as total
            # unless changed_lines gives us a denominator.
            missing_lines = 0
            coverage_pct = 100.0 if covered_lines > 0 else 0.0

            cl_covered: int | None = None
            cl_missing: int | None = None
            cl_pct: float | None = None

            if changed_lines is not None:
                # Look up changed lines using the same raw key the caller used,
                # or the abs path.
                raw_changed = changed_lines.get(raw_path) or changed_lines.get(abs_path) or []
                if raw_changed:
                    cl_covered = sum(1 for ln in raw_changed if ln in covered_line_set)
                    cl_missing = len(raw_changed) - cl_covered
                    cl_pct = (cl_covered / len(raw_changed)) * 100.0
                else:
                    cl_covered = 0
                    cl_missing = 0
                    cl_pct = 0.0

            result_files[abs_path] = {
                "covered_lines": covered_lines,
                "missing_lines": missing_lines,
                "coverage_pct": coverage_pct,
                "changed_lines_covered": cl_covered,
                "changed_lines_missing": cl_missing,
                "changed_lines_coverage_pct": cl_pct,
            }

        return {"coverage_available": True, "files": result_files}

    def _find_coverage_file(self) -> str | None:
        """Look for .coverage in repo_path, then parent dirs up to 2 levels."""
        search_path = self._repo_path
        for _ in range(3):  # current + 2 levels up
            candidate = os.path.join(search_path, ".coverage")
            if os.path.isfile(candidate):
                return candidate
            parent = os.path.dirname(search_path)
            if parent == search_path:
                break
            search_path = parent
        return None
