"""Compiler tests are a mix of mock-based and DB-backed cases."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def apply_migrations(request):  # noqa: F811 - intentional override of root fixture
    """No-op only when no explicit DB-backed test path is configured."""
    if os.getenv("CHIPS_TEST_DB_URL") or os.getenv("CHIPS_TEST_DB_ROOT_URL"):
        return request.getfixturevalue("_root_apply_migrations")
    return
