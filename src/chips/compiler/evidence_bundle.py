"""Phase 1 (contract §B / §I.5): project a brief's assembled signals into an EvidenceBundle.

Pure layer — no DB, no LLM. The bundle is a typed, stable-ID *projection* of what
``BriefBuilder.build()`` already assembles:

- ``constraints``: the non-negotiable layer contradiction is scored against (``con:<uuid>``,
  ``constraint_kind`` + ``target`` first-class, authority weight 1.0).
- ``evidence``: the citable soft pool (``mem:`` / ``diff:`` / ``find:`` / ``struct:``).

Kept out of ``builder.py`` deliberately — the orchestrator is already over-centralized
(see docs/31_05_codex_remediation_plan.md); the projection is unit-testable in isolation.
"""
from __future__ import annotations

from uuid import UUID

from chips.compiler.evidence import is_evidence_id, make_evidence_id
from chips.compiler.evidence_pointer import (
    EvidencePointer,
    NonIdentityCitationError,
    dereference,
)
from chips.compiler.models import Constraint, EvidenceBundle, EvidenceItem, SoftContextItem

# SoftContextItem.category → EvidenceItem.kind for the citable kinds in v1.
# 'file'/'generic' are intentionally absent: the §A contract has no 'file'/'generic'
# EvidenceKind. File signals are injected into the brief body (A2a) so they inform
# context, but they are not citable evidence and must not enter the bundle.
_CATEGORY_KIND: dict[str, str] = {
    "memory": "memory",
    "diff": "diff",
    "finding": "finding",
    "structural": "structural",
}
# Categories whose item_id is a *bare* natural key needing a "<prefix>:" added.
_BARE_PREFIX: dict[str, str] = {"memory": "mem", "diff": "diff"}
# Categories whose item_id is ALREADY a full "<prefix>:<key>" evidence id.
_PREFIXED: dict[str, str] = {"finding": "find", "structural": "struct"}

_LABEL_LEN = 72


def _label(text: str) -> str:
    """Compact, stable single-line label for logs / UI / write-back review."""
    stripped = text.strip()
    first_line = stripped.splitlines()[0] if stripped else ""
    return first_line[:_LABEL_LEN]


def _soft_evidence_id(item: SoftContextItem) -> str | None:
    """Stable evidence_id for a soft item, or None if it has no citable identity."""
    cat = item.category
    if cat in _BARE_PREFIX:
        return make_evidence_id(_BARE_PREFIX[cat], item.item_id) if item.item_id else None
    if cat in _PREFIXED:
        if not item.item_id:
            return None
        prefix = _PREFIXED[cat]
        if item.item_id.startswith(f"{prefix}:"):
            return item.item_id
        return make_evidence_id(prefix, item.item_id)
    return None  # pragma: no cover — unreachable: caller filters to _CATEGORY_KIND categories


def _constraint_item(c: Constraint) -> EvidenceItem:
    refs: dict = {}
    if c.source_kind:
        refs["source_kind"] = c.source_kind
    if c.source_ref:
        refs["source_ref"] = c.source_ref
    return EvidenceItem(
        evidence_id=make_evidence_id("con", str(c.id)),
        kind="constraint",
        label=c.source_ref or _label(c.text),
        text=c.text,
        weight=1.0,  # authority weight — constraints are non-negotiable (§B)
        constraint_kind=c.kind,
        target=dict(c.target or {}),
        refs=refs,
    )


def assemble_evidence_bundle(
    brief_id: UUID,
    constraints: list[Constraint],
    soft_items: list[SoftContextItem],
) -> EvidenceBundle:
    """Project assembled constraints + soft items into a typed EvidenceBundle.

    ``bundle_id == brief_id`` (contract §B). Soft items whose category is not a citable
    evidence kind in v1, or that lack a natural key, are skipped — an item with no stable
    identity cannot be cited and must not enter the bundle.
    """
    constraint_items = [_constraint_item(c) for c in constraints]
    evidence_items: list[EvidenceItem] = []
    for item in soft_items:
        kind = _CATEGORY_KIND.get(item.category)
        if kind is None:
            continue
        evidence_id = _soft_evidence_id(item)
        if evidence_id is None:
            continue
        evidence_items.append(
            EvidenceItem(
                evidence_id=evidence_id,
                kind=kind,  # type: ignore[arg-type]
                label=_label(item.text),
                text=item.text,
                weight=item.score,
            )
        )
    return EvidenceBundle(
        bundle_id=brief_id,
        constraints=constraint_items,
        evidence=evidence_items,
    )


def resolve_source_citation(citation: object, bundle: EvidenceBundle) -> EvidenceItem:
    """Resolve a persisted source citation to its lossless EvidenceItem, enforcing the I3 ban.

    This is the Option-A enforcement point: the EvidenceBundle is where ``evidence_id`` *becomes*
    the citable identity, so guarding here protects every downstream consumer (decision log,
    write-back, the future gate) by construction rather than at each exit by vigilance.

    Two fail-closed checks, in order:

    1. **Identity, not transport** (note §0 / I4) — the citation must be a canonical evidence id.
       Compressed projection text or a transport handle (e.g. an :class:`EvidencePointer`) cited
       *as* the identity is rejected with :class:`NonIdentityCitationError`. This is the I3 ban's
       teeth: "is this a legitimate id?", not merely "does it resolve?".
    2. **Dereference at point of use** (note §I1/§I2) — the id is resolved against *this* bundle
       via :meth:`EvidenceBundle.by_id`; an id absent from the bundle at resolve time (rebuilt,
       pruned, a different instance) raises :class:`DanglingPointerError`. The check is here, at
       the moment of resolution, never assumed from citation-creation time.
    """
    if not is_evidence_id(citation):
        raise NonIdentityCitationError(
            f"source citation {citation!r} is not a canonical evidence identity; compressed "
            f"projections and transport handles may not be cited as a source artifact"
        )
    pointer = EvidencePointer(artifact_id=citation)  # type: ignore[arg-type]  # narrowed by is_evidence_id
    item = dereference(pointer, bundle.by_id)
    assert isinstance(item, EvidenceItem)  # bundle.by_id only ever yields EvidenceItem
    return item
