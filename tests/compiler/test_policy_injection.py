from __future__ import annotations

import textwrap
from unittest.mock import MagicMock

from chips.compiler.builder import BriefBuilder
from chips.compiler.policy import PolicyLoader


def _make_embedder() -> MagicMock:
    m = MagicMock()
    m.embed.return_value = [0.1] * 768
    return m


def _make_compressor() -> MagicMock:
    m = MagicMock()
    m.compress.return_value = "compressed"
    m.compress_with_trace.return_value = ("compressed", [])
    return m


def _loader_with(yaml_text: str) -> PolicyLoader:
    return PolicyLoader.from_yaml_string(yaml_text)


def test_forbidden_policy_added_to_hard_constraints(conn):
    yaml_text = textwrap.dedent("""
        version: 1
        policies:
          - scope: auth
            forbidden:
              - "Never bypass token validation"
    """)
    builder = BriefBuilder(
        conn, _make_embedder(), _make_compressor(),
        policy_loader=_loader_with(yaml_text),
    )
    brief = builder.build("fix auth bug", scope="auth")
    assert "Never bypass token validation" in brief.forbidden_edits


def test_required_policy_added_to_brief(conn):
    yaml_text = textwrap.dedent("""
        version: 1
        policies:
          - scope: payments
            required:
              - "Always validate amount > 0"
    """)
    builder = BriefBuilder(
        conn, _make_embedder(), _make_compressor(),
        policy_loader=_loader_with(yaml_text),
    )
    brief = builder.build("update payment flow", scope="payments")
    assert "Always validate amount > 0" in brief.allowed_edits


def test_global_policy_applies_when_no_scope(conn):
    yaml_text = textwrap.dedent("""
        version: 1
        policies:
          - scope: "*"
            forbidden:
              - "Never commit credentials"
    """)
    builder = BriefBuilder(
        conn, _make_embedder(), _make_compressor(),
        policy_loader=_loader_with(yaml_text),
    )
    brief = builder.build("fix bug")
    assert "Never commit credentials" in brief.forbidden_edits


def test_no_policy_loader_gives_empty_edits(conn):
    builder = BriefBuilder(conn, _make_embedder(), _make_compressor())
    brief = builder.build("refactor module")
    assert brief.forbidden_edits == []
    assert brief.allowed_edits == []


def test_forbidden_items_passed_to_compressor_as_hard_constraints(conn):
    yaml_text = textwrap.dedent("""
        version: 1
        policies:
          - scope: auth
            forbidden:
              - "No plaintext passwords"
    """)
    compressor = _make_compressor()
    builder = BriefBuilder(
        conn, _make_embedder(), compressor,
        policy_loader=_loader_with(yaml_text),
    )
    builder.build("fix auth", scope="auth")
    call_args = compressor.compress_with_trace.call_args
    hard = call_args[0][0]
    assert "No plaintext passwords" in hard
