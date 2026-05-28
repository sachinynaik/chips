"""Phase 0: pure constraint helpers (no DB, no LLM).

Contract: docs/27_05_phase1_evidence_hypotheses_contract.md §H and the four locked
Phase-0 decisions (dedup normalization, restrictive-wins conflicts, render format,
injection order).
"""
from __future__ import annotations

import hashlib
import json
import re

from chips.compiler.models import Constraint

_WS = re.compile(r"\s+")


def normalize_text(s: str) -> str:
    """Strip, collapse internal whitespace to single spaces, casefold."""
    return _WS.sub(" ", s).strip().casefold()


def canonical_target(target: dict | None) -> str:
    """Sorted-key, compact JSON. Absent/None → '{}', never 'null'.

    Assumes primitive nested dict/list values (the constraint target contract).
    """
    return json.dumps(target or {}, sort_keys=True, separators=(",", ":"))


def dedup_hash(
    tenant_id: str | None,
    scope_pattern: str,
    kind: str,
    constraint_text: str,
    target: dict | None,
) -> str:
    """Stable sha256 over the canonical dedup identity.

    tenant None and "" collapse to the same key (single-tenant/dev). Text is
    normalized; target is canonicalized. Backs both the repository idempotency
    check and the DB partial-unique index on active rows.
    """
    key = json.dumps(
        [
            tenant_id or "",
            scope_pattern,
            kind,
            normalize_text(constraint_text),
            canonical_target(target),
        ],
        separators=(",", ":"),
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def render_constraint(c: Constraint) -> str:
    """Imperative, source-linked rendering for injection into hard_constraints."""
    if c.kind == "forbidden":
        return f"MUST NOT: {c.text}"
    if c.kind == "invariant":
        return f"INVARIANT: {c.text}"
    out = f"KNOWN ISSUE — avoid: {c.text}"
    if c.reason:
        out += f" (caused: {c.reason})"
    if c.source_ref:
        out += f" [ref: {c.source_ref}]"
    return out


def _recent_first(items: list[Constraint]) -> list[Constraint]:
    """Deterministic within-group order: created_at desc, tie-break id asc."""
    return sorted(
        items,
        key=lambda c: (-(c.created_at.timestamp() if c.created_at else 0.0), str(c.id)),
    )


def _of_kind(constraints: list[Constraint], kind: str) -> list[Constraint]:
    return _recent_first([c for c in constraints if c.kind == kind])


def effective_allowed_edits(
    allowed: list[str], constraints: list[Constraint]
) -> list[str]:
    """Restrictive wins: drop any allowed edit whose value is the path/symbol
    target of a forbidden/invariant constraint. known_issue does not restrict.
    """
    blocked: set[str] = set()
    for c in constraints:
        if c.kind in ("forbidden", "invariant"):
            for key in ("path", "symbol"):
                value = c.target.get(key)
                if value:
                    blocked.add(value)
    return [a for a in allowed if a not in blocked]


def assemble_hard_constraints(
    learned: list[Constraint],
    policy_forbidden: list[str],
    memory_invariants: list[str],
    hard_additions: list[str],
) -> list[str]:
    """Inject in locked precedence order (most non-negotiable first)."""
    return (
        [render_constraint(c) for c in _of_kind(learned, "forbidden")]
        + list(policy_forbidden)
        + [render_constraint(c) for c in _of_kind(learned, "invariant")]
        + list(memory_invariants)
        + [render_constraint(c) for c in _of_kind(learned, "known_issue")]
        + list(hard_additions)
    )


def assemble_forbidden_edits(
    learned: list[Constraint], policy_forbidden: list[str]
) -> list[str]:
    """forbidden_edits holds only truly prohibitive entries: learned forbidden
    (recent first, raw text) then policy forbidden. No invariant, no known_issue.
    """
    return [c.text for c in _of_kind(learned, "forbidden")] + list(policy_forbidden)
