from __future__ import annotations

from chips.compiler.policy_version import (
    FEATURE_SCHEMA_VERSION,
    active_policy_descriptor,
    active_policy_version,
    compute_policy_version,
)
from chips.compiler.ranker import RANKER_WEIGHTS


def test_compute_policy_version_is_order_independent():
    # Same content, different key insertion order → identical hash (canonical JSON).
    a = compute_policy_version({"x": 1, "y": {"a": 2, "b": 3}})
    b = compute_policy_version({"y": {"b": 3, "a": 2}, "x": 1})
    assert a == b


def test_compute_policy_version_changes_with_content():
    base = compute_policy_version({"w": 0.5})
    changed = compute_policy_version({"w": 0.6})
    assert base != changed


def test_policy_version_is_a_content_hash_not_free_text():
    pv = compute_policy_version({"w": 0.5})
    assert pv.startswith("pv-")
    digest = pv.removeprefix("pv-")
    assert len(digest) == 12
    assert all(c in "0123456789abcdef" for c in digest)


def test_active_descriptor_carries_ranker_weights_and_schema_version():
    desc = active_policy_descriptor()
    assert desc["ranker_weights"] == RANKER_WEIGHTS
    assert desc["feature_schema_version"] == FEATURE_SCHEMA_VERSION


def test_active_policy_version_is_stable_and_tracks_weights():
    assert active_policy_version() == active_policy_version()
    # Hashing the active descriptor must equal the convenience accessor.
    assert active_policy_version() == compute_policy_version(active_policy_descriptor())
