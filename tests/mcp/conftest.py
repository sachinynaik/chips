"""Local conftest for MCP tests — overrides autouse apply_migrations.

Mock-based MCP tests (test_server.py) don't need a real DB. Without this
override the session-level autouse fixture pulls in testcontainers for every
test in this directory, even those that never touch the DB.
"""
import pytest


@pytest.fixture(scope="session", autouse=True)
def apply_migrations():  # noqa: F811 — intentional override of root conftest fixture
    """No-op: MCP unit tests use mocked connections; no DB migration needed."""
    return
