from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

DEFAULT_WINDOW_DAYS = 14


@dataclass(frozen=True)
class AdverseEvent:
    file_path: str
    occurred_at: datetime
    kind: str  # "revert" | "hotfix"
    ref: str  # sha or id, for evidence


def durability_label(
    edited_files: list[str],
    brief_time: datetime,
    adverse_events: list[AdverseEvent],
    now: datetime,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> dict:
    """Return a deterministic outcome label. Pure — no I/O.

    - bad: an adverse event touched an edited file within [brief_time, brief_time + window).
    - good: else if the window has fully matured (now >= brief_time + window).
    - unknown: no edited files, or the window has not yet matured.
    """
    if not edited_files:
        return {"status": "unknown", "reason": "no_outcome_files"}

    window_end = brief_time + timedelta(days=window_days)

    counted = [
        event
        for event in adverse_events
        if event.file_path in edited_files and brief_time <= event.occurred_at < window_end
    ]

    if counted:
        evidence = sorted(
            counted,
            key=lambda event: (event.occurred_at, event.file_path, event.ref),
        )
        return {
            "status": "bad",
            "reason": "reverted_or_hotfixed_within_window",
            "window_days": window_days,
            "evidence": [
                {
                    "file_path": event.file_path,
                    "kind": event.kind,
                    "ref": event.ref,
                    "occurred_at": event.occurred_at.isoformat(),
                }
                for event in evidence
            ],
        }

    if now >= window_end:
        return {
            "status": "good",
            "reason": "stable_through_window",
            "window_days": window_days,
        }

    return {
        "status": "unknown",
        "reason": "window_not_matured",
        "window_days": window_days,
    }
