from __future__ import annotations

import logging
from dataclasses import dataclass

from chips.compiler.models import RankedSignal, SoftContextItem
from chips.observability.metrics import observe_rerank

logger = logging.getLogger(__name__)

try:
    from flashrank import Ranker as _Ranker
    from flashrank import RerankRequest as _RerankRequest
    _FLASHRANK_AVAILABLE = True
except ImportError:
    _FLASHRANK_AVAILABLE = False

# Cached at module level — loading once takes ~0.2s; per-call would be ~200ms overhead.
_ranker: object | None = None

_DEFAULT_MODEL = "ms-marco-MiniLM-L-12-v2"
_DEFAULT_CACHE_DIR = ".flashrank_cache"


def _get_ranker(model_name: str, cache_dir: str) -> object | None:
    global _ranker
    if not _FLASHRANK_AVAILABLE:
        return None
    if _ranker is None:
        try:
            _ranker = _Ranker(model_name=model_name, cache_dir=cache_dir)
        except Exception as exc:
            logger.warning("flashrank ranker failed to load: %s", exc)
            return None
    return _ranker


@dataclass(frozen=True)
class RerankerConfig:
    model_name: str = _DEFAULT_MODEL
    cache_dir: str = _DEFAULT_CACHE_DIR
    top_n: int = 15


def rerank(
    query: str,
    signals: list[RankedSignal],
    items: list[SoftContextItem],
    *,
    config: RerankerConfig | None = None,
) -> tuple[list[RankedSignal], list[SoftContextItem]]:
    """Re-score signals and items using a cross-encoder. Returns updated lists sorted by
    the new score. Falls back to original order if flashrank is unavailable or errors.

    The cross-encoder sees (query, item_text) pairs and produces a relevance score that
    accounts for query-item interaction — unlike the bi-encoder cosine similarity used
    for initial retrieval. Scores are merged: 0.7 × reranker_score + 0.3 × original_score.
    """
    if not items:
        observe_rerank(status="skipped")
        return signals, items

    cfg = config or RerankerConfig()
    ranker = _get_ranker(cfg.model_name, cfg.cache_dir)
    if ranker is None:
        observe_rerank(status="unavailable")
        return signals, items

    passages = [{"id": item.item_id, "text": item.text} for item in items]
    try:
        request = _RerankRequest(query=query, passages=passages)
        results = ranker.rerank(request)  # type: ignore[union-attr]
    except Exception as exc:
        logger.warning("flashrank rerank failed, keeping original order: %s", exc)
        observe_rerank(status="error")
        return signals, items

    # Build score lookup: item_id → reranker score (normalised 0-1)
    raw_scores = {r["id"]: float(r["score"]) for r in results}
    if not raw_scores:
        observe_rerank(status="empty")
        return signals, items

    max_score = max(raw_scores.values()) or 1.0
    norm_scores = {k: v / max_score for k, v in raw_scores.items()}

    # Rebuild items with merged scores
    signal_map = {s.item_id: s for s in signals}
    reranked_items: list[SoftContextItem] = []
    updated_signals: list[RankedSignal] = []
    seen_ids: set[str] = set()

    for item in items:
        rerank_score = norm_scores.get(item.item_id, 0.0)
        merged = 0.7 * rerank_score + 0.3 * item.score
        reranked_items.append(SoftContextItem(
            item_id=item.item_id,
            category=item.category,
            text=item.text,
            score=round(merged, 4),
        ))
        seen_ids.add(item.item_id)
        if item.item_id in signal_map:
            sig = signal_map[item.item_id]
            updated_signals.append(RankedSignal(
                item_id=sig.item_id,
                item_type=sig.item_type,
                score=round(merged, 4),
                signal_breakdown={**sig.signal_breakdown, "rerank_score": round(rerank_score, 4)},
            ))

    # Keep any signals not in soft_items (e.g. hard-constraint memories)
    for sig in signals:
        if sig.item_id not in seen_ids:
            updated_signals.append(sig)

    reranked_items.sort(key=lambda i: (-i.score, i.item_id))
    updated_signals.sort(key=lambda s: s.score, reverse=True)
    observe_rerank(status="success")
    return updated_signals, reranked_items
