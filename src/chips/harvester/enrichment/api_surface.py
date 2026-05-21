"""GriffeAnalyzer — detect API surface issues in Python files using griffe."""
from __future__ import annotations

import pathlib


class GriffeAnalyzer:
    """Analyse public API surface of Python files using griffe (AST-based).

    For each public function/method, reports:
      - missing_return_annotation
      - missing_param_annotation   (skips ``self``/``cls``)
      - undocumented_public_api

    Private symbols (leading underscore) and dunder methods are skipped.
    Non-.py files are silently skipped.  Returns [] if griffe is not installed
    or if a per-file parse error occurs.
    """

    def analyze(self, file_paths: list[str]) -> list[dict]:
        """Return a list of API-issue dicts for the given file paths."""
        try:
            import griffe  # noqa: PLC0415
        except ImportError:
            return []

        results: list[dict] = []
        for fp in file_paths:
            if not fp.endswith(".py"):
                continue
            try:
                path = pathlib.Path(fp)
                code = path.read_text(encoding="utf-8")
                module = griffe.visit(path.stem, filepath=path, code=code)
                results.extend(self._check_module(fp, module))
            except Exception:  # noqa: BLE001
                pass
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_module(self, file_path: str, module) -> list[dict]:
        results: list[dict] = []
        for name, obj in module.members.items():
            results.extend(self._check_object(file_path, name, obj))
        return results

    def _check_object(self, file_path: str, name: str, obj) -> list[dict]:
        """Recursively check an object (function or class) for API issues."""
        try:
            from griffe import Kind  # noqa: PLC0415
        except ImportError:
            return []

        results: list[dict] = []

        if obj.kind == Kind.FUNCTION:
            # Skip private names and dunders
            if name.startswith("_"):
                return []
            results.extend(self._check_function(file_path, name, obj))

        elif obj.kind == Kind.CLASS:
            if name.startswith("_"):
                return []
            # Check methods inside the class
            for method_name, method_obj in obj.members.items():
                if method_obj.kind != Kind.FUNCTION:
                    continue
                # Skip dunders and private methods
                if method_name.startswith("__") and method_name.endswith("__"):
                    continue
                if method_name.startswith("_"):
                    continue
                qualified = f"{name}.{method_name}"
                results.extend(
                    self._check_function(file_path, qualified, method_obj, is_method=True)
                )

        return results

    def _check_function(
        self, file_path: str, symbol: str, func_obj, *, is_method: bool = False
    ) -> list[dict]:
        results: list[dict] = []

        # 1. Missing return annotation
        if func_obj.returns is None:
            results.append(
                {
                    "file": file_path,
                    "symbol": symbol,
                    "change_type": "missing_return_annotation",
                    "details": f"Public function '{symbol}' has no return type annotation.",
                }
            )

        # 2. Missing parameter annotations (skip self/cls for methods)
        skip_params = {"self", "cls"} if is_method else set()
        for param in func_obj.parameters:
            if param.name in skip_params:
                continue
            if param.annotation is None:
                results.append(
                    {
                        "file": file_path,
                        "symbol": symbol,
                        "change_type": "missing_param_annotation",
                        "details": (
                            f"Parameter '{param.name}' of '{symbol}' "
                            f"has no type annotation."
                        ),
                    }
                )

        # 3. Undocumented public API
        if func_obj.docstring is None:
            results.append(
                {
                    "file": file_path,
                    "symbol": symbol,
                    "change_type": "undocumented_public_api",
                    "details": f"Public function '{symbol}' has no docstring.",
                }
            )

        return results
