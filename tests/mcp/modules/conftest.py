"""
Local conftest for mcp/modules tests.
These tests are pure unit tests (no DB) — override session-scoped DB fixtures
so Docker is never required when running this directory in isolation.
"""
import pytest


@pytest.fixture(scope="session")
def _container():
    yield None


@pytest.fixture(scope="session")
def alembic_url(_container):
    return ""


@pytest.fixture(scope="session", autouse=True)
def apply_migrations(alembic_url):
    pass
