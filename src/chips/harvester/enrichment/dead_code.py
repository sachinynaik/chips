"""VultureAnalyzer — detect dead code in Python files using vulture."""
from __future__ import annotations

from chips.harvester.enrichment.models import AnalyzerStatus


class VultureAnalyzer:
    """Analyse Python files for dead code using vulture.

    Reports unused functions, classes, variables, and imports. Non-.py files
    are silently skipped.

    Evidence > Guessing: ``analyze`` still returns a plain ``list[dict]`` (the
    finding shape is unchanged), but the run outcome is exposed via
    :attr:`last_status` (an :class:`AnalyzerStatus` value) so a non-result —
    vulture missing (``not_installed``) or a per-file crash (``failed``) — is
    never mistaken for a clean ``[]``. A genuine clean run is ``ok``.

    Args:
        min_confidence: Minimum confidence threshold (0-100) for reported
            findings. Defaults to 60 (vulture's recommended default).
    """

    def __init__(self, min_confidence: int = 60) -> None:
        self._min_confidence = min_confidence
        self._last_status: str = AnalyzerStatus.SKIPPED.value

    @property
    def last_status(self) -> str:
        """:class:`AnalyzerStatus` value for the most recent ``analyze`` call."""
        return self._last_status

    def analyze(self, file_paths: list[str]) -> list[dict]:
        """Return a list of dead-code dicts for the given file paths."""
        self._last_status = AnalyzerStatus.SKIPPED.value

        try:
            import vulture  # noqa: PLC0415
        except ImportError:
            self._last_status = AnalyzerStatus.NOT_INSTALLED.value
            return []

        py_files = [fp for fp in file_paths if fp.endswith(".py")]
        if not py_files:
            return []

        status = AnalyzerStatus.OK.value
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
                # Surface the failure via status instead of swallowing it into
                # a false-clean. Other files still get processed.
                status = AnalyzerStatus.FAILED.value

        self._last_status = status
        return results
