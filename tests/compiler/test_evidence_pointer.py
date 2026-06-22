"""Slice 1 of compression-contract enforcement (#33).

Tests the reversible-compression note's load-bearing safety property: a compressed
projection is referenced only through a transport pointer that **fails closed** when
it cannot be dereferenced to its source artifact at point of use.

Contract: docs/design_docs/18_06/chips-reversible-compression-note.md
  - §0 positive invariant (I1): every projection is dereferenceable to a stable artifact id.
  - §0 / §3.1 (I2): dereferenceability is checked at point of use; a pointer valid when
    written but dangling when read fails closed at the moment of resolution.
  - §0 identity rule / §2.4 (I4): the pointer is a transport handle; canonical identity is
    the original artifact id, never the pointer itself.

Pure module — no DB, no LLM (mirrors evidence_bundle.py).
"""
from __future__ import annotations

import pytest

from chips.compiler.evidence_pointer import (
    DanglingPointerError,
    EvidencePointer,
    dereference,
)


def test_dereference_resolves_pointer_to_source_artifact() -> None:
    """I1: a live pointer resolves to its lossless source artifact."""
    artifact = {"id": "find:abc123", "text": "the lossless original"}
    resolver = {"find:abc123": artifact}.get
    pointer = EvidencePointer(artifact_id="find:abc123")

    assert dereference(pointer, resolver) is artifact


def test_dangling_pointer_fails_closed() -> None:
    """I1/I2: an unresolvable pointer raises — it never returns None or compressed text."""
    resolver = {}.get  # source artifact absent
    pointer = EvidencePointer(artifact_id="find:missing")

    with pytest.raises(DanglingPointerError):
        dereference(pointer, resolver)


def test_canonical_identity_is_artifact_id_not_pointer() -> None:
    """I4: canonical identity is the artifact id, shared by any pointer that targets it."""
    p1 = EvidencePointer(artifact_id="find:abc123")
    p2 = EvidencePointer(artifact_id="find:abc123")

    assert p1.canonical_id == "find:abc123"
    assert p1.canonical_id == p2.canonical_id


def test_point_of_use_valid_when_written_then_dangling_when_read() -> None:
    """I2: resolution happens at deref time, not construction time.

    A pointer that dereferenced cleanly when written fails closed once its source
    artifact is gone at the next read — proving the check is point-of-use.
    """
    store: dict[str, dict] = {"find:abc123": {"text": "original"}}
    resolver = store.get
    pointer = EvidencePointer(artifact_id="find:abc123")

    assert dereference(pointer, resolver) == {"text": "original"}

    del store["find:abc123"]  # artifact evicted between write and the next read
    with pytest.raises(DanglingPointerError):
        dereference(pointer, resolver)


def test_pointer_requires_nonempty_artifact_id() -> None:
    """A pointer with no canonical identity is malformed and cannot be constructed."""
    with pytest.raises(ValueError):
        EvidencePointer(artifact_id="")
