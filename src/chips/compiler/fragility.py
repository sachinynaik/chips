from __future__ import annotations


_FRAGILITY_INPUT_FIELDS = (
    "churn_score",
    "cochange_entropy",
    "defect_history_count",
)


def fragility_inputs(
    churn_score: float | None,
    cochange_entropy: float | None,
    defect_history_count: int | None,
) -> dict[str, object]:
    values = {
        "churn_score": churn_score,
        "cochange_entropy": cochange_entropy,
        "defect_history_count": defect_history_count,
    }
    present = [field for field, value in values.items() if value is not None]
    missing = [field for field in _FRAGILITY_INPUT_FIELDS if field not in present]
    return {
        "complete": not missing,
        "present": present,
        "missing": missing,
    }


def fragility_score(
    churn_score: float | None,
    cochange_entropy: float | None,
    defect_history_count: int | None,
) -> float:
    churn = float(churn_score or 0.0)
    entropy = float(cochange_entropy or 0.0)
    defect_presence = 1.0 if defect_history_count is not None and defect_history_count > 0 else 0.0
    raw = (0.45 * churn) + (0.35 * entropy) + (0.15 * defect_presence)
    return round(min(raw, 1.0), 2)
