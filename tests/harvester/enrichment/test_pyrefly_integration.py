"""Integration test for PyreflyAnalyzer against the real ``pyrefly`` binary.

Skipped when pyrefly is not on PATH. Proves the central Evidence > Guessing
invariant end-to-end: a clean file yields status ``ok`` with no errors, which
is distinct from the ``not_installed`` a missing binary would produce — so a
clean result can never be confused with a non-result.
"""
from __future__ import annotations

import shutil

import pytest

from chips.harvester.enrichment.pyrefly import PyreflyAnalyzer

pytestmark = pytest.mark.skipif(
    shutil.which("pyrefly") is None, reason="pyrefly not installed"
)


def _write(tmp_path, name: str, code: str) -> str:
    p = tmp_path / name
    p.write_text(code, encoding="utf-8")
    return str(p)


def test_real_pyrefly_reports_type_error(tmp_path):
    # Deliberate error: reference to an undefined name. This is flagged by
    # pyrefly's default ``basic`` preset (stricter checks like bad-return are
    # preset-dependent), so the assertion holds without a project config.
    code = "value: int = undefined_name_xyz\n"
    py_file = _write(tmp_path, "buggy.py", code)
    result = PyreflyAnalyzer(repo_path=str(tmp_path)).analyze([py_file])
    assert result["status"] == "ok"
    assert len(result["errors"]) >= 1


def test_real_pyrefly_clean_file_is_ok_not_not_installed(tmp_path):
    # A correctly annotated, type-clean file: ran successfully, zero errors.
    code = (
        "def add(x: int, y: int) -> int:\n"
        "    return x + y\n"
    )
    py_file = _write(tmp_path, "clean.py", code)
    result = PyreflyAnalyzer(repo_path=str(tmp_path)).analyze([py_file])
    assert result["status"] == "ok"
    assert result["errors"] == []
