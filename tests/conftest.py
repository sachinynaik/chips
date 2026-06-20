"""
Test database strategy:
  Dev (fast):  set CHIPS_TEST_DB_URL=postgresql://... to use a persistent DB
  CI (isolated): leave unset — testcontainers starts a fresh pgvector container

Each test gets a connection that rolls back after the test, so tests never
leak state into each other regardless of which DB backend is used.
"""
import os
from pathlib import Path
import pytest
try:
    import psycopg
    _PSYCOPG_AVAILABLE = True
except ImportError:
    _PSYCOPG_AVAILABLE = False
from chips.testing.db_harness import (
    resolve_runtime_database_urls,
    resolve_test_database_plan,
    cleanup_temporary_databases,
    create_temporary_database,
    drop_temporary_database,
)

POSTGRES_IMAGE = "pgvector/pgvector:pg16"
_TEST_DB_URL = os.getenv("CHIPS_TEST_DB_URL")
_TEST_DB_ROOT_URL = os.getenv("CHIPS_TEST_DB_ROOT_URL")
_LOCAL_TMP_ROOT = Path(__file__).parent.parent / ".pytest_tmp"


# ---------------------------------------------------------------------------
# Container / URL fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def _resolved_db_plan():
    return resolve_test_database_plan(explicit_url=_TEST_DB_URL, root_url=_TEST_DB_ROOT_URL)


@pytest.fixture(scope="session")
def _container(_resolved_db_plan):
    """Container fallback when no explicit DB is configured and root DB is unavailable."""
    plan = _resolved_db_plan
    if plan.mode != "container":
        yield None
        return
    from testcontainers.postgres import PostgresContainer
    try:
        container = PostgresContainer(POSTGRES_IMAGE)
        container.start()
    except Exception:
        yield None
        return
    try:
        yield container
    finally:
        container.stop()


@pytest.fixture(scope="session")
def _temp_db(_resolved_db_plan):
    plan = _resolved_db_plan
    if plan.mode != "root":
        yield None
        return
    assert plan.root_url is not None
    cleanup_temporary_databases(plan.root_url)
    db_name, db_url = create_temporary_database(plan.root_url)
    try:
        yield {"name": db_name, "url": db_url, "root_url": plan.root_url}
    finally:
        drop_temporary_database(plan.root_url, db_name)
        cleanup_temporary_databases(plan.root_url)


@pytest.fixture(scope="session")
def psycopg_url(_container, _temp_db) -> str:
    """Plain postgresql:// URL for psycopg3 direct connections."""
    urls = resolve_runtime_database_urls(
        explicit_url=_TEST_DB_URL,
        temp_db=_temp_db,
        container=_container,
    )
    if urls is None:
        pytest.skip(
            "No DB-backed test backend available: root Postgres unreachable and container backend unavailable"
        )
    return urls[0]


@pytest.fixture(scope="session")
def alembic_url(_container, _temp_db) -> str:
    """postgresql+psycopg:// URL for SQLAlchemy / Alembic."""
    urls = resolve_runtime_database_urls(
        explicit_url=_TEST_DB_URL,
        temp_db=_temp_db,
        container=_container,
    )
    if urls is None:
        pytest.skip(
            "No DB-backed test backend available: root Postgres unreachable and container backend unavailable"
        )
    return urls[1]


# ---------------------------------------------------------------------------
# Migration — runs once per session
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def _root_apply_migrations(alembic_url):
    from alembic.config import Config
    from alembic import command

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", alembic_url)
    command.upgrade(cfg, "head")


@pytest.fixture(scope="session", autouse=True)
def apply_migrations(_root_apply_migrations):
    return _root_apply_migrations


# ---------------------------------------------------------------------------
# Per-test connection with automatic rollback
# ---------------------------------------------------------------------------

@pytest.fixture()
def conn(psycopg_url):
    """Isolated connection — all writes are rolled back after the test."""
    if not _PSYCOPG_AVAILABLE:
        pytest.skip("psycopg not available")
    connection = psycopg.connect(psycopg_url, autocommit=False)
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


@pytest.fixture()
def tmp_path(request):
    """Project-local tmp_path override for Windows-safe test execution."""
    name = request.node.name
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)[:80]
    p = _LOCAL_TMP_ROOT / safe
    p.mkdir(parents=True, exist_ok=True)
    yield p
