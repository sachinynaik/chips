from __future__ import annotations
from chips.harvester.enrichment.refactoring import RefactoringDetector
from chips.harvester.enrichment.joern import JoernAnalyzer
from chips.harvester.enrichment.defect import DefectPredictor

def test_refactoring_detector_returns_none():
    result = RefactoringDetector().detect("some diff content")
    assert result is None

def test_joern_analyzer_returns_empty_list():
    result = JoernAnalyzer().analyze(["src/auth.py"])
    assert result == []

def test_defect_predictor_returns_stub_with_null_risk():
    result = DefectPredictor().predict("some diff", "fix bug")
    assert result["risk_score"] is None

def test_defect_predictor_returns_reason():
    result = DefectPredictor().predict("some diff", "fix bug")
    assert "insufficient_history" in result["reason"]
