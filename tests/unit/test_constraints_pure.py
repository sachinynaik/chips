"""Phase 0: pure constraint helpers — normalization, dedup hash, render, precedence.

Locks the four pre-coding decisions (no DB here):
  - dedup normalization (strip/collapse/casefold) + canonical_target rules
  - conflict rule: restrictive wins (forbidden/invariant strip allowed edits)
  - render format per kind
  - injection order: learned-forbidden, policy-forbidden, learned-invariant,
    invariant/contract memories, learned-known_issue, finding hard-additions
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from chips.compiler.constraints import (
    assemble_forbidden_edits,
    assemble_hard_constraints,
    canonical_target,
    dedup_hash,
    effective_allowed_edits,
    normalize_text,
    render_constraint,
)
from chips.compiler.models import Constraint


def _c(kind: str, text: str, *, cid: str, when: int = 0, reason=None, ref=None, **target) -> Constraint:
    return Constraint(
        id=UUID(int=int(cid)),
        tenant_id="t1",
        scope_pattern="checkout",
        kind=kind,  # type: ignore[arg-type]
        text=text,
        reason=reason,
        source_ref=ref,
        target=target,
        created_at=datetime(2026, 5, 27, 0, 0, when, tzinfo=timezone.utc),
    )


# ── normalize_text ───────────────────────────────────────────────────────────

def test_normalize_text_strips_collapses_and_casefolds():
    assert normalize_text("  Do  Not\tdo  X ") == "do not do x"


def test_normalize_text_equates_trivially_different_strings():
    assert normalize_text("DO NOT X") == normalize_text("  do   not   x  ")


# ── canonical_target ─────────────────────────────────────────────────────────

def test_canonical_target_sorts_keys_compactly():
    assert canonical_target({"b": 1, "a": 2}) == '{"a":2,"b":1}'


def test_canonical_target_is_order_independent_including_nested():
    a = canonical_target({"path": "p", "meta": {"y": 2, "x": 1}})
    b = canonical_target({"meta": {"x": 1, "y": 2}, "path": "p"})
    assert a == b


def test_canonical_target_absent_is_empty_object_not_null():
    assert canonical_target(None) == "{}"
    assert canonical_target({}) == "{}"


# ── dedup_hash ───────────────────────────────────────────────────────────────

def test_dedup_hash_is_deterministic_and_text_normalized():
    h1 = dedup_hash("t1", "checkout", "forbidden", "Do  Not X", {"path": "a"})
    h2 = dedup_hash("t1", "checkout", "forbidden", "do not x", {"path": "a"})
    assert h1 == h2


def test_dedup_hash_treats_none_tenant_as_empty_key():
    assert dedup_hash(None, "checkout", "forbidden", "x", {}) == dedup_hash("", "checkout", "forbidden", "x", {})


def test_dedup_hash_distinguishes_kind_scope_and_target():
    base = dedup_hash("t1", "checkout", "forbidden", "x", {"path": "a"})
    assert base != dedup_hash("t1", "checkout", "invariant", "x", {"path": "a"})
    assert base != dedup_hash("t1", "cart", "forbidden", "x", {"path": "a"})
    assert base != dedup_hash("t1", "checkout", "forbidden", "x", {"path": "b"})


# ── render_constraint ────────────────────────────────────────────────────────

def test_render_forbidden_and_invariant():
    assert render_constraint(_c("forbidden", "edit pay.py", cid="1")) == "MUST NOT: edit pay.py"
    assert render_constraint(_c("invariant", "payment precedes inventory", cid="2")) == "INVARIANT: payment precedes inventory"


def test_render_known_issue_includes_reason_and_ref():
    out = render_constraint(_c("known_issue", "double decrement", cid="3", reason="race", ref="otlp-9921"))
    assert out == "KNOWN ISSUE — avoid: double decrement (caused: race) [ref: otlp-9921]"


def test_render_known_issue_without_reason_or_ref():
    assert render_constraint(_c("known_issue", "thing", cid="4")) == "KNOWN ISSUE — avoid: thing"


# ── effective_allowed_edits (restrictive wins) ───────────────────────────────

def test_forbidden_target_strips_allowed_edit():
    learned = [_c("forbidden", "no pay edits", cid="1", path="pay.py")]
    assert effective_allowed_edits(["pay.py", "cart.py"], learned) == ["cart.py"]


def test_invariant_target_symbol_strips_allowed_edit():
    learned = [_c("invariant", "keep", cid="1", symbol="Cart.add")]
    assert effective_allowed_edits(["Cart.add", "Cart.remove"], learned) == ["Cart.remove"]


def test_known_issue_does_not_strip_allowed_edits():
    learned = [_c("known_issue", "careful", cid="1", path="pay.py")]
    assert effective_allowed_edits(["pay.py"], learned) == ["pay.py"]


# ── assemble_hard_constraints (exact injection order) ────────────────────────

def test_hard_constraints_injection_order():
    learned = [
        _c("known_issue", "ki", cid="1"),
        _c("invariant", "inv", cid="2"),
        _c("forbidden", "fb", cid="3"),
    ]
    out = assemble_hard_constraints(
        learned,
        policy_forbidden=["policy-fb"],
        memory_invariants=["mem-inv"],
        hard_additions=["finding-x"],
    )
    assert out == [
        "MUST NOT: fb",        # 1. learned forbidden
        "policy-fb",           # 2. policy forbidden
        "INVARIANT: inv",      # 3. learned invariant
        "mem-inv",             # 4. invariant/contract memories
        "KNOWN ISSUE — avoid: ki",  # 5. learned known_issue
        "finding-x",           # 6. finding hard additions
    ]


def test_within_group_ordering_is_recent_first_then_id():
    learned = [
        _c("forbidden", "older", cid="2", when=1),
        _c("forbidden", "newer", cid="1", when=5),
    ]
    out = assemble_hard_constraints(learned, [], [], [])
    assert out == ["MUST NOT: newer", "MUST NOT: older"]


# ── assemble_forbidden_edits (no known_issue / no invariant) ─────────────────

def test_forbidden_edits_only_prohibitive():
    learned = [
        _c("forbidden", "fb-text", cid="1"),
        _c("invariant", "inv-text", cid="2"),
        _c("known_issue", "ki-text", cid="3"),
    ]
    out = assemble_forbidden_edits(learned, policy_forbidden=["policy-fb"])
    assert out == ["fb-text", "policy-fb"]
