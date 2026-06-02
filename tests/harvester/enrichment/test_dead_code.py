"""Tests for VultureAnalyzer (dead_code.py)."""
from __future__ import annotations

import sys
from unittest.mock import patch

from chips.harvester.enrichment.dead_code import VultureAnalyzer


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
    result = VultureAnalyzer().analyze([])
    assert result == []


def test_returns_empty_for_non_py_files():
    result = VultureAnalyzer().analyze(["foo.ts", "bar.go", "baz.dart"])
    assert result == []


def test_skips_non_py_files_in_mixed_list(tmp_path):
    code = "def unused_func():\n    pass\n"
    py_file = _write(tmp_path, "mod.py", code)
    result = VultureAnalyzer().analyze([py_file, "other.ts", "other.go"])
    assert all(r["file"] == py_file for r in result)


# ---------------------------------------------------------------------------
# ImportError guard
# ---------------------------------------------------------------------------

def test_returns_empty_when_vulture_not_importable(tmp_path):
    code = "def unused_func():\n    pass\n"
    py_file = _write(tmp_path, "mod.py", code)
    with patch.dict(sys.modules, {"vulture": None}):
        result = VultureAnalyzer().analyze([py_file])
    assert result == []


# ---------------------------------------------------------------------------
# Real file — no dead code
# ---------------------------------------------------------------------------

def test_returns_empty_for_file_with_no_dead_code(tmp_path):
    code = (
        "def greet(name: str) -> str:\n"
        "    return f'Hello {name}'\n"
        "\n"
        "result = greet('world')\n"
        "print(result)\n"
    )
    py_file = _write(tmp_path, "clean.py", code)
    result = VultureAnalyzer().analyze([py_file])
    # 'result' might be flagged as unused variable depending on vulture version;
    # the important thing is 'greet' is NOT flagged
    names = {r["name"] for r in result}
    assert "greet" not in names


# ---------------------------------------------------------------------------
# Real file — unused function detected
# ---------------------------------------------------------------------------

def test_detects_unused_function(tmp_path):
    code = (
        "def used():\n"
        "    return 1\n"
        "\n"
        "def unused_func():\n"
        "    return 2\n"
        "\n"
        "x = used()\n"
    )
    py_file = _write(tmp_path, "mod.py", code)
    result = VultureAnalyzer().analyze([py_file])
    names = {r["name"] for r in result}
    assert "unused_func" in names


def test_unused_function_has_type_unused_function(tmp_path):
    code = (
        "def used():\n"
        "    return 1\n"
        "\n"
        "def unused_func():\n"
        "    return 2\n"
        "\n"
        "x = used()\n"
    )
    py_file = _write(tmp_path, "mod.py", code)
    result = VultureAnalyzer().analyze([py_file])
    func_findings = [r for r in result if r["name"] == "unused_func"]
    assert len(func_findings) >= 1
    assert func_findings[0]["type"] == "unused_function"


# ---------------------------------------------------------------------------
# Real file — unused class detected
# ---------------------------------------------------------------------------

def test_detects_unused_class(tmp_path):
    code = (
        "class UsedClass:\n"
        "    pass\n"
        "\n"
        "class UnusedClass:\n"
        "    pass\n"
        "\n"
        "obj = UsedClass()\n"
    )
    py_file = _write(tmp_path, "mod.py", code)
    result = VultureAnalyzer().analyze([py_file])
    names = {r["name"] for r in result}
    assert "UnusedClass" in names


def test_unused_class_has_type_unused_class(tmp_path):
    code = (
        "class UsedClass:\n"
        "    pass\n"
        "\n"
        "class UnusedClass:\n"
        "    pass\n"
        "\n"
        "obj = UsedClass()\n"
    )
    py_file = _write(tmp_path, "mod.py", code)
    result = VultureAnalyzer().analyze([py_file])
    cls_findings = [r for r in result if r["name"] == "UnusedClass"]
    assert len(cls_findings) >= 1
    assert cls_findings[0]["type"] == "unused_class"


# ---------------------------------------------------------------------------
# Result dict structure
# ---------------------------------------------------------------------------

def test_result_dicts_have_required_keys(tmp_path):
    code = (
        "def used():\n"
        "    return 1\n"
        "\n"
        "def unused_func():\n"
        "    return 2\n"
        "\n"
        "x = used()\n"
    )
    py_file = _write(tmp_path, "mod.py", code)
    result = VultureAnalyzer().analyze([py_file])
    assert len(result) > 0
    for r in result:
        assert "file" in r
        assert "line" in r
        assert "name" in r
        assert "type" in r
        assert "confidence" in r


def test_type_values_start_with_unused(tmp_path):
    code = (
        "def used():\n"
        "    return 1\n"
        "\n"
        "def unused_func():\n"
        "    return 2\n"
        "\n"
        "x = used()\n"
    )
    py_file = _write(tmp_path, "mod.py", code)
    result = VultureAnalyzer().analyze([py_file])
    for r in result:
        assert r["type"].startswith("unused_"), f"Unexpected type: {r['type']}"


def test_confidence_is_int_between_0_and_100(tmp_path):
    code = (
        "def used():\n"
        "    return 1\n"
        "\n"
        "def unused_func():\n"
        "    return 2\n"
        "\n"
        "x = used()\n"
    )
    py_file = _write(tmp_path, "mod.py", code)
    result = VultureAnalyzer().analyze([py_file])
    for r in result:
        assert isinstance(r["confidence"], int)
        assert 0 <= r["confidence"] <= 100


def test_line_is_int(tmp_path):
    code = "def unused_func():\n    pass\n"
    py_file = _write(tmp_path, "mod.py", code)
    result = VultureAnalyzer().analyze([py_file])
    for r in result:
        assert isinstance(r["line"], int)


# ---------------------------------------------------------------------------
# min_confidence filtering
# ---------------------------------------------------------------------------

def test_min_confidence_100_filters_low_confidence_findings(tmp_path):
    code = (
        "def used():\n"
        "    return 1\n"
        "\n"
        "def unused_func():\n"
        "    return 2\n"
        "\n"
        "x = used()\n"
    )
    py_file = _write(tmp_path, "mod.py", code)
    result_60 = VultureAnalyzer(min_confidence=60).analyze([py_file])
    result_100 = VultureAnalyzer(min_confidence=100).analyze([py_file])
    # High confidence threshold should return same or fewer items
    assert len(result_100) <= len(result_60)


def test_min_confidence_0_includes_everything(tmp_path):
    code = (
        "def used():\n"
        "    return 1\n"
        "\n"
        "def unused_func():\n"
        "    return 2\n"
        "\n"
        "x = used()\n"
    )
    py_file = _write(tmp_path, "mod.py", code)
    result_0 = VultureAnalyzer(min_confidence=0).analyze([py_file])
    result_60 = VultureAnalyzer(min_confidence=60).analyze([py_file])
    assert len(result_0) >= len(result_60)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_handles_file_that_does_not_exist():
    result = VultureAnalyzer().analyze(["/nonexistent/path/file.py"])
    assert result == []


def test_handles_empty_py_file(tmp_path):
    py_file = _write(tmp_path, "empty.py", "")
    result = VultureAnalyzer().analyze([py_file])
    assert result == []


def test_last_status_defaults_to_skipped_before_run():
    assert VultureAnalyzer().last_status == "skipped"


def test_last_status_ok_after_real_run(tmp_path):
    code = "def used():\n    return 1\n\nx = used()\n"
    py_file = _write(tmp_path, "mod.py", code)
    analyzer = VultureAnalyzer()
    analyzer.analyze([py_file])
    assert analyzer.last_status == "ok"


def test_last_status_skipped_when_no_py_files():
    analyzer = VultureAnalyzer()
    analyzer.analyze(["foo.ts", "bar.go"])
    assert analyzer.last_status == "skipped"


def test_last_status_not_installed_when_vulture_absent(tmp_path):
    code = "def unused_func():\n    pass\n"
    py_file = _write(tmp_path, "mod.py", code)
    analyzer = VultureAnalyzer()
    with patch.dict(sys.modules, {"vulture": None}):
        analyzer.analyze([py_file])
    assert analyzer.last_status == "not_installed"


def test_last_status_failed_on_per_file_error(tmp_path):
    code = "def used():\n    return 1\n\nx = used()\n"
    py_file = _write(tmp_path, "mod.py", code)
    analyzer = VultureAnalyzer()
    with patch("vulture.Vulture", side_effect=RuntimeError("boom")):
        result = analyzer.analyze([py_file])
    # The error is surfaced via status, not swallowed into a false-clean.
    assert analyzer.last_status == "failed"
    assert result == []


def test_multiple_files_processed_in_one_call(tmp_path):
    code_a = (
        "def used_a():\n"
        "    return 1\n"
        "\n"
        "def unused_a():\n"
        "    return 2\n"
        "\n"
        "x = used_a()\n"
    )
    code_b = (
        "def used_b():\n"
        "    return 3\n"
        "\n"
        "def unused_b():\n"
        "    return 4\n"
        "\n"
        "y = used_b()\n"
    )
    file_a = _write(tmp_path, "mod_a.py", code_a)
    file_b = _write(tmp_path, "mod_b.py", code_b)
    result = VultureAnalyzer().analyze([file_a, file_b])
    names = {r["name"] for r in result}
    assert "unused_a" in names
    assert "unused_b" in names
