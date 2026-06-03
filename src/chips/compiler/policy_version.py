"""Foundation: ``policy_version`` as a content hash of the active policy.

The contextual-bandit design (`02_06_contextual_bandit_design.md` §9.1) requires
``policy_version`` to be a **content hash of the active weight-set, not free text**
— so replay grouping and (later) off-policy evaluation can filter logged decisions
to one identifiable policy. ``feature_schema_version`` versions the
``context_features``/``action`` shape so OPE never builds ragged matrices.

Kept deliberately tiny and dependency-light: it hashes a canonical JSON view of
the active policy descriptor. When a knob changes (ranker weights, or — once Slice
A4 lands — the experimental-layer flags), the hash changes, which is exactly the
replay-grouping behaviour the design wants.
"""

from __future__ import annotations

import hashlib
import json

from chips.compiler.ranker import RANKER_WEIGHTS

#: Versions the context_features/action payload shape (semver). Bump on any
#: change to the keys those dicts carry so OPE can filter to one schema.
FEATURE_SCHEMA_VERSION = "1.0.0"


def compute_policy_version(descriptor: dict) -> str:
    """Stable ``pv-<12 hex>`` content hash of a policy descriptor.

    Canonical JSON (sorted keys) → SHA-256 → first 12 hex chars. Order- and
    whitespace-independent so logically identical policies hash identically.
    """
    canonical = json.dumps(descriptor, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]
    return f"pv-{digest}"


def active_policy_descriptor() -> dict:
    """The policy CHIPS currently applies, as a hashable descriptor.

    ``layers`` are all-on today (the experimental governor/reranker/structural
    layers are not yet flag-gated — Slice A4). They are listed explicitly so that
    when A4 makes them configurable, the policy hash moves with the real config.
    """
    return {
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "ranker_weights": RANKER_WEIGHTS,
        "layers": {"governor": True, "reranker": True, "structural": True},
    }


def active_policy_version() -> str:
    """Content hash of the active policy descriptor."""
    return compute_policy_version(active_policy_descriptor())
