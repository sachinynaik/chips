from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from chips.harvester.enrichment.architecture import ImportLinterAnalyzer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_importlinter(tmp_path: Path) -> Path:
    """Create a minimal .importlinter config in tmp_path and return its path."""
    cfg = tmp_path / ".importlinter"
    cfg.write_text(
        "[importlinter]\n"
        "root_package = mypackage\n\n"
        "[importlinter:contract:layers]\n"
        "name = Layers contract\n"
        "type = layers\n"
        "layers =\n"
        "    high\n"
        "    low\n",
        encoding="utf-8",
    )
    return cfg


def _ok_result() -> MagicMock:
    r = MagicMock()
    r.returncode = 0
    r.stdout = ""
    r.stderr = ""
    return r


def _violation_result(output: str) -> MagicMock:
    r = MagicMock()
    r.returncode = 1
    r.stdout = output
    r.stderr = ""
    return r


# ---------------------------------------------------------------------------
# Tests: no .importlinter file
# ---------------------------------------------------------------------------

def test_returns_empty_when_no_importlinter_file(tmp_path: Path) -> None:
    analyzer = ImportLinterAnalyzer(str(tmp_path))
    assert analyzer.analyze(["src/foo.py"]) == []


def test_returns_empty_when_no_importlinter_file_empty_paths(tmp_path: Path) -> None:
    analyzer = ImportLinterAnalyzer(str(tmp_path))
    assert analyzer.analyze([]) == []


# ---------------------------------------------------------------------------
# Tests: lint-imports not installed
# ---------------------------------------------------------------------------

def test_returns_empty_when_lint_imports_not_installed(tmp_path: Path) -> None:
    _make_importlinter(tmp_path)
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = ImportLinterAnalyzer(str(tmp_path)).analyze(["src/foo.py"])
    assert result == []


# ---------------------------------------------------------------------------
# Tests: exit code 0 (no violations)
# ---------------------------------------------------------------------------

def test_returns_empty_on_exit_code_zero(tmp_path: Path) -> None:
    _make_importlinter(tmp_path)
    with patch("subprocess.run", return_value=_ok_result()):
        result = ImportLinterAnalyzer(str(tmp_path)).analyze(["src/foo.py"])
    assert result == []


def test_returns_empty_on_exit_code_zero_with_empty_paths(tmp_path: Path) -> None:
    _make_importlinter(tmp_path)
    with patch("subprocess.run", return_value=_ok_result()):
        result = ImportLinterAnalyzer(str(tmp_path)).analyze([])
    assert result == []


# ---------------------------------------------------------------------------
# Tests: violations found
# ---------------------------------------------------------------------------

VIOLATION_OUTPUT = (
    "Layers contract\n"
    "    mypackage.low -> mypackage.high: not allowed\n"
)


def test_returns_list_on_violations(tmp_path: Path) -> None:
    _make_importlinter(tmp_path)
    with patch("subprocess.run", return_value=_violation_result(VIOLATION_OUTPUT)):
        result = ImportLinterAnalyzer(str(tmp_path)).analyze(["src/foo.py"])
    assert isinstance(result, list)
    assert len(result) >= 1


def test_violation_dict_has_required_keys(tmp_path: Path) -> None:
    _make_importlinter(tmp_path)
    with patch("subprocess.run", return_value=_violation_result(VIOLATION_OUTPUT)):
        result = ImportLinterAnalyzer(str(tmp_path)).analyze(["src/foo.py"])
    assert len(result) >= 1
    v = result[0]
    for key in ("file", "import_from", "import_to", "contract", "message"):
        assert key in v, f"Missing key: {key}"


def test_violation_contract_is_non_empty(tmp_path: Path) -> None:
    _make_importlinter(tmp_path)
    with patch("subprocess.run", return_value=_violation_result(VIOLATION_OUTPUT)):
        result = ImportLinterAnalyzer(str(tmp_path)).analyze(["src/foo.py"])
    assert result[0]["contract"] != ""


def test_violation_message_is_non_empty(tmp_path: Path) -> None:
    _make_importlinter(tmp_path)
    with patch("subprocess.run", return_value=_violation_result(VIOLATION_OUTPUT)):
        result = ImportLinterAnalyzer(str(tmp_path)).analyze(["src/foo.py"])
    assert result[0]["message"] != ""


# ---------------------------------------------------------------------------
# Tests: multiple contracts
# ---------------------------------------------------------------------------

MULTI_VIOLATION_OUTPUT = (
    "Layers contract\n"
    "    mypackage.low -> mypackage.high: not allowed\n"
    "\n"
    "Independence contract\n"
    "    moduleA -> moduleB: not allowed\n"
)


def test_multiple_contracts_each_has_correct_contract_name(tmp_path: Path) -> None:
    _make_importlinter(tmp_path)
    with patch("subprocess.run", return_value=_violation_result(MULTI_VIOLATION_OUTPUT)):
        result = ImportLinterAnalyzer(str(tmp_path)).analyze(["src/foo.py"])
    contracts = {r["contract"] for r in result}
    assert "Layers contract" in contracts
    assert "Independence contract" in contracts


# ---------------------------------------------------------------------------
# Tests: edge cases
# ---------------------------------------------------------------------------

def test_returns_empty_on_timeout(tmp_path: Path) -> None:
    _make_importlinter(tmp_path)
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="lint-imports", timeout=60)):
        result = ImportLinterAnalyzer(str(tmp_path)).analyze(["src/foo.py"])
    assert result == []


def test_returns_empty_on_nonzero_exit_with_empty_output(tmp_path: Path) -> None:
    _make_importlinter(tmp_path)
    empty_violation = _violation_result("")
    with patch("subprocess.run", return_value=empty_violation):
        result = ImportLinterAnalyzer(str(tmp_path)).analyze(["src/foo.py"])
    assert result == []


def test_file_paths_param_accepted(tmp_path: Path) -> None:
    """file_paths is accepted even when v1 doesn't filter by file."""
    _make_importlinter(tmp_path)
    with patch("subprocess.run", return_value=_ok_result()):
        result = ImportLinterAnalyzer(str(tmp_path)).analyze(["a.py", "b.py", "c.py"])
    assert result == []


def test_real_temp_importlinter_file(tmp_path: Path) -> None:
    """Analyzer instantiates and detects the real temp config file."""
    _make_importlinter(tmp_path)
    with patch("subprocess.run", return_value=_ok_result()):
        result = ImportLinterAnalyzer(str(tmp_path)).analyze([])
    assert result == []
