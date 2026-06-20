from __future__ import annotations


_YIELD_INPUT_FIELDS = (
    "churn_score",
    "cochange_entropy",
    "defect_history_count",
    "defect_density",
)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(value, high))


def _raw_yield_inputs(
    churn_score: float | None,
    cochange_entropy: float | None,
    defect_history_count: int | None,
    defect_density: float | None,
) -> dict[str, object]:
    values = {
        "churn_score": churn_score,
        "cochange_entropy": cochange_entropy,
        "defect_history_count": defect_history_count,
        "defect_density": defect_density,
    }
    present = [field for field, value in values.items() if value is not None]
    missing = [field for field in _YIELD_INPUT_FIELDS if field not in present]
    return {
        "complete": not missing,
        "present": present,
        "missing": missing,
    }


def compute_yield_score(
    *,
    churn_score: float | None,
    cochange_entropy: float | None,
    defect_history_count: int | None,
    defect_density: float | None,
) -> dict[str, object]:
    """Raw deterministic yield score.

    This is deliberately pre-calibration: a 1–10 health score computed from the
    currently-available evolutionary signals only. It is tagged ``mode=raw`` and
    ``calibrated=False`` so later learned weights cannot be confused with this
    bootstrap score.
    """
    normalized_signals = []
    if churn_score is not None:
        normalized_signals.append(_clamp(float(churn_score)))
    if cochange_entropy is not None:
        normalized_signals.append(_clamp(float(cochange_entropy)))
    if defect_history_count is not None:
        normalized_signals.append(_clamp(float(defect_history_count) / 5.0))
    if defect_density is not None:
        normalized_signals.append(_clamp(float(defect_density) / 5.0))

    risk = sum(normalized_signals) / len(normalized_signals) if normalized_signals else 0.0
    score = round(10.0 - (9.0 * risk), 2)
    return {
        "score": _clamp(score, 1.0, 10.0),
        "mode": "raw",
        "calibrated": False,
        "inputs": _raw_yield_inputs(
            churn_score,
            cochange_entropy,
            defect_history_count,
            defect_density,
        ),
    }
