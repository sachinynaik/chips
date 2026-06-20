from __future__ import annotations

from chips.harvester.yield_score import compute_yield_score


def test_yield_score_is_top_of_scale_for_clean_signal_set():
    result = compute_yield_score(
        churn_score=0.0,
        cochange_entropy=0.0,
        defect_history_count=0,
        defect_density=None,
    )

    assert result["mode"] == "raw"
    assert result["calibrated"] is False
    assert result["score"] == 10.0


def test_yield_score_drops_as_signals_get_worse():
    healthier = compute_yield_score(
        churn_score=0.2,
        cochange_entropy=0.1,
        defect_history_count=0,
        defect_density=0.5,
    )
    riskier = compute_yield_score(
        churn_score=0.9,
        cochange_entropy=0.8,
        defect_history_count=4,
        defect_density=6.0,
    )

    assert riskier["score"] < healthier["score"]


def test_yield_score_reports_missing_signals_but_still_computes():
    result = compute_yield_score(
        churn_score=0.8,
        cochange_entropy=None,
        defect_history_count=2,
        defect_density=None,
    )

    assert result["score"] < 10.0
    assert result["inputs"]["complete"] is False
    assert "cochange_entropy" in result["inputs"]["missing"]
    assert "defect_density" in result["inputs"]["missing"]
