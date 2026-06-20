from __future__ import annotations

from unittest.mock import MagicMock
from unittest.mock import patch

from chips.harvester.enrichment.defect import DefectPredictor


def test_predict_returns_insufficient_history_without_conn():
    result = DefectPredictor().predict("diff", "message")

    assert result["risk_score"] is None
    assert result["history_count"] == 0
    assert result["matched_commits"] == []
    assert result["reason"] == "insufficient_history"


def test_predict_returns_zero_history_when_no_matching_defect_rows():
    conn = MagicMock()
    count_cursor = MagicMock()
    count_cursor.fetchone.return_value = (0,)
    recent_cursor = MagicMock()
    recent_cursor.fetchall.return_value = []
    conn.execute.side_effect = [count_cursor, recent_cursor]

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
    assert result["defect_density"] is None
    assert result["density_basis_nloc"] == 0


def test_predict_returns_history_count_and_recent_matching_shas():
    conn = MagicMock()
    count_cursor = MagicMock()
    count_cursor.fetchone.return_value = (4,)
    recent_cursor = MagicMock()
    recent_cursor.fetchall.return_value = [("abc123",), ("def456",)]
    conn.execute.side_effect = [count_cursor, recent_cursor]

    with patch("chips.harvester.enrichment.defect.estimate_defect_density", return_value=(1.25, 800)):
        result = DefectPredictor().predict(
            "diff",
            "message",
            conn=conn,
            files_changed=["src/auth.py"],
        )

    assert result["risk_score"] is None
    assert result["history_count"] == 4
    assert result["matched_commits"] == ["abc123", "def456"]
    assert result["reason"] == "history_found"
    assert result["defect_density"] == 1.25
    assert result["density_basis_nloc"] == 800


def test_predict_sql_uses_high_precision_rule_not_any_issue_ref():
    conn = MagicMock()
    count_cursor = MagicMock()
    count_cursor.fetchone.return_value = (0,)
    recent_cursor = MagicMock()
    recent_cursor.fetchall.return_value = []
    conn.execute.side_effect = [count_cursor, recent_cursor]

    DefectPredictor().predict(
        "diff",
        "message",
        conn=conn,
        files_changed=["src/auth.py"],
    )

    count_sql = conn.execute.call_args_list[0].args[0]
    assert "has_bug_keyword = TRUE" in count_sql
    assert "has_defect_keyword = TRUE" in count_sql
