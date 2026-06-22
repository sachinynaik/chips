"""Slice 2 of compression-contract enforcement (#33): the I3 ban at the EvidenceBundle boundary.

Contract: docs/design_docs/18_06/chips-reversible-compression-note.md §0.
  Negative invariant (I3): no persisted decision/score/etc. may cite COMPRESSED text as its
  source — only a stable evidence identity that dereferences to the lossless artifact.
  Identity rule (I4): pointer tokens / projections are transport, not canonical identities.
  Point-of-use (I2): dereferenceability is checked at resolve time, not citation-creation time.

Option A enforcement (ratified): the guard lives at the EvidenceBundle boundary — where
``evidence_id`` *becomes* the citable identity — so every downstream consumer is protected by
construction, not by per-exit vigilance.

Pure module — no DB, no LLM.
"""
from __future__ import annotations

from uuid import UUID

import pytest

from chips.compiler.evidence import is_evidence_id
from chips.compiler.evidence_bundle import resolve_source_citation
from chips.compiler.evidence_pointer import (
    DanglingPointerError,
    EvidencePointer,
    NonIdentityCitationError,
)
from chips.compiler.models import EvidenceBundle, EvidenceItem


def _bundle(*items: EvidenceItem) -> EvidenceBundle:
    return EvidenceBundle(bundle_id=UUID(int=1), evidence=list(items))


def _finding(evidence_id: str, text: str = "the lossless original") -> EvidenceItem:
    return EvidenceItem(evidence_id=evidence_id, kind="finding", label="lbl", text=text)


def test_citation_of_stable_id_resolves_to_lossless_item() -> None:
    """Happy path: a citation that is a real evidence_id in the bundle resolves to its item."""
    item = _finding("find:abc123")
    assert resolve_source_citation("find:abc123", _bundle(item)) is item


def test_dangling_citation_fails_closed_at_point_of_use() -> None:
    """LOAD-BEARING: a well-formed id absent from the bundle fails closed at the resolve call."""
    other = _bundle(_finding("find:present"))
    with pytest.raises(DanglingPointerError):
        resolve_source_citation("find:absent", other)


def test_point_of_use_present_in_one_bundle_absent_in_another() -> None:
    """LOAD-BEARING: resolution is point-of-use — valid against the bundle it was built from,
    dangling once resolved against a rebuilt/pruned bundle that no longer carries it."""
    built = _bundle(_finding("find:abc123"))
    assert resolve_source_citation("find:abc123", built) is not None

    rebuilt = _bundle(_finding("find:different"))  # abc123 pruned on rebuild
    with pytest.raises(DanglingPointerError):
        resolve_source_citation("find:abc123", rebuilt)


def test_compressed_text_as_citation_is_rejected() -> None:
    """LOAD-BEARING (I3 teeth): smuggled projection prose is not a canonical identity."""
    compressed = "## Context\nthe model summarized this region for economy"
    with pytest.raises(NonIdentityCitationError):
        resolve_source_citation(compressed, _bundle(_finding("find:abc123")))


def test_transport_handle_as_citation_is_rejected() -> None:
    """LOAD-BEARING (I4): the citation must be the identity (id string), not a transport handle."""
    pointer = EvidencePointer(artifact_id="find:abc123")
    with pytest.raises(NonIdentityCitationError):
        resolve_source_citation(pointer, _bundle(_finding("find:abc123")))


def test_is_evidence_id_accepts_stable_ids_rejects_projection() -> None:
    """The identity predicate: accept well-formed evidence ids, reject smuggled projection."""
    assert is_evidence_id("find:abc123")
    assert is_evidence_id("con:550e8400-e29b-41d4-a716-446655440000")
    assert not is_evidence_id("## Context\nsummary text")  # compressed prose (whitespace)
    assert not is_evidence_id("a bare sentence")           # whitespace
    assert not is_evidence_id("unknown:xyz")               # not a known evidence kind
    assert not is_evidence_id("find:")                     # empty natural key
    assert not is_evidence_id("nocolonhere")               # no kind separator
    assert not is_evidence_id(EvidencePointer(artifact_id="find:abc123"))  # transport object
