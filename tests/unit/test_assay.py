from __future__ import annotations

from datetime import datetime, timezone

from chips.harvester.assay import assay_signal


def test_assay_signal_marks_deterministic_source_as_pure():
    assayed_at = datetime(2026, 6, 20, tzinfo=timezone.utc)

    result = assay_signal(
        source_kind="git_history",
        assayed_at=assayed_at,
        code_version="abc123",
        observed_changed_at=None,
        dopants=[],
    )

    assert result["purity"]["score"] == 1.0
    assert result["purity"]["deterministic_fraction"] == 1.0
    assert result["purity"]["dopants"] == []
    assert result["freshness"]["complete"] is True


def test_assay_signal_flags_missing_code_version_as_gap():
    assayed_at = datetime(2026, 6, 20, tzinfo=timezone.utc)

    result = assay_signal(
        source_kind="git_history",
        assayed_at=assayed_at,
        code_version=None,
        observed_changed_at=None,
        dopants=[],
    )

    assert result["freshness"]["complete"] is False
    assert result["freshness"]["code_version"] is None
    assert "code_version" in result["freshness"]["missing"]


def test_assay_signal_degrades_purity_when_dopants_exist():
    assayed_at = datetime(2026, 6, 20, tzinfo=timezone.utc)

    result = assay_signal(
        source_kind="projection",
        assayed_at=assayed_at,
        code_version="abc123",
        observed_changed_at=None,
        dopants=[{"element": "llm_inference", "weight": 0.25}],
    )

    assert result["purity"]["score"] == 0.75
    assert result["purity"]["deterministic_fraction"] == 0.75
    assert result["purity"]["dopants"] == [{"element": "llm_inference", "weight": 0.25}]
