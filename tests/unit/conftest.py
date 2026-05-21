"""Local conftest for unit (mock-based) tests — no Docker, no DB required.

Overrides the session-level autouse `apply_migrations` fixture so that
Docker/testcontainers are never started when running these tests in isolation.
"""
import pytest


@pytest.fixture(scope="session", autouse=True)
def apply_migrations():  # noqa: F811 — intentional override of root conftest fixture
    """No-op: unit tests use mocked connections; no DB migration needed."""
    return
