from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch

from chips.harvester.enrichment.security import BanditAnalyzer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bandit_result(results: list[dict], returncode: int = 1) -> MagicMock:
    """Build a mock subprocess.CompletedProcess with valid bandit JSON output."""
    payload = {
        "errors": [],
        "generated_at": "2026-01-01T00:00:00Z",
        "metrics": {},
        "results": results,
    }
    return MagicMock(returncode=returncode, stdout=json.dumps(payload), stderr="")


def _finding(
    filename: str = "/repo/src/auth.py",
    line_number: int = 42,
    test_id: str = "B602",
    test_name: str = "subprocess_popen_with_shell_equals_true",
    issue_severity: str = "HIGH",
    issue_confidence: str = "HIGH",
    issue_text: str = "subprocess call with shell=True identified.",
) -> dict:
    """Build a single bandit result entry."""
    return {
        "filename": filename,
        "line_number": line_number,
        "test_id": test_id,
        "test_name": test_name,
        "issue_severity": issue_severity,
        "issue_confidence": issue_confidence,
        "issue_text": issue_text,
        "code": "subprocess.run(cmd, shell=True)",
        "col_offset": 0,
    }


# ---------------------------------------------------------------------------
# Basic behaviour
# ---------------------------------------------------------------------------

def test_returns_empty_for_empty_file_list():
    result = BanditAnalyzer().analyze([])
    assert result == []


def test_returns_empty_for_non_py_files_only():
    """No .py files — bandit should never be called and [] returned."""
    with patch("subprocess.run") as mock_run:
        result = BanditAnalyzer().analyze(["README.md", "package.json", "Dockerfile"])
    assert result == []
    mock_run.assert_not_called()


def test_filters_non_py_from_mixed_list():
    """Only .py files are forwarded to bandit."""
    finding = _finding(filename="/repo/auth.py")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = _bandit_result([finding])
        BanditAnalyzer().analyze(["auth.py", "README.md", "config.json"])
    called_cmd = mock_run.call_args[0][0]
    # Only auth.py should be in the command
    assert "auth.py" in called_cmd
    assert "README.md" not in called_cmd
    assert "config.json" not in called_cmd


def test_returns_empty_when_bandit_not_installed():
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = BanditAnalyzer().analyze(["src/auth.py"])
    assert result == []


# ---------------------------------------------------------------------------
# JSON parsing and field mapping
# ---------------------------------------------------------------------------

def test_parses_bandit_json_output_correctly():
    finding = _finding()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = _bandit_result([finding])
        result = BanditAnalyzer(severity_threshold="LOW").analyze(["/repo/src/auth.py"])
    assert len(result) == 1


def test_maps_bandit_fields_to_schema():
    finding = _finding(
        filename="/repo/src/auth.py",
        line_number=10,
        test_id="B602",
        test_name="subprocess_popen_with_shell_equals_true",
        issue_severity="HIGH",
        issue_confidence="HIGH",
        issue_text="subprocess call with shell=True identified.",
    )
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = _bandit_result([finding])
        result = BanditAnalyzer(severity_threshold="LOW").analyze(["/repo/src/auth.py"])
    r = result[0]
    assert r["file"] == "/repo/src/auth.py"
    assert r["line"] == 10
    assert r["test_id"] == "B602"
    assert r["test_name"] == "subprocess_popen_with_shell_equals_true"
    assert r["severity"] == "HIGH"
    assert r["confidence"] == "HIGH"
    assert r["message"] == "subprocess call with shell=True identified."


def test_result_dicts_have_required_keys():
    finding = _finding()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = _bandit_result([finding])
        result = BanditAnalyzer(severity_threshold="LOW").analyze(["/repo/src/auth.py"])
    required = {"file", "line", "test_id", "test_name", "severity", "confidence", "message"}
    for r in result:
        assert required.issubset(r.keys()), f"Missing keys: {required - r.keys()}"


# ---------------------------------------------------------------------------
# Severity threshold filtering
# ---------------------------------------------------------------------------

def test_threshold_low_keeps_all_findings():
    findings = [
        _finding(issue_severity="LOW"),
        _finding(issue_severity="MEDIUM"),
        _finding(issue_severity="HIGH"),
    ]
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = _bandit_result(findings)
        result = BanditAnalyzer(severity_threshold="LOW").analyze(["/repo/src/auth.py"])
    assert len(result) == 3


def test_threshold_medium_filters_out_low():
    findings = [
        _finding(issue_severity="LOW"),
        _finding(issue_severity="MEDIUM"),
        _finding(issue_severity="HIGH"),
    ]
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = _bandit_result(findings)
        result = BanditAnalyzer(severity_threshold="MEDIUM").analyze(["/repo/src/auth.py"])
    severities = {r["severity"] for r in result}
    assert "LOW" not in severities
    assert len(result) == 2


def test_threshold_high_filters_out_low_and_medium():
    findings = [
        _finding(issue_severity="LOW"),
        _finding(issue_severity="MEDIUM"),
        _finding(issue_severity="HIGH"),
    ]
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = _bandit_result(findings)
        result = BanditAnalyzer(severity_threshold="HIGH").analyze(["/repo/src/auth.py"])
    assert len(result) == 1
    assert result[0]["severity"] == "HIGH"


# ---------------------------------------------------------------------------
# Exit-code and error handling
# ---------------------------------------------------------------------------

def test_handles_exit_code_1_with_valid_json():
    """Bandit exits 1 when findings exist — we must still parse the JSON."""
    finding = _finding()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = _bandit_result([finding], returncode=1)
        result = BanditAnalyzer(severity_threshold="LOW").analyze(["/repo/src/auth.py"])
    assert len(result) == 1


def test_handles_empty_results_array():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = _bandit_result([], returncode=0)
        result = BanditAnalyzer().analyze(["/repo/src/auth.py"])
    assert result == []


def test_handles_invalid_json_on_non_zero_exit():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=2, stdout="", stderr="fatal error")
        result = BanditAnalyzer().analyze(["/repo/src/auth.py"])
    assert result == []


def test_handles_subprocess_timeout():
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="bandit", timeout=120)):
        result = BanditAnalyzer().analyze(["/repo/src/auth.py"])
    assert result == []


def test_last_status_defaults_to_skipped():
    assert BanditAnalyzer().last_status == "skipped"


def test_last_status_ok_on_success():
    finding = _finding()
    analyzer = BanditAnalyzer()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = _bandit_result([finding])
        analyzer.analyze(["/repo/src/auth.py"])
    assert analyzer.last_status == "ok"


def test_last_status_not_installed_when_bandit_missing():
    analyzer = BanditAnalyzer()
    with patch("subprocess.run", side_effect=FileNotFoundError):
        analyzer.analyze(["/repo/src/auth.py"])
    assert analyzer.last_status == "not_installed"


def test_last_status_timed_out_when_bandit_times_out():
    analyzer = BanditAnalyzer()
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="bandit", timeout=120)):
        analyzer.analyze(["/repo/src/auth.py"])
    assert analyzer.last_status == "timed_out"


def test_last_status_failed_on_invalid_json():
    analyzer = BanditAnalyzer()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=2, stdout="", stderr="fatal error")
        analyzer.analyze(["/repo/src/auth.py"])
    assert analyzer.last_status == "failed"


# ---------------------------------------------------------------------------
# Valid enum values
# ---------------------------------------------------------------------------

def test_severity_values_are_valid_enum():
    findings = [
        _finding(issue_severity="LOW"),
        _finding(issue_severity="MEDIUM"),
        _finding(issue_severity="HIGH"),
    ]
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = _bandit_result(findings)
        result = BanditAnalyzer(severity_threshold="LOW").analyze(["/repo/src/auth.py"])
    valid = {"LOW", "MEDIUM", "HIGH"}
    for r in result:
        assert r["severity"] in valid


def test_confidence_values_are_valid_enum():
    findings = [
        _finding(issue_confidence="LOW"),
        _finding(issue_confidence="MEDIUM"),
        _finding(issue_confidence="HIGH"),
    ]
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = _bandit_result(findings)
        result = BanditAnalyzer(severity_threshold="LOW").analyze(["/repo/src/auth.py"])
    valid = {"LOW", "MEDIUM", "HIGH"}
    for r in result:
        assert r["confidence"] in valid
