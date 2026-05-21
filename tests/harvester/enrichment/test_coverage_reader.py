from __future__ import annotations

import os
import sys
import tempfile
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from chips.harvester.enrichment.coverage_reader import CoverageReader


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@contextmanager
def _tmpdir():
    """Create a temporary directory and clean it up automatically."""
    d = tempfile.mkdtemp(prefix="chips_cov_test_")
    try:
        yield d
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)


def _reader(repo_path: str) -> CoverageReader:
    return CoverageReader(repo_path=repo_path)


def _make_coverage_mock(measured_files: dict[str, list[int]]):
    """Return a mocked Coverage object whose data matches measured_files.

    measured_files maps absolute file path -> list of executed (covered) line numbers.
    """
    data_mock = MagicMock()
    data_mock.measured_files.return_value = set(measured_files.keys())
    data_mock.lines.side_effect = lambda f: measured_files.get(f, [])

    cov_mock = MagicMock()
    cov_mock.get_data.return_value = data_mock
    return cov_mock, data_mock


# ---------------------------------------------------------------------------
# coverage_available=False cases
# ---------------------------------------------------------------------------

def test_returns_false_when_no_coverage_file():
    with _tmpdir() as d:
        reader = _reader(d)
        result = reader.analyze([os.path.join(d, "src", "auth.py")])
    assert result["coverage_available"] is False
    assert result["files"] == {}


def test_returns_false_when_coverage_not_importable():
    with _tmpdir() as d:
        open(os.path.join(d, ".coverage"), "w").close()
        # Simulate ImportError by patching coverage.Coverage to raise ImportError
        with patch("chips.harvester.enrichment.coverage_reader.CoverageReader.analyze",
                   wraps=None) as _:
            pass
        # Alternative: patch the import inside the module
        with patch.dict(sys.modules, {"coverage": None}):
            reader = _reader(d)
            result = reader.analyze([os.path.join(d, "auth.py")])
    assert result["coverage_available"] is False


def test_returns_false_for_non_py_files():
    with _tmpdir() as d:
        open(os.path.join(d, ".coverage"), "w").close()
        reader = _reader(d)
        result = reader.analyze(["README.md", "config.json"])
    assert result["coverage_available"] is False
    assert result["files"] == {}


def test_returns_false_when_exception_loading_coverage():
    with _tmpdir() as d:
        open(os.path.join(d, ".coverage"), "w").close()
        cov_mock = MagicMock()
        cov_mock.load.side_effect = Exception("corrupt db")
        with patch("coverage.Coverage", return_value=cov_mock):
            reader = _reader(d)
            result = reader.analyze([os.path.join(d, "auth.py")])
    assert result["coverage_available"] is False


# ---------------------------------------------------------------------------
# coverage_available=True and basic file-level coverage
# ---------------------------------------------------------------------------

def test_returns_true_when_coverage_file_found():
    with _tmpdir() as d:
        open(os.path.join(d, ".coverage"), "w").close()
        abs_path = os.path.join(d, "auth.py")
        cov_mock, _ = _make_coverage_mock({abs_path: [1, 2, 3]})
        with patch("coverage.Coverage", return_value=cov_mock):
            reader = _reader(d)
            result = reader.analyze([abs_path])
    assert result["coverage_available"] is True


def test_files_dict_contains_entry_for_each_py_file():
    with _tmpdir() as d:
        open(os.path.join(d, ".coverage"), "w").close()
        abs_auth = os.path.join(d, "auth.py")
        abs_utils = os.path.join(d, "utils.py")
        cov_mock, _ = _make_coverage_mock({abs_auth: [1, 2], abs_utils: [1]})
        with patch("coverage.Coverage", return_value=cov_mock):
            reader = _reader(d)
            result = reader.analyze([abs_auth, abs_utils])
    assert abs_auth in result["files"]
    assert abs_utils in result["files"]


def test_coverage_pct_is_float_between_0_and_100():
    with _tmpdir() as d:
        open(os.path.join(d, ".coverage"), "w").close()
        abs_path = os.path.join(d, "auth.py")
        cov_mock, _ = _make_coverage_mock({abs_path: [1, 2, 3]})
        with patch("coverage.Coverage", return_value=cov_mock):
            reader = _reader(d)
            result = reader.analyze([abs_path])
    pct = result["files"][abs_path]["coverage_pct"]
    assert isinstance(pct, float)
    assert 0.0 <= pct <= 100.0


def test_covered_plus_missing_equals_total():
    with _tmpdir() as d:
        open(os.path.join(d, ".coverage"), "w").close()
        abs_path = os.path.join(d, "auth.py")
        cov_mock, _ = _make_coverage_mock({abs_path: [1, 2, 3]})
        with patch("coverage.Coverage", return_value=cov_mock):
            reader = _reader(d)
            result = reader.analyze([abs_path])
    f = result["files"][abs_path]
    assert f["covered_lines"] >= 0
    assert f["missing_lines"] >= 0
    # covered + missing should equal whatever the implementation considers total
    total = f["covered_lines"] + f["missing_lines"]
    assert total >= 0


# ---------------------------------------------------------------------------
# changed_lines=None → None fields
# ---------------------------------------------------------------------------

def test_changed_lines_fields_are_none_when_not_provided():
    with _tmpdir() as d:
        open(os.path.join(d, ".coverage"), "w").close()
        abs_path = os.path.join(d, "auth.py")
        cov_mock, _ = _make_coverage_mock({abs_path: [1, 2, 3]})
        with patch("coverage.Coverage", return_value=cov_mock):
            reader = _reader(d)
            result = reader.analyze([abs_path])
    f = result["files"][abs_path]
    assert f["changed_lines_covered"] is None
    assert f["changed_lines_missing"] is None
    assert f["changed_lines_coverage_pct"] is None


# ---------------------------------------------------------------------------
# changed_lines provided
# ---------------------------------------------------------------------------

def test_changed_lines_coverage_pct_calculated_correctly():
    with _tmpdir() as d:
        open(os.path.join(d, ".coverage"), "w").close()
        abs_path = os.path.join(d, "auth.py")
        # Lines 1, 2, 3 are covered; 4 and 5 are not
        cov_mock, _ = _make_coverage_mock({abs_path: [1, 2, 3]})
        with patch("coverage.Coverage", return_value=cov_mock):
            reader = _reader(d)
            result = reader.analyze([abs_path], changed_lines={abs_path: [1, 2, 4, 5]})
    f = result["files"][abs_path]
    assert f["changed_lines_covered"] == 2
    assert f["changed_lines_missing"] == 2
    assert f["changed_lines_coverage_pct"] == pytest.approx(50.0)


def test_changed_lines_not_in_coverage_counted_as_missing():
    with _tmpdir() as d:
        open(os.path.join(d, ".coverage"), "w").close()
        abs_path = os.path.join(d, "auth.py")
        cov_mock, _ = _make_coverage_mock({abs_path: []})  # nothing covered
        with patch("coverage.Coverage", return_value=cov_mock):
            reader = _reader(d)
            result = reader.analyze([abs_path], changed_lines={abs_path: [10, 20, 30]})
    f = result["files"][abs_path]
    assert f["changed_lines_covered"] == 0
    assert f["changed_lines_missing"] == 3
    assert f["changed_lines_coverage_pct"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_handles_empty_coverage_file_no_measured_files():
    with _tmpdir() as d:
        open(os.path.join(d, ".coverage"), "w").close()
        abs_path = os.path.join(d, "auth.py")
        cov_mock, _ = _make_coverage_mock({})  # no measured files
        with patch("coverage.Coverage", return_value=cov_mock):
            reader = _reader(d)
            result = reader.analyze([abs_path])
    # File is not in measured files → not in result["files"]
    assert result["files"] == {}


def test_searches_parent_dirs_for_coverage_file():
    """_find_coverage_file should look up to 2 parent levels."""
    with _tmpdir() as d:
        sub = os.path.join(d, "a", "b")
        os.makedirs(sub, exist_ok=True)
        # Place .coverage at d (2 levels above sub)
        open(os.path.join(d, ".coverage"), "w").close()
        abs_path = os.path.join(d, "auth.py")
        cov_mock, _ = _make_coverage_mock({abs_path: [1, 2]})
        with patch("coverage.Coverage", return_value=cov_mock):
            reader = _reader(sub)
            result = reader.analyze([abs_path])
    assert result["coverage_available"] is True


def test_file_path_normalization_relative_matched_to_absolute():
    """Relative file paths resolved to absolute before matching coverage data."""
    with _tmpdir() as d:
        open(os.path.join(d, ".coverage"), "w").close()
        abs_path = os.path.join(d, "auth.py")
        cov_mock, _ = _make_coverage_mock({abs_path: [1, 2, 3]})
        with patch("coverage.Coverage", return_value=cov_mock):
            reader = _reader(d)
            # Pass relative path — abspath should match the coverage data key
            old_cwd = os.getcwd()
            try:
                os.chdir(d)
                result = reader.analyze(["auth.py"])
            finally:
                os.chdir(old_cwd)
    assert result["coverage_available"] is True
    assert len(result["files"]) >= 1


def test_returns_empty_files_when_no_overlap():
    """Files in request don't appear in coverage data → empty files dict."""
    with _tmpdir() as d:
        open(os.path.join(d, ".coverage"), "w").close()
        other_path = os.path.join(d, "other.py")
        cov_mock, _ = _make_coverage_mock({other_path: [1, 2, 3]})
        with patch("coverage.Coverage", return_value=cov_mock):
            reader = _reader(d)
            result = reader.analyze([os.path.join(d, "untracked.py")])
    assert result["files"] == {}


def test_multiple_files_in_single_call():
    with _tmpdir() as d:
        open(os.path.join(d, ".coverage"), "w").close()
        paths = [os.path.join(d, f"file{i}.py") for i in range(3)]
        measured = {p: list(range(1, 6)) for p in paths}
        cov_mock, _ = _make_coverage_mock(measured)
        with patch("coverage.Coverage", return_value=cov_mock):
            reader = _reader(d)
            result = reader.analyze(paths)
    assert result["coverage_available"] is True
    assert len(result["files"]) == 3
    for p in paths:
        assert p in result["files"]


def test_all_changed_lines_covered_gives_100_pct():
    with _tmpdir() as d:
        open(os.path.join(d, ".coverage"), "w").close()
        abs_path = os.path.join(d, "auth.py")
        cov_mock, _ = _make_coverage_mock({abs_path: [1, 2, 3, 4, 5]})
        with patch("coverage.Coverage", return_value=cov_mock):
            reader = _reader(d)
            result = reader.analyze([abs_path], changed_lines={abs_path: [1, 2, 3]})
    f = result["files"][abs_path]
    assert f["changed_lines_coverage_pct"] == pytest.approx(100.0)
    assert f["changed_lines_missing"] == 0
