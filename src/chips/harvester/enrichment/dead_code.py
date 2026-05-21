"""VultureAnalyzer — detect dead code in Python files using vulture."""
from __future__ import annotations


class VultureAnalyzer:
    """Analyse Python files for dead code using vulture.

    Reports unused functions, classes, variables, and imports.
    Non-.py files are silently skipped.  Returns [] if vulture is not
    installed or if a per-file error occurs.

    Args:
        min_confidence: Minimum confidence threshold (0–100) for reported
            findings.  Defaults to 60 (vulture's recommended default).
    """

    def __init__(self, min_confidence: int = 60) -> None:
        self._min_confidence = min_confidence

    def analyze(self, file_paths: list[str]) -> list[dict]:
        """Return a list of dead-code dicts for the given file paths."""
        try:
            import vulture  # noqa: PLC0415
        except ImportError:
            return []

        py_files = [fp for fp in file_paths if fp.endswith(".py")]
        if not py_files:
            return []

        results: list[dict] = []
        for fp in py_files:
            try:
                v = vulture.Vulture()
                v.scavenge([fp])
                for item in v.get_unused_code(min_confidence=self._min_confidence):
                    results.append(
                        {
                            "file": fp,
                            "line": item.first_lineno,
                            "name": item.name,
                            "type": f"unused_{item.typ}",
                            "confidence": item.confidence,
                        }
                    )
            except (Exception, SystemExit):  # noqa: BLE001
                pass

        return results
