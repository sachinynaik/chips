from __future__ import annotations
from unittest.mock import patch, MagicMock
from chips.harvester.enrichment.complexity import LizardAnalyzer

def test_analyze_returns_empty_when_lizard_not_installed():
    with patch.dict("sys.modules", {"lizard": None}):
        result = LizardAnalyzer().analyze(["src/auth/token.py"])
    assert result == []

def test_analyze_returns_function_metrics():
    mock_func = MagicMock()
    mock_func.name = "create_auth_token"
    mock_func.cyclomatic_complexity = 5
    mock_func.nloc = 20
    mock_analysis = MagicMock()
    mock_analysis.function_list = [mock_func]
    mock_lizard = MagicMock()
    mock_lizard.analyze_file.return_value = mock_analysis
    with patch.dict("sys.modules", {"lizard": mock_lizard}):
        result = LizardAnalyzer().analyze(["src/auth/token.py"])
    assert len(result) == 1
    assert result[0]["function"] == "create_auth_token"
    assert result[0]["cyclomatic_complexity"] == 5

def test_analyze_returns_empty_list_for_no_files():
    result = LizardAnalyzer().analyze([])
    assert result == []

def test_analyze_skips_file_on_exception():
    mock_lizard = MagicMock()
    mock_lizard.analyze_file.side_effect = Exception("parse error")
    with patch.dict("sys.modules", {"lizard": mock_lizard}):
        result = LizardAnalyzer().analyze(["bad.py"])
    assert result == []


def test_last_status_defaults_to_skipped():
    assert LizardAnalyzer().last_status == "skipped"


def test_last_status_ok_on_success():
    mock_func = MagicMock()
    mock_func.name = "create_auth_token"
    mock_func.cyclomatic_complexity = 5
    mock_func.nloc = 20
    mock_analysis = MagicMock()
    mock_analysis.function_list = [mock_func]
    mock_lizard = MagicMock()
    mock_lizard.analyze_file.return_value = mock_analysis
    analyzer = LizardAnalyzer()
    with patch.dict("sys.modules", {"lizard": mock_lizard}):
        analyzer.analyze(["src/auth/token.py"])
    assert analyzer.last_status == "ok"


def test_last_status_not_installed_when_lizard_missing():
    analyzer = LizardAnalyzer()
    with patch.dict("sys.modules", {"lizard": None}):
        analyzer.analyze(["src/auth/token.py"])
    assert analyzer.last_status == "not_installed"


def test_last_status_failed_on_file_error():
    mock_lizard = MagicMock()
    mock_lizard.analyze_file.side_effect = Exception("parse error")
    analyzer = LizardAnalyzer()
    with patch.dict("sys.modules", {"lizard": mock_lizard}):
        analyzer.analyze(["bad.py"])
    assert analyzer.last_status == "failed"
