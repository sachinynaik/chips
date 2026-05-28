from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Defaults: if mean memory confidence >= 0.75 and we have >= 3 memories,
# secondary sources (diffs, file signals) are unlikely to add signal.
_DEFAULT_CONFIDENCE_THRESHOLD = 0.75
_DEFAULT_MIN_ITEMS = 3


@dataclass(frozen=True)
class GovernorDecision:
    """Records what the governor decided and why."""
    triggered: bool
    mean_confidence: float
    item_count: int
    skipped_sources: list[str] = field(default_factory=list)
    reason: str = ""


def evaluate(
    memories: list[dict],
    *,
    confidence_threshold: float = _DEFAULT_CONFIDENCE_THRESHOLD,
    min_items: int = _DEFAULT_MIN_ITEMS,
) -> GovernorDecision:
    """Decide whether to short-circuit secondary retrieval.

    Uses the semantic similarity / confidence scores already present on each
    memory dict (set by retrieve_memories before learning adjustments are applied).
    If mean confidence is high enough and we have sufficient items, there is
    diminishing return from diffs and file-signal sources.
    """
    if not memories:
        return GovernorDecision(
            triggered=False,
            mean_confidence=0.0,
            item_count=0,
            reason="no memories retrieved",
        )

    scores = [
        float(m.get("similarity") if m.get("similarity") is not None else m.get("confidence", 0.0))
        for m in memories
    ]
    mean_conf = sum(scores) / len(scores)
    n = len(memories)

    if n < min_items:
        return GovernorDecision(
            triggered=False,
            mean_confidence=round(mean_conf, 4),
            item_count=n,
            reason=f"too few memories ({n} < {min_items})",
        )

    if mean_conf < confidence_threshold:
        return GovernorDecision(
            triggered=False,
            mean_confidence=round(mean_conf, 4),
            item_count=n,
            reason=f"mean confidence {mean_conf:.3f} below threshold {confidence_threshold}",
        )

    skipped = ["diffs", "file_signals"]
    reason = (
        f"mean confidence {mean_conf:.3f} >= {confidence_threshold} "
        f"with {n} memories — skipping {', '.join(skipped)}"
    )
    logger.info("governor triggered: %s", reason)
    return GovernorDecision(
        triggered=True,
        mean_confidence=round(mean_conf, 4),
        item_count=n,
        skipped_sources=skipped,
        reason=reason,
    )
