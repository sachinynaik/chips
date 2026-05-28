"""Phase 0: builder injection of learned constraints into the brief.

Verifies the dynamic policy layer reaches hard_constraints / forbidden_edits via
the locked assemble_* helpers, and that for_scope is called scope+tenant-scoped.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import UUID

from chips.compiler.builder import BriefBuilder
from chips.compiler.models import Constraint


def _builder() -> BriefBuilder:
    return BriefBuilder(
        conn=MagicMock(),
        embedder=MagicMock(embed=MagicMock(return_value=[0.1] * 768)),
        compressor=MagicMock(compress_with_trace=MagicMock(return_value=("compressed", []))),
    )


def _con(kind: str, text: str, **target) -> Constraint:
    return Constraint(
        id=UUID(int=1), tenant_id="t1", scope_pattern="checkout", kind=kind,  # type: ignore[arg-type]
        text=text, target=target, created_at=datetime(2026, 5, 27, tzinfo=timezone.utc),
    )


def _build(constraints, *, repo=None):
    builder = _builder()
    repo = repo or MagicMock()
    repo.for_scope.return_value = constraints
    with (
        patch("chips.compiler.builder.retrieve_memories", return_value=[]),
        patch("chips.compiler.builder.retrieve_diffs", return_value=[]),
        patch("chips.compiler.builder.retrieve_file_signals", return_value=[]),
        patch("chips.compiler.builder.ConstraintRepository", return_value=repo),
        patch.object(BriefBuilder, "_persist"),
    ):
        brief = builder.build("fix crash", scope="checkout", tenant_id="t1")
    return brief, repo


def test_learned_forbidden_injected_into_hard_constraints():
    brief, _ = _build([_con("forbidden", "no pay edits", path="pay.py")])
    assert "MUST NOT: no pay edits" in brief.hard_constraints


def test_learned_forbidden_in_forbidden_edits_raw():
    brief, _ = _build([_con("forbidden", "no pay edits")])
    assert "no pay edits" in brief.forbidden_edits


def test_known_issue_in_hard_constraints_but_not_forbidden_edits():
    brief, _ = _build([_con("known_issue", "double decrement", path="pay.py")])
    assert any("KNOWN ISSUE — avoid: double decrement" in h for h in brief.hard_constraints)
    assert "double decrement" not in brief.forbidden_edits


def test_for_scope_called_scope_and_tenant_scoped():
    _, repo = _build([])
    repo.for_scope.assert_called_once_with("checkout", tenant_id="t1")
