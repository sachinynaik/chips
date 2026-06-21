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


def test_assay_signal_emits_independent_decay_score():
    # Materials-layer spec: every node carries three orthogonal scores
    # (purity, decay, freshness), never collapsed. Decay = perishability:
    # intrinsic half-life by belief-kind x extrinsic territory turbulence.
    assayed_at = datetime(2026, 6, 20, tzinfo=timezone.utc)

    result = assay_signal(
        source_kind="git_history",
        assayed_at=assayed_at,
        code_version="abc123",
        observed_changed_at=None,
        churn_score=0.2,
        cochange_entropy=0.3,
    )

    decay = result["decay"]
    assert 0.0 <= decay["score"] <= 1.0
    assert decay["intrinsic"]["half_life_days"] > 0
    assert decay["extrinsic"]["present"] == ["churn_score", "cochange_entropy"]
    # Territory signals not yet harvested are reported as gaps, not silently zeroed.
    assert "volatility" in decay["extrinsic"]["missing"]
    assert "crowding" in decay["extrinsic"]["missing"]
    # Coefficients are cold-start priors until the Materials layer fits them.
    assert decay["calibrated"] is False


def test_assay_decay_rises_with_territory_turbulence():
    assayed_at = datetime(2026, 6, 20, tzinfo=timezone.utc)

    calm = assay_signal(
        source_kind="git_history",
        assayed_at=assayed_at,
        code_version="abc123",
        observed_changed_at=None,
        churn_score=0.0,
        cochange_entropy=0.0,
    )
    turbulent = assay_signal(
        source_kind="git_history",
        assayed_at=assayed_at,
        code_version="abc123",
        observed_changed_at=None,
        churn_score=0.9,
        cochange_entropy=0.9,
    )

    assert turbulent["decay"]["score"] > calm["decay"]["score"]


def test_assay_decay_is_independent_of_purity():
    # A perfectly pure belief can still be highly perishable: the three scores
    # must not collapse into one another.
    assayed_at = datetime(2026, 6, 20, tzinfo=timezone.utc)

    result = assay_signal(
        source_kind="git_history",
        assayed_at=assayed_at,
        code_version="abc123",
        observed_changed_at=None,
        dopants=[],
        churn_score=0.8,
        cochange_entropy=0.8,
    )

    assert result["purity"]["score"] == 1.0
    assert result["decay"]["score"] > 0.0


def test_assay_decay_intrinsic_half_life_varies_by_belief_kind():
    # A projection perishes faster (shorter half-life) than durable git history.
    assayed_at = datetime(2026, 6, 20, tzinfo=timezone.utc)

    history = assay_signal(
        source_kind="git_history",
        assayed_at=assayed_at,
        code_version="abc123",
        observed_changed_at=None,
    )
    projection = assay_signal(
        source_kind="projection",
        assayed_at=assayed_at,
        code_version="abc123",
        observed_changed_at=None,
    )

    assert (
        projection["decay"]["intrinsic"]["half_life_days"]
        < history["decay"]["intrinsic"]["half_life_days"]
    )
