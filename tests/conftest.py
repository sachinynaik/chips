"""
Test database strategy:
  Dev (fast):  set CHIPS_TEST_DB_URL=postgresql://... to use a persistent DB
  CI (isolated): leave unset — testcontainers starts a fresh pgvector container

Each test gets a connection that rolls back after the test, so tests never
leak state into each other regardless of which DB backend is used.
"""
import os
import pytest
import psycopg

POSTGRES_IMAGE = "pgvector/pgvector:pg16"
_TEST_DB_URL = os.getenv("CHIPS_TEST_DB_URL")


# ---------------------------------------------------------------------------
# Container / URL fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def _container():
    """Only started when CHIPS_TEST_DB_URL is not set."""
    if _TEST_DB_URL:
        yield None
        return
    from testcontainers.postgres import PostgresContainer
    with PostgresContainer(POSTGRES_IMAGE) as pg:
        yield pg


@pytest.fixture(scope="session")
def psycopg_url(_container) -> str:
    """Plain postgresql:// URL for psycopg3 direct connections."""
    if _TEST_DB_URL:
        return _TEST_DB_URL
    return _container.get_connection_url().replace("postgresql+psycopg2://", "postgresql://")


@pytest.fixture(scope="session")
def alembic_url(_container) -> str:
    """postgresql+psycopg:// URL for SQLAlchemy / Alembic."""
    if _TEST_DB_URL:
        return _TEST_DB_URL.replace("postgresql://", "postgresql+psycopg://", 1)
    return _container.get_connection_url().replace("postgresql+psycopg2", "postgresql+psycopg")


# ---------------------------------------------------------------------------
# Migration — runs once per session
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def apply_migrations(alembic_url):
    from alembic.config import Config
    from alembic import command

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", alembic_url)
    command.upgrade(cfg, "head")


# ---------------------------------------------------------------------------
# Per-test connection with automatic rollback
# ---------------------------------------------------------------------------

@pytest.fixture()
def conn(psycopg_url):
    """Isolated connection — all writes are rolled back after the test."""
    connection = psycopg.connect(psycopg_url, autocommit=False)
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()
