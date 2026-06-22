"""Reversible-compression safety boundary: fail-closed evidence pointers (#33, slice 1).

Contract: docs/design_docs/18_06/chips-reversible-compression-note.md

A compressed projection is lossy and must never be treated as evidence-grade truth.
Where a projection omits or compacts content, it references the omitted material through
an :class:`EvidencePointer` — a *transport handle* whose canonical identity is the stable
original artifact id (e.g. ``find:<content-hash>`` from :mod:`chips.compiler.evidence`).

The load-bearing property is **fail-closed dereference at point of use**:

- **I1** (positive): a projection is valid only if it dereferences to a stable artifact id.
- **I2** (point-of-use): dereferenceability is checked at read time, not compression time. A
  pointer valid when written but dangling when read fails closed at the moment of resolution.
- **I4** (identity): the pointer is transport only; canonical identity is the artifact id.

Pure module — no DB, no LLM (mirrors :mod:`chips.compiler.evidence_bundle`). The resolver
(artifact id -> lossless artifact) is injected so the storage/tooling step stays out of here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

#: Resolves a canonical artifact id to its lossless source artifact, or ``None`` if absent.
#: Modeled as a plain callable (``dict.get`` satisfies it) so callers inject CHIPS storage.
ArtifactResolver = Callable[[str], object | None]


class CompressionContractError(Exception):
    """Base for every reversible-compression-contract violation.

    Both subtypes mean the same operational thing — *fail closed* — so a consumer that only
    cares "did the I3 boundary reject this?" can catch this base; callers that need to
    distinguish a dangling resolve from a smuggled non-identity catch the specific subtype.
    """


class DanglingPointerError(CompressionContractError):
    """A pointer could not be dereferenced to its source artifact at point of use.

    Raised — never swallowed — so an unresolvable projection fails closed: it must not
    enter any gate, assay, audit, or evaluation path (note §0 / §3.1, no warning-only mode).
    """


class NonIdentityCitationError(CompressionContractError):
    """A source citation was not a canonical evidence identity (note §0 identity rule / I4).

    Raised when something tries to cite compressed projection text — or a transport handle —
    *as if it were* the citable identity. The I3 ban's teeth: a citation must be a stable
    evidence id, not smuggled projection material that merely happens to be present.
    """


@dataclass(frozen=True)
class EvidencePointer:
    """A transport handle to a compressed projection's lossless source artifact.

    ``artifact_id`` is the canonical identity (a stable evidence id). The pointer object/token
    is *not* the identity — any pointer that targets the same artifact shares its ``canonical_id``.
    """

    artifact_id: str

    def __post_init__(self) -> None:
        if not self.artifact_id:
            raise ValueError("EvidencePointer requires a non-empty artifact_id")

    @property
    def canonical_id(self) -> str:
        """The canonical evidence identity this pointer resolves to (note §0 identity rule)."""
        return self.artifact_id


def dereference(pointer: EvidencePointer, resolver: ArtifactResolver) -> object:
    """Resolve ``pointer`` to its lossless source artifact, failing closed if absent.

    Resolution happens here, at point of use — so a pointer that was valid when written but
    whose artifact is gone when read raises :class:`DanglingPointerError` rather than returning
    ``None`` or any lossy stand-in.
    """
    artifact = resolver(pointer.canonical_id)
    if artifact is None:
        raise DanglingPointerError(
            f"evidence pointer {pointer.canonical_id!r} does not resolve to a source "
            f"artifact at point of use; failing closed"
        )
    return artifact
