from __future__ import annotations

from unittest.mock import MagicMock

from chips.compiler.retrieval import retrieve_file_signals


def test_retrieve_file_signals_includes_cochange_entropy():
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = [
        ("src/auth.py", 0.8, 0.5, 2, 2, None),
    ]
    conn.execute.return_value = cursor

    result = retrieve_file_signals(conn, ["src/auth.py"])

    assert result == [
        {
            "file_path": "src/auth.py",
            "churn_score": 0.8,
            "cochange_entropy": 0.5,
            "defect_history_count": 2,
            "fragility": 0.69,
            "failure_count": 2,
            "last_changed_at": None,
        }
    ]
