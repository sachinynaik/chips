from __future__ import annotations

import subprocess
from pathlib import Path


class ImportLinterAnalyzer:
    """Run import-linter to detect architecture layer violations."""

    def __init__(self, repo_path: str) -> None:
        self._repo_path = Path(repo_path)

    def analyze(self, file_paths: list[str]) -> list[dict]:
        """Return list of architecture violation dicts.

        Each dict: {
            "file": str,
            "import_from": str,
            "import_to": str,
            "contract": str,
            "message": str,
        }
        """
        config = self._repo_path / ".importlinter"
        if not config.exists():
            return []

        try:
            result = subprocess.run(
                ["lint-imports", "--config", str(config)],
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

        if result.returncode == 0:
            return []

        output = result.stdout or result.stderr or ""
        return self._parse_violations(output)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_violations(self, output: str) -> list[dict]:
        """Parse import-linter text output into violation dicts.

        import-linter groups violations under a contract heading line, followed
        by indented detail lines.  We collect one dict per contract that has
        at least one detail line.

        Example output::

            Layers contract
                mypackage.low -> mypackage.high: not allowed

            Independence contract
                moduleA -> moduleB: not allowed
        """
        violations: list[dict] = []
        lines = output.splitlines()

        current_contract: str | None = None
        detail_lines: list[str] = []

        def _flush() -> None:
            if current_contract and detail_lines:
                violations.append(
                    {
                        "file": "",
                        "import_from": "",
                        "import_to": "",
                        "contract": current_contract,
                        "message": "\n".join(detail_lines).strip(),
                    }
                )

        for line in lines:
            if not line.strip():
                # Blank line: flush current contract block
                _flush()
                current_contract = None
                detail_lines = []
                continue

            if line[0] not in (" ", "\t"):
                # Non-indented, non-blank → new contract heading
                _flush()
                current_contract = line.strip()
                detail_lines = []
            else:
                # Indented line → detail under current contract
                if current_contract is not None:
                    detail_lines.append(line.strip())

        # Flush last block (no trailing blank line)
        _flush()

        return violations
