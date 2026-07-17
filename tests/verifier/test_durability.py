from __future__ import annotations

from datetime import datetime, timedelta, timezone

from chips.verifier.durability import AdverseEvent, durability_label

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_no_edited_files_is_unknown() -> None:
    result = durability_label(
        edited_files=[],
        brief_time=T0,
        adverse_events=[],
        now=T0 + timedelta(days=100),
    )
    assert result == {"status": "unknown", "reason": "no_outcome_files"}


def test_adverse_event_inside_window_is_bad_with_evidence() -> None:
    event = AdverseEvent(
        file_path="a.py",
        occurred_at=T0 + timedelta(days=1),
        kind="revert",
        ref="sha123",
    )
    result = durability_label(
        edited_files=["a.py"],
        brief_time=T0,
        adverse_events=[event],
        now=T0 + timedelta(days=100),
    )
    assert result == {
        "status": "bad",
        "reason": "reverted_or_hotfixed_within_window",
        "window_days": 14,
        "evidence": [
            {
                "file_path": "a.py",
                "kind": "revert",
                "ref": "sha123",
                "occurred_at": (T0 + timedelta(days=1)).isoformat(),
            }
        ],
    }


def test_adverse_event_exactly_at_window_boundary_not_counted_and_matures_good() -> None:
    boundary = T0 + timedelta(days=14)
    event = AdverseEvent(
        file_path="a.py",
        occurred_at=boundary,
        kind="hotfix",
        ref="sha999",
    )
    result = durability_label(
        edited_files=["a.py"],
        brief_time=T0,
        adverse_events=[event],
        now=boundary + timedelta(seconds=1),
    )
    assert result == {
        "status": "good",
        "reason": "stable_through_window",
        "window_days": 14,
    }


def test_adverse_event_on_non_edited_file_is_ignored() -> None:
    event = AdverseEvent(
        file_path="b.py",
        occurred_at=T0 + timedelta(days=1),
        kind="revert",
        ref="sha123",
    )
    result = durability_label(
        edited_files=["a.py"],
        brief_time=T0,
        adverse_events=[event],
        now=T0 + timedelta(days=100),
    )
    assert result == {
        "status": "good",
        "reason": "stable_through_window",
        "window_days": 14,
    }


def test_adverse_event_before_brief_time_is_ignored() -> None:
    event = AdverseEvent(
        file_path="a.py",
        occurred_at=T0 - timedelta(days=1),
        kind="revert",
        ref="sha123",
    )
    result = durability_label(
        edited_files=["a.py"],
        brief_time=T0,
        adverse_events=[event],
        now=T0 + timedelta(days=100),
    )
    assert result == {
        "status": "good",
        "reason": "stable_through_window",
        "window_days": 14,
    }


def test_no_adverse_events_window_matured_is_good() -> None:
    result = durability_label(
        edited_files=["a.py"],
        brief_time=T0,
        adverse_events=[],
        now=T0 + timedelta(days=14),
    )
    assert result == {
        "status": "good",
        "reason": "stable_through_window",
        "window_days": 14,
    }


def test_no_adverse_events_window_not_matured_is_unknown() -> None:
    result = durability_label(
        edited_files=["a.py"],
        brief_time=T0,
        adverse_events=[],
        now=T0 + timedelta(days=13),
    )
    assert result == {
        "status": "unknown",
        "reason": "window_not_matured",
        "window_days": 14,
    }


def test_bad_precedence_over_not_yet_matured() -> None:
    event = AdverseEvent(
        file_path="a.py",
        occurred_at=T0 + timedelta(days=1),
        kind="revert",
        ref="sha123",
    )
    result = durability_label(
        edited_files=["a.py"],
        brief_time=T0,
        adverse_events=[event],
        now=T0 + timedelta(days=2),
    )
    assert result["status"] == "bad"


def test_multiple_adverse_events_sorted_deterministically() -> None:
    e1 = AdverseEvent(
        file_path="b.py",
        occurred_at=T0 + timedelta(days=2),
        kind="revert",
        ref="sha2",
    )
    e2 = AdverseEvent(
        file_path="a.py",
        occurred_at=T0 + timedelta(days=1),
        kind="hotfix",
        ref="sha1",
    )
    e3 = AdverseEvent(
        file_path="a.py",
        occurred_at=T0 + timedelta(days=1),
        kind="revert",
        ref="sha0",
    )
    result = durability_label(
        edited_files=["a.py", "b.py"],
        brief_time=T0,
        adverse_events=[e1, e2, e3],
        now=T0 + timedelta(days=100),
    )
    assert result["status"] == "bad"
    assert [ev["ref"] for ev in result["evidence"]] == ["sha0", "sha1", "sha2"]


def test_custom_window_days_respected() -> None:
    result = durability_label(
        edited_files=["a.py"],
        brief_time=T0,
        adverse_events=[],
        now=T0 + timedelta(days=6),
        window_days=5,
    )
    assert result == {
        "status": "good",
        "reason": "stable_through_window",
        "window_days": 5,
    }
