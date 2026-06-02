"""Tests for GriffeAnalyzer (api_surface.py)."""
from __future__ import annotations

import sys
from unittest.mock import patch

from chips.harvester.enrichment.api_surface import GriffeAnalyzer

VALID_CHANGE_TYPES = {
    "missing_return_annotation",
    "missing_param_annotation",
    "undocumented_public_api",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(tmp_path, name: str, code: str) -> str:
    p = tmp_path / name
    p.write_text(code, encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------------------
# Basic / boundary tests
# ---------------------------------------------------------------------------

def test_returns_empty_for_empty_file_list():
    result = GriffeAnalyzer().analyze([])
    assert result == []


def test_returns_empty_for_non_py_files():
    result = GriffeAnalyzer().analyze(["foo.ts", "bar.go", "baz.dart"])
    assert result == []


def test_skips_non_py_files_processes_py_in_mixed_list(tmp_path):
    code = "def public_func(x):\n    pass\n"
    py_file = _write(tmp_path, "mod.py", code)
    result = GriffeAnalyzer().analyze([py_file, "other.ts", "other.go"])
    # All findings must reference the .py file, not the skipped files
    assert all(r["file"] == py_file for r in result)


def test_skips_non_py_silently_no_error_raised(tmp_path):
    """Non-.py files in a mixed list do not raise exceptions."""
    code = "def annotated(x: int) -> int:\n    return x\n"
    py_file = _write(tmp_path, "clean.py", code)
    # Should not raise
    result = GriffeAnalyzer().analyze([py_file, "data.json", "Makefile"])
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# ImportError guard
# ---------------------------------------------------------------------------

def test_returns_empty_when_griffe_not_importable(tmp_path):
    code = "def func(x):\n    pass\n"
    py_file = _write(tmp_path, "mod.py", code)
    with patch.dict(sys.modules, {"griffe": None}):
        result = GriffeAnalyzer().analyze([py_file])
    assert result == []


# ---------------------------------------------------------------------------
# Missing return annotation
# ---------------------------------------------------------------------------

def test_detects_missing_return_annotation(tmp_path):
    code = "def public_func(x: int):\n    pass\n"
    py_file = _write(tmp_path, "mod.py", code)
    result = GriffeAnalyzer().analyze([py_file])
    types = {r["change_type"] for r in result}
    assert "missing_return_annotation" in types


def test_no_flag_when_return_annotation_present(tmp_path):
    code = "def public_func(x: int) -> int:\n    return x\n"
    py_file = _write(tmp_path, "clean.py", code)
    result = GriffeAnalyzer().analyze([py_file])
    types = {r["change_type"] for r in result}
    assert "missing_return_annotation" not in types


# ---------------------------------------------------------------------------
# Private / dunder exclusions
# ---------------------------------------------------------------------------

def test_does_not_flag_private_functions(tmp_path):
    code = "def _private(x):\n    pass\n"
    py_file = _write(tmp_path, "mod.py", code)
    result = GriffeAnalyzer().analyze([py_file])
    assert result == []


def test_does_not_flag_dunder_methods(tmp_path):
    code = (
        "class Foo:\n"
        "    def __init__(self, x):\n"
        "        self.x = x\n"
        "    def __str__(self):\n"
        "        return str(self.x)\n"
    )
    py_file = _write(tmp_path, "mod.py", code)
    result = GriffeAnalyzer().analyze([py_file])
    assert result == []


# ---------------------------------------------------------------------------
# Missing param annotation
# ---------------------------------------------------------------------------

def test_detects_missing_param_annotation(tmp_path):
    code = "def public_func(x, y: int) -> int:\n    return y\n"
    py_file = _write(tmp_path, "mod.py", code)
    result = GriffeAnalyzer().analyze([py_file])
    types = {r["change_type"] for r in result}
    assert "missing_param_annotation" in types


def test_does_not_flag_self_parameter(tmp_path):
    """self param without annotation should not produce missing_param_annotation."""
    code = (
        "class Foo:\n"
        "    def method(self, x: int) -> int:\n"
        "        return x\n"
    )
    py_file = _write(tmp_path, "mod.py", code)
    result = GriffeAnalyzer().analyze([py_file])
    types = {r["change_type"] for r in result}
    assert "missing_param_annotation" not in types


# ---------------------------------------------------------------------------
# Undocumented public API
# ---------------------------------------------------------------------------

def test_detects_undocumented_public_api(tmp_path):
    code = "def public_func(x: int) -> int:\n    return x\n"
    py_file = _write(tmp_path, "mod.py", code)
    result = GriffeAnalyzer().analyze([py_file])
    types = {r["change_type"] for r in result}
    assert "undocumented_public_api" in types


def test_no_flag_when_docstring_present(tmp_path):
    code = (
        'def public_func(x: int) -> int:\n'
        '    """Do something."""\n'
        '    return x\n'
    )
    py_file = _write(tmp_path, "clean.py", code)
    result = GriffeAnalyzer().analyze([py_file])
    types = {r["change_type"] for r in result}
    assert "undocumented_public_api" not in types


# ---------------------------------------------------------------------------
# File not found / empty file
# ---------------------------------------------------------------------------

def test_handles_file_that_does_not_exist():
    result = GriffeAnalyzer().analyze(["/nonexistent/path/file.py"])
    assert result == []


def test_handles_empty_py_file(tmp_path):
    py_file = _write(tmp_path, "empty.py", "")
    result = GriffeAnalyzer().analyze([py_file])
    assert result == []


# ---------------------------------------------------------------------------
# Fully-annotated file — no findings except docstring
# ---------------------------------------------------------------------------

def test_fully_annotated_function_no_annotation_findings(tmp_path):
    code = (
        'def fully_annotated(x: int, y: str) -> bool:\n'
        '    """Documented.\"\"\"\n'
        '    return True\n'
    )
    py_file = _write(tmp_path, "good.py", code)
    result = GriffeAnalyzer().analyze([py_file])
    types = {r["change_type"] for r in result}
    assert "missing_return_annotation" not in types
    assert "missing_param_annotation" not in types
    assert "undocumented_public_api" not in types


# ---------------------------------------------------------------------------
# Result dict structure
# ---------------------------------------------------------------------------

def test_result_dicts_have_required_keys(tmp_path):
    code = "def public_func(x):\n    pass\n"
    py_file = _write(tmp_path, "mod.py", code)
    result = GriffeAnalyzer().analyze([py_file])
    assert len(result) > 0
    for r in result:
        assert "file" in r
        assert "symbol" in r
        assert "change_type" in r
        assert "details" in r


def test_change_type_values_are_from_valid_set(tmp_path):
    code = "def public_func(x):\n    pass\n"
    py_file = _write(tmp_path, "mod.py", code)
    result = GriffeAnalyzer().analyze([py_file])
    for r in result:
        assert r["change_type"] in VALID_CHANGE_TYPES


def test_file_field_matches_input_path(tmp_path):
    code = "def public_func(x):\n    pass\n"
    py_file = _write(tmp_path, "mod.py", code)
    result = GriffeAnalyzer().analyze([py_file])
    for r in result:
        assert r["file"] == py_file


# ---------------------------------------------------------------------------
# Run status (Evidence > Guessing)
# ---------------------------------------------------------------------------

def test_last_status_defaults_to_skipped_before_run():
    assert GriffeAnalyzer().last_status == "skipped"


def test_last_status_ok_after_real_run(tmp_path):
    code = "def public_func(x):\n    pass\n"
    py_file = _write(tmp_path, "mod.py", code)
    analyzer = GriffeAnalyzer()
    analyzer.analyze([py_file])
    assert analyzer.last_status == "ok"


def test_last_status_skipped_when_no_py_files():
    analyzer = GriffeAnalyzer()
    analyzer.analyze(["foo.ts", "bar.go"])
    assert analyzer.last_status == "skipped"


def test_last_status_not_installed_when_griffe_absent(tmp_path):
    code = "def func(x):\n    pass\n"
    py_file = _write(tmp_path, "mod.py", code)
    analyzer = GriffeAnalyzer()
    with patch.dict(sys.modules, {"griffe": None}):
        analyzer.analyze([py_file])
    assert analyzer.last_status == "not_installed"


def test_last_status_failed_on_per_file_error(tmp_path):
    code = "def public_func(x):\n    pass\n"
    py_file = _write(tmp_path, "mod.py", code)
    analyzer = GriffeAnalyzer()
    with patch("griffe.visit", side_effect=RuntimeError("boom")):
        result = analyzer.analyze([py_file])
    assert analyzer.last_status == "failed"
    assert result == []
