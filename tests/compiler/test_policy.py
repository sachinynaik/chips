from __future__ import annotations

import textwrap

import pytest

from chips.compiler.policy import Policy, PolicyLoader


# ---------------------------------------------------------------------------
# PolicyLoader.from_yaml_string
# ---------------------------------------------------------------------------

def test_load_single_scope_policy():
    yaml_text = textwrap.dedent("""
        version: 1
        policies:
          - scope: auth
            forbidden:
              - "Never expose raw password hashes"
            required:
              - "Always use bcrypt"
    """)
    loader = PolicyLoader.from_yaml_string(yaml_text)
    policies = loader.for_scope("auth")
    assert len(policies) == 1
    assert policies[0].scope == "auth"


def test_forbidden_items_populated():
    yaml_text = textwrap.dedent("""
        version: 1
        policies:
          - scope: auth
            forbidden:
              - "Never bypass token validation"
              - "Do not store plaintext passwords"
    """)
    loader = PolicyLoader.from_yaml_string(yaml_text)
    policy = loader.for_scope("auth")[0]
    assert "Never bypass token validation" in policy.forbidden
    assert "Do not store plaintext passwords" in policy.forbidden


def test_required_items_populated():
    yaml_text = textwrap.dedent("""
        version: 1
        policies:
          - scope: payments
            required:
              - "Always validate amount > 0"
    """)
    loader = PolicyLoader.from_yaml_string(yaml_text)
    policy = loader.for_scope("payments")[0]
    assert "Always validate amount > 0" in policy.required


def test_global_scope_applies_to_all():
    yaml_text = textwrap.dedent("""
        version: 1
        policies:
          - scope: "*"
            forbidden:
              - "Never commit credentials"
          - scope: auth
            forbidden:
              - "Never expose tokens"
    """)
    loader = PolicyLoader.from_yaml_string(yaml_text)
    auth_policies = loader.for_scope("auth")
    assert len(auth_policies) == 2
    scopes = {p.scope for p in auth_policies}
    assert "*" in scopes
    assert "auth" in scopes


def test_no_match_returns_only_global():
    yaml_text = textwrap.dedent("""
        version: 1
        policies:
          - scope: "*"
            forbidden:
              - "Never commit secrets"
          - scope: payments
            forbidden:
              - "Always validate currency"
    """)
    loader = PolicyLoader.from_yaml_string(yaml_text)
    policies = loader.for_scope("auth")
    assert len(policies) == 1
    assert policies[0].scope == "*"


def test_no_scope_returns_only_global():
    yaml_text = textwrap.dedent("""
        version: 1
        policies:
          - scope: "*"
            forbidden:
              - "Never commit secrets"
    """)
    loader = PolicyLoader.from_yaml_string(yaml_text)
    policies = loader.for_scope(None)
    assert len(policies) == 1


def test_empty_yaml_returns_no_policies():
    loader = PolicyLoader.from_yaml_string("version: 1\npolicies: []")
    assert loader.for_scope("auth") == []


def test_missing_forbidden_defaults_to_empty():
    yaml_text = textwrap.dedent("""
        version: 1
        policies:
          - scope: auth
            required:
              - "Use HTTPS"
    """)
    loader = PolicyLoader.from_yaml_string(yaml_text)
    policy = loader.for_scope("auth")[0]
    assert policy.forbidden == []


def test_missing_required_defaults_to_empty():
    yaml_text = textwrap.dedent("""
        version: 1
        policies:
          - scope: auth
            forbidden:
              - "No plaintext passwords"
    """)
    loader = PolicyLoader.from_yaml_string(yaml_text)
    policy = loader.for_scope("auth")[0]
    assert policy.required == []


def test_from_file_loads_yaml():
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(textwrap.dedent("""
            version: 1
            policies:
              - scope: api
                forbidden:
                  - "Never return 500 without logging"
        """))
        path = f.name
    try:
        loader = PolicyLoader.from_file(path)
        policies = loader.for_scope("api")
        assert len(policies) == 1
    finally:
        os.unlink(path)


def test_from_file_missing_returns_empty_loader():
    loader = PolicyLoader.from_file("/nonexistent/path/cortex_policy.yaml")
    assert loader.for_scope("auth") == []
