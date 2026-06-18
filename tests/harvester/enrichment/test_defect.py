from __future__ import annotations

from unittest.mock import MagicMock

from chips.harvester.enrichment.defect import DefectPredictor


def test_predict_returns_insufficient_history_without_conn():
    result = DefectPredictor().predict("diff", "message")

    assert result["risk_score"] is None
    assert result["history_count"] == 0
    assert result["matched_commits"] == []
    assert result["reason"] == "insufficient_history"


def test_predict_returns_zero_history_when_no_matching_defect_rows():
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    conn.execute.return_value = cursor

    result = DefectPredictor().predict(
        "diff",
        "message",
        conn=conn,
        files_changed=["src/auth.py"],
    )

    assert result["risk_score"] is None
    assert result["history_count"] == 0
    assert result["matched_commits"] == []
    assert result["reason"] == "no_prior_defects"


def test_predict_returns_history_count_and_recent_matching_shas():
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = [("abc123",), ("def456",)]
    conn.execute.return_value = cursor

    result = DefectPredictor().predict(
        "diff",
        "message",
        conn=conn,
        files_changed=["src/auth.py"],
    )

    assert result["risk_score"] is None
    assert result["history_count"] == 2
    assert result["matched_commits"] == ["abc123", "def456"]
    assert result["reason"] == "history_found"
