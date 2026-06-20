from __future__ import annotations

from unittest.mock import MagicMock
from unittest.mock import patch

from chips.compiler.retrieval import retrieve_file_signals


def test_retrieve_file_signals_includes_cochange_entropy():
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = [
        ("src/auth.py", 0.8, 0.5, None, 2, 2, None),
    ]
    conn.execute.return_value = cursor

    mocked_yield = {
        "score": 3.5,
        "mode": "raw",
        "calibrated": False,
        "inputs": {
            "complete": True,
            "present": ["churn_score", "cochange_entropy", "defect_history_count", "defect_density"],
            "missing": [],
        },
    }
    mocked_assay = {
        "purity": {"score": 1.0, "deterministic_fraction": 1.0, "dopants": []},
        "freshness": {
            "assayed_at": "2026-06-20T00:00:00+00:00",
            "code_version": None,
            "observed_changed_at": None,
            "complete": False,
            "missing": ["code_version"],
        },
        "source_kind": "git_history",
    }
    with patch("chips.compiler.retrieval.estimate_defect_density", return_value=(1.5, 1333)):
        with patch("chips.compiler.retrieval.compute_yield_score", return_value=mocked_yield):
            with patch("chips.compiler.retrieval.assay_signal", return_value=mocked_assay):
                result = retrieve_file_signals(conn, ["src/auth.py"])

    assert result == [
        {
            "file_path": "src/auth.py",
            "churn_score": 0.8,
            "cochange_entropy": 0.5,
            "generated_kind": None,
            "defect_history_count": 2,
            "defect_density": 1.5,
            "defect_density_basis_nloc": 1333,
            "yield_score": mocked_yield,
            "assay": mocked_assay,
            "fragility": 0.69,
            "fragility_inputs": {
                "complete": True,
                "present": ["churn_score", "cochange_entropy", "defect_history_count"],
                "missing": [],
            },
            "failure_count": 2,
            "last_changed_at": None,
        }
    ]
