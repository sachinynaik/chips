from __future__ import annotations

from datetime import datetime


# Cold-start intrinsic half-life priors (days) by belief/source kind. These are
# documented priors, NOT fitted coefficients: the Materials layer (Refinery /
# projection) fits real per-context decay rates later. Until then every decay
# block is tagged ``calibrated=False`` so a prior is never mistaken for a fit.
_INTRINSIC_HALF_LIFE_DAYS: dict[str, float] = {
    "git_history": 30.0,   # durable evolutionary truth, perishes slowly
    "projection": 7.0,     # an estimate between real assays, perishes fast
}
_DEFAULT_HALF_LIFE_DAYS = 30.0
# Reference horizon that maps a half-life into an intrinsic perishability in [0,1).
_DECAY_REFERENCE_DAYS = 30.0
# Extrinsic "territory" turbulence signals. churn/co-change entropy are harvested
# today; volatility/crowding are declared gaps until they are harvested.
_TERRITORY_FIELDS = ("churn_score", "cochange_entropy", "volatility", "crowding")


def _decay(
    source_kind: str,
    churn_score: float | None,
    cochange_entropy: float | None,
) -> dict[str, object]:
    half_life_days = _INTRINSIC_HALF_LIFE_DAYS.get(source_kind, _DEFAULT_HALF_LIFE_DAYS)
    # Shorter half-life -> higher intrinsic perishability, in [0, 1).
    intrinsic = _DECAY_REFERENCE_DAYS / (_DECAY_REFERENCE_DAYS + half_life_days)

    territory: dict[str, float | None] = {
        "churn_score": churn_score,
        "cochange_entropy": cochange_entropy,
    }
    present = [field for field in _TERRITORY_FIELDS if territory.get(field) is not None]
    missing = [field for field in _TERRITORY_FIELDS if field not in present]
    extrinsic_values = [
        max(0.0, min(1.0, float(value)))
        for field in _TERRITORY_FIELDS
        if (value := territory.get(field)) is not None
    ]
    extrinsic = sum(extrinsic_values) / len(extrinsic_values) if extrinsic_values else 0.0

    # Decay is intrinsic perishability amplified by territory turbulence. The 0.5/0.5
    # split is a cold-start prior, fitted away from later by the Materials layer.
    score = max(0.0, min(1.0, round((0.5 * intrinsic) + (0.5 * extrinsic), 2)))
    return {
        "score": score,
        "calibrated": False,
        "intrinsic": {
            "half_life_days": half_life_days,
            "perishability": round(intrinsic, 2),
        },
        "extrinsic": {
            "score": round(extrinsic, 2),
            "present": present,
            "missing": missing,
        },
    }


def assay_signal(
    *,
    source_kind: str,
    assayed_at: datetime,
    code_version: str | None,
    observed_changed_at: datetime | None,
    dopants: list[dict] | None = None,
    churn_score: float | None = None,
    cochange_entropy: float | None = None,
) -> dict[str, object]:
    dopant_list = list(dopants or [])
    dopant_weight = sum(float(dopant.get("weight", 0.0)) for dopant in dopant_list)
    deterministic_fraction = max(0.0, min(1.0, 1.0 - dopant_weight))
    purity = {
        "score": round(deterministic_fraction, 2),
        "deterministic_fraction": round(deterministic_fraction, 2),
        "dopants": dopant_list,
    }
    missing = []
    if code_version is None:
        missing.append("code_version")
    freshness = {
        "assayed_at": assayed_at.isoformat(),
        "code_version": code_version,
        "observed_changed_at": observed_changed_at.isoformat() if observed_changed_at else None,
        "complete": not missing,
        "missing": missing,
    }
    return {
        "source_kind": source_kind,
        "purity": purity,
        "decay": _decay(source_kind, churn_score, cochange_entropy),
        "freshness": freshness,
    }
