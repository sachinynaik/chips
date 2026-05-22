"""Local conftest for compiler tests — overrides autouse apply_migrations.

All compiler tests are mock-based (no real DB). Without this override the
session-level autouse fixture pulls in testcontainers for every test here.
"""
import pytest


@pytest.fixture(scope="session", autouse=True)
def apply_migrations():  # noqa: F811 — intentional override of root conftest fixture
    """No-op: compiler tests use mocked connections; no DB migration needed."""
    return
