from __future__ import annotations
import json
from unittest.mock import patch, MagicMock
from chips.harvester.enrichment.semgrep import SemgrepAnalyzer

def test_analyze_returns_findings():
    findings = [{"check_id": "python.security.audit.xss", "path": "src/web.py"}]
    output = json.dumps({"results": findings})
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout=output)
        result = SemgrepAnalyzer().analyze(["src/web.py"])
    assert len(result) == 1
    assert result[0]["check_id"] == "python.security.audit.xss"

def test_analyze_returns_empty_on_no_findings():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({"results": []}))
        result = SemgrepAnalyzer().analyze(["src/clean.py"])
    assert result == []

def test_analyze_returns_empty_when_semgrep_not_installed():
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = SemgrepAnalyzer().analyze(["src/auth.py"])
    assert result == []

def test_analyze_returns_empty_for_no_files():
    result = SemgrepAnalyzer().analyze([])
    assert result == []

def test_analyze_returns_empty_on_invalid_json():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="not json")
        result = SemgrepAnalyzer().analyze(["src/auth.py"])
    assert result == []
