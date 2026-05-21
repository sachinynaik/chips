from __future__ import annotations

from chips.harvester.enrichment.pyrefly import PyreflyAnalyzer

_SUPPORTED = ("pyrefly",)


class TypeCheckerAnalyzer:
    """Configurable type checker enricher.

    Switch backend via the `backend` constructor parameter. Currently
    supports Pyrefly. Pyright support can be added later by extending
    _build_analyzer without changing any call sites.

    Usage:
        tc = TypeCheckerAnalyzer(backend="pyrefly", repo_path=".")
        result = tc.analyze(["src/auth/token.py"])
        # result: {"errors": [...], "coverage": {...}, "backend": "pyrefly"}
    """

    def __init__(
        self,
        repo_path: str,
        backend: str = "pyrefly",
        config_path: str | None = None,
    ) -> None:
        if backend not in _SUPPORTED:
            raise ValueError(
                f"Unsupported backend: {backend!r}. Supported: {_SUPPORTED}"
            )
        self._backend = backend
        self._analyzer = self._build_analyzer(backend, repo_path, config_path)

    @property
    def backend(self) -> str:
        return self._backend

    def analyze(self, file_paths: list[str]) -> dict:
        return self._analyzer.analyze(file_paths)

    def _build_analyzer(self, backend: str, repo_path: str, config_path: str | None):
        if backend == "pyrefly":
            return PyreflyAnalyzer(repo_path=repo_path, config_path=config_path)
        raise ValueError(f"Unknown backend: {backend!r}")
