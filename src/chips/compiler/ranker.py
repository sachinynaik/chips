from __future__ import annotations

import math
from datetime import datetime, timezone

from chips.compiler.models import RankedSignal

_W_SEMANTIC = 0.5
_W_RECENCY = 0.3
_W_CHURN = 0.2


def _recency_score(last_changed_at: datetime | None, now: datetime) -> float:
    if last_changed_at is None:
        return 0.0
    if last_changed_at.tzinfo is None:
        last_changed_at = last_changed_at.replace(tzinfo=timezone.utc)
    age_days = max((now - last_changed_at).days, 0)
    return math.exp(-age_days / 30.0)


def rank_signals(
    memories: list[dict],
    file_signals: list[dict],
    now: datetime | None = None,
) -> list[RankedSignal]:
    if now is None:
        now = datetime.now(timezone.utc)

    ranked: list[RankedSignal] = []

    for mem in memories:
        sem = float(mem.get("similarity", 0.0))
        ranked.append(RankedSignal(
            item_id=str(mem["id"]),
            item_type="memory",
            score=min(sem, 1.0),
            signal_breakdown={"semantic": sem},
        ))

    for sig in file_signals:
        churn = float(sig.get("churn_score") or 0.0)
        recency = _recency_score(sig.get("last_changed_at"), now)
        raw = _W_CHURN * churn + _W_RECENCY * recency
        score = min(raw / (_W_CHURN + _W_RECENCY), 1.0)
        ranked.append(RankedSignal(
            item_id=sig["file_path"],
            item_type="file",
            score=score,
            signal_breakdown={"churn": churn, "recency": recency},
        ))

    return sorted(ranked, key=lambda s: s.score, reverse=True)
