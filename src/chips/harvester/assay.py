from __future__ import annotations

from datetime import datetime


def assay_signal(
    *,
    source_kind: str,
    assayed_at: datetime,
    code_version: str | None,
    observed_changed_at: datetime | None,
    dopants: list[dict] | None = None,
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
        "freshness": freshness,
    }
