from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from chips.harvester.enrichment.pyrefly import PyreflyAnalyzer


def _analyzer(config_path: str | None = None) -> PyreflyAnalyzer:
    return PyreflyAnalyzer(repo_path="/fake/repo", config_path=config_path)


def _errors_response(errors: list[dict] | None = None) -> MagicMock:
    return MagicMock(returncode=0 if not errors else 1, stdout=json.dumps(errors or []))


def _coverage_response(files: dict | None = None) -> MagicMock:
    return MagicMock(returncode=0, stdout=json.dumps({"files": files or {}}))


# ── Basic behaviour ───────────────────────────────────────────────────────────

def test_analyze_returns_dict_with_required_keys():
    result = _analyzer().analyze([])
    assert "errors" in result
    assert "coverage" in result
    assert "backend" in result


def test_analyze_backend_is_pyrefly():
    assert _analyzer().analyze([])["backend"] == "pyrefly"


def test_analyze_returns_empty_for_no_files():
    result = _analyzer().analyze([])
    assert result["errors"] == []
    assert result["coverage"] == {}


def test_analyze_skips_non_python_files():
    result = _analyzer().analyze(["README.md", "package.json", "Dockerfile"])
    assert result["errors"] == []
    assert result["coverage"] == {}


def test_analyze_processes_py_files():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [_errors_response(), _coverage_response()]
        _analyzer().analyze(["src/auth/token.py"])
    assert mock_run.call_count == 2


# ── Error parsing ─────────────────────────────────────────────────────────────

def test_check_errors_parses_single_error():
    errors = [
        {
            "code": "bad-argument-type",
            "message": "Expected int, got str",
            "path": "src/auth/token.py",
            "range": {"start": {"line": 10, "character": 5}, "end": {"line": 10, "character": 15}},
        }
    ]
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [_errors_response(errors), _coverage_response()]
        result = _analyzer().analyze(["src/auth/token.py"])
    assert len(result["errors"]) == 1
    assert result["errors"][0]["code"] == "bad-argument-type"
    assert result["errors"][0]["message"] == "Expected int, got str"
    assert result["errors"][0]["path"] == "src/auth/token.py"
    assert result["errors"][0]["line"] == 10


def test_check_errors_parses_multiple_errors():
    errors = [
        {"code": "bad-return-type", "message": "msg1", "path": "a.py", "range": {"start": {"line": 1}}},
        {"code": "missing-attribute", "message": "msg2", "path": "b.py", "range": {"start": {"line": 5}}},
    ]
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [_errors_response(errors), _coverage_response()]
        result = _analyzer().analyze(["a.py", "b.py"])
    assert len(result["errors"]) == 2


def test_check_errors_returns_empty_for_clean_file():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [_errors_response([]), _coverage_response()]
        result = _analyzer().analyze(["src/clean.py"])
    assert result["errors"] == []


def test_check_errors_returns_empty_when_pyrefly_not_installed():
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = _analyzer().analyze(["src/auth/token.py"])
    assert result["errors"] == []


def test_check_errors_returns_empty_on_invalid_json():
    bad = MagicMock(returncode=1, stdout="not json output")
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [bad, _coverage_response()]
        result = _analyzer().analyze(["src/auth/token.py"])
    assert result["errors"] == []


def test_check_errors_returns_empty_on_empty_stdout():
    empty = MagicMock(returncode=0, stdout="")
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [empty, _coverage_response()]
        result = _analyzer().analyze(["src/auth/token.py"])
    assert result["errors"] == []


def test_check_errors_handles_missing_range_gracefully():
    errors = [{"code": "unknown-name", "message": "x is not defined", "path": "src/a.py"}]
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [_errors_response(errors), _coverage_response()]
        result = _analyzer().analyze(["src/a.py"])
    assert result["errors"][0]["line"] == 0


# ── Coverage parsing ──────────────────────────────────────────────────────────

def test_check_coverage_parses_annotation_completeness():
    files = {
        "src/auth/token.py": {"annotation_completeness": 0.75, "type_completeness": 0.82}
    }
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [_errors_response(), _coverage_response(files)]
        result = _analyzer().analyze(["src/auth/token.py"])
    assert "src/auth/token.py" in result["coverage"]
    assert result["coverage"]["src/auth/token.py"]["annotation_completeness"] == 0.75
    assert result["coverage"]["src/auth/token.py"]["type_completeness"] == 0.82


def test_check_coverage_returns_empty_when_pyrefly_not_installed():
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = _analyzer().analyze(["src/auth/token.py"])
    assert result["coverage"] == {}


def test_check_coverage_returns_empty_on_invalid_json():
    bad_coverage = MagicMock(returncode=0, stdout="not json")
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [_errors_response(), bad_coverage]
        result = _analyzer().analyze(["src/auth/token.py"])
    assert result["coverage"] == {}


def test_check_coverage_returns_empty_for_project_with_no_files_key():
    no_files = MagicMock(returncode=0, stdout=json.dumps({}))
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [_errors_response(), no_files]
        result = _analyzer().analyze(["src/auth/token.py"])
    assert result["coverage"] == {}


# ── Config path forwarding ────────────────────────────────────────────────────

def test_config_path_passed_to_check_command():
    analyzer = _analyzer(config_path="/fake/pyrefly.toml")
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [_errors_response(), _coverage_response()]
        analyzer.analyze(["src/auth/token.py"])
    check_cmd = mock_run.call_args_list[0][0][0]
    assert "--config" in check_cmd
    assert "/fake/pyrefly.toml" in check_cmd


def test_config_path_passed_to_coverage_command():
    analyzer = _analyzer(config_path="/fake/pyrefly.toml")
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [_errors_response(), _coverage_response()]
        analyzer.analyze(["src/auth/token.py"])
    coverage_cmd = mock_run.call_args_list[1][0][0]
    assert "--config" in coverage_cmd
    assert "/fake/pyrefly.toml" in coverage_cmd


def test_no_config_path_omits_config_flag():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [_errors_response(), _coverage_response()]
        _analyzer().analyze(["src/auth/token.py"])
    check_cmd = mock_run.call_args_list[0][0][0]
    assert "--config" not in check_cmd
