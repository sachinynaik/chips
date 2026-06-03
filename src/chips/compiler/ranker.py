from __future__ import annotations

import math
from datetime import datetime, timezone

from chips.compiler.models import RankedSignal

# The active ranking weight-set, as a single named source. policy_version
# content-hashes this (contextual-bandit design §9.1) and the future bandit tunes
# it, so it lives here as one dict rather than scattered constants.
RANKER_WEIGHTS = {"semantic": 0.5, "recency": 0.3, "churn": 0.2}

_W_SEMANTIC = RANKER_WEIGHTS["semantic"]
_W_RECENCY = RANKER_WEIGHTS["recency"]
_W_CHURN = RANKER_WEIGHTS["churn"]


def _recency_score(last_changed_at: datetime | None, now: datetime) -> float:
    if last_changed_at is None:
        return 0.0
    if last_changed_at.tzinfo is None:
        last_changed_at = last_changed_at.replace(tzinfo=timezone.utc)
    age_days = max((now - last_changed_at).days, 0)
    return math.exp(-age_days / 30.0)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def rank_signals(
    memories: list[dict],
    file_signals: list[dict],
    diffs: list[dict] | None = None,
    now: datetime | None = None,
) -> list[RankedSignal]:
    if now is None:
        now = datetime.now(timezone.utc)

    ranked: list[RankedSignal] = []

    for mem in memories:
        sem = float(
            mem.get("similarity")
            if mem.get("similarity") is not None
            else mem.get("confidence", 0.0)
        )
        learned = float(mem.get("learning_adjustment", 0.0))
        score = min(max(sem + learned, 0.0), 1.0)
        ranked.append(RankedSignal(
            item_id=str(mem["id"]),
            item_type="memory",
            score=score,
            signal_breakdown={"semantic": sem, "learning_adjustment": learned},
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

    for diff in (diffs or []):
        committed_at = _parse_datetime(diff.get("committed_at"))
        recency = _recency_score(committed_at, now)
        cochange_count = len(diff.get("cochange_pairs", []))
        cochange_norm = min(cochange_count / 10.0, 1.0)
        score = min(_W_RECENCY * recency + _W_CHURN * cochange_norm, 1.0)
        ranked.append(RankedSignal(
            item_id=diff["sha"],
            item_type="diff",
            score=score,
            signal_breakdown={"recency": round(recency, 4), "cochange_count": cochange_count},
        ))

    return sorted(ranked, key=lambda s: s.score, reverse=True)
