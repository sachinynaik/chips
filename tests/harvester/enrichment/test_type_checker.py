from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from chips.harvester.enrichment.type_checker import TypeCheckerAnalyzer


def _tc(backend: str = "pyrefly", **kwargs) -> TypeCheckerAnalyzer:
    return TypeCheckerAnalyzer(backend=backend, repo_path="/fake/repo", **kwargs)


def _mock_subprocess(errors=None, coverage_files=None):
    errors_resp = MagicMock(returncode=0, stdout=json.dumps(errors or []))
    coverage_resp = MagicMock(
        returncode=0, stdout=json.dumps({"files": coverage_files or {}})
    )
    return [errors_resp, coverage_resp]


# ── Construction ──────────────────────────────────────────────────────────────

def test_default_backend_is_pyrefly():
    tc = TypeCheckerAnalyzer(repo_path="/fake/repo")
    assert tc.backend == "pyrefly"


def test_raises_on_unsupported_backend():
    with pytest.raises(ValueError, match="Unsupported backend"):
        TypeCheckerAnalyzer(backend="mypy", repo_path="/fake/repo")


def test_supported_backends_listed_in_error():
    with pytest.raises(ValueError, match="pyrefly"):
        TypeCheckerAnalyzer(backend="unknown", repo_path="/fake/repo")


# ── Delegation ────────────────────────────────────────────────────────────────

def test_analyze_delegates_to_pyrefly():
    tc = _tc(backend="pyrefly")
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = _mock_subprocess()
        result = tc.analyze(["src/auth/token.py"])
    assert result["backend"] == "pyrefly"


def test_analyze_returns_errors_from_backend():
    errors = [
        {"code": "bad-return-type", "message": "...", "path": "src/a.py",
         "range": {"start": {"line": 5}}}
    ]
    tc = _tc(backend="pyrefly")
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = _mock_subprocess(errors=errors)
        result = tc.analyze(["src/a.py"])
    assert len(result["errors"]) == 1
    assert result["errors"][0]["code"] == "bad-return-type"


def test_analyze_returns_coverage_from_backend():
    coverage = {"src/auth/token.py": {"annotation_completeness": 0.6, "type_completeness": 0.7}}
    tc = _tc(backend="pyrefly")
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = _mock_subprocess(coverage_files=coverage)
        result = tc.analyze(["src/auth/token.py"])
    assert "src/auth/token.py" in result["coverage"]


def test_analyze_returns_empty_for_no_files():
    result = _tc().analyze([])
    assert result["errors"] == []
    assert result["coverage"] == {}


# ── Config forwarding ─────────────────────────────────────────────────────────

def test_config_path_forwarded_to_backend():
    tc = TypeCheckerAnalyzer(
        backend="pyrefly", repo_path="/fake/repo", config_path="/fake/pyrefly.toml"
    )
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = _mock_subprocess()
        tc.analyze(["src/auth/token.py"])
    check_cmd = mock_run.call_args_list[0][0][0]
    assert "/fake/pyrefly.toml" in check_cmd


# ── Graceful fallback ─────────────────────────────────────────────────────────

def test_analyze_returns_empty_when_backend_not_installed():
    tc = _tc(backend="pyrefly")
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = tc.analyze(["src/auth/token.py"])
    assert result["errors"] == []
    assert result["coverage"] == {}


# ── Status passthrough ────────────────────────────────────────────────────────

def test_status_passed_through_from_backend_ok():
    tc = _tc(backend="pyrefly")
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = _mock_subprocess()
        result = tc.analyze(["src/auth/token.py"])
    assert result["status"] == "ok"


def test_status_passed_through_from_backend_not_installed():
    tc = _tc(backend="pyrefly")
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = tc.analyze(["src/auth/token.py"])
    assert result["status"] == "not_installed"
