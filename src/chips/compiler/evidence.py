"""Phase 1: stable evidence ID scheme.

Contract: docs/27_05_phase1_evidence_hypotheses_contract.md §A.

Every evidence ID is ``<kind>:<natural-key>`` where the natural key derives from
the evidence's identity/content — never from position or compile-time ordering.
The same evidence yields the same ID across every compile and into write-back.

This module is pure (no DB, no LLM). The builder wires these in a later slice;
notably the finding ID replaces the positional ``finding:{index}``.
"""
from __future__ import annotations

import hashlib
import json

_FINDING_HASH_LEN = 12


def make_evidence_id(kind: str, natural_key: str) -> str:
    """Compose a stable evidence ID from a kind and a natural key.

    This is the unvalidated primitive guarded only against empty parts; each kind
    owns its natural-key normalization in a dedicated builder (e.g.
    :func:`finding_evidence_id`; reserved ``rule``/``span`` builders arrive in
    Phase 2). Raises ValueError rather than emit a malformed ``:`` / ``kind:`` ID.
    """
    if not kind or not natural_key:
        raise ValueError(
            f"malformed evidence id: kind={kind!r}, natural_key={natural_key!r}"
        )
    return f"{kind}:{natural_key}"


def finding_content_hash(finding: dict) -> str:
    """Order-independent, deterministic content hash of a finding.

    Canonical JSON (sorted keys, including nested) so logically identical findings
    hash equally regardless of key insertion order. Truncated to a short hex digest.

    Stability contract (IDs are reused long-term, so this must hold across runs):
    findings are expected to be JSON-primitive dicts (str/int/float/bool/None,
    lists, nested dicts). ``default=str`` is a safety net for stray non-primitives,
    but it is NOT a stability guarantee for arbitrary objects whose ``str()`` is
    non-deterministic (e.g. default ``repr`` with a memory address). Harvester
    findings satisfy the primitive contract; do not feed live objects here.
    """
    canonical = json.dumps(finding, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return digest[:_FINDING_HASH_LEN]


def finding_evidence_id(finding: dict) -> str:
    """Stable ``find:<content-hash>`` ID for a harvester finding.

    Note the ID prefix is ``find`` while the EvidenceItem.kind is ``finding`` —
    a deliberate distinction fixed by the §A contract.
    """
    return make_evidence_id("find", finding_content_hash(finding))
