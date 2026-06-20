from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit
import uuid
from typing import Any

import psycopg

_CONNECT_TIMEOUT_SECONDS = 5


@dataclass(frozen=True)
class TestDatabasePlan:
    mode: str
    url: str | None = None
    root_url: str | None = None


def build_test_database_plan(
    *,
    explicit_url: str | None,
    root_url: str | None,
) -> TestDatabasePlan:
    if explicit_url:
        return TestDatabasePlan(mode="explicit", url=explicit_url)
    if root_url:
        return TestDatabasePlan(mode="root", root_url=root_url)
    return TestDatabasePlan(mode="container")


def resolve_test_database_plan(
    *,
    explicit_url: str | None,
    root_url: str | None,
) -> TestDatabasePlan:
    plan = build_test_database_plan(explicit_url=explicit_url, root_url=root_url)
    if plan.mode == "explicit":
        return plan
    if plan.mode == "root" and plan.root_url is not None:
        if can_connect_root(plan.root_url):
            return plan
        return TestDatabasePlan(mode="container")
    return plan


def resolve_runtime_database_urls(
    *,
    explicit_url: str | None,
    temp_db: dict[str, str] | None,
    container: Any | None,
) -> tuple[str, str] | None:
    if explicit_url:
        return explicit_url, explicit_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if temp_db:
        url = temp_db["url"]
        return url, url.replace("postgresql://", "postgresql+psycopg://", 1)
    if container is not None:
        psycopg_url = container.get_connection_url().replace("postgresql+psycopg2://", "postgresql://")
        alembic_url = container.get_connection_url().replace("postgresql+psycopg2", "postgresql+psycopg")
        return psycopg_url, alembic_url
    return None


def create_temporary_database(root_url: str, prefix: str = "chips_test_") -> tuple[str, str]:
    db_name = prefix + uuid.uuid4().hex[:8]
    with _connect_root(root_url) as conn:
        with conn.cursor() as cur:
            cur.execute(f'CREATE DATABASE "{db_name}"')
    return db_name, replace_database_name(root_url, db_name)


def drop_temporary_database(root_url: str, db_name: str) -> None:
    with _connect_root(root_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()",
                (db_name,),
            )
            cur.execute(f'DROP DATABASE IF EXISTS "{db_name}"')


def cleanup_temporary_databases(root_url: str, prefix: str = "chips_test_") -> list[str]:
    dropped: list[str] = []
    with _connect_root(root_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT datname FROM pg_database WHERE datname LIKE %s ORDER BY datname",
                (f"{prefix}%",),
            )
            for (db_name,) in cur.fetchall():
                if not db_name.startswith(prefix):
                    continue
                cur.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()",
                    (db_name,),
                )
                cur.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
                dropped.append(db_name)
    return dropped


def can_connect_root(root_url: str) -> bool:
    try:
        with _connect_root(root_url):
            return True
    except RuntimeError:
        return False


def _connect_root(root_url: str) -> psycopg.Connection:
    try:
        return psycopg.connect(
            root_url,
            autocommit=True,
            connect_timeout=_CONNECT_TIMEOUT_SECONDS,
        )
    except psycopg.OperationalError as exc:
        raise RuntimeError(
            "Unable to connect to test database root URL for temporary database lifecycle management"
        ) from exc


def replace_database_name(url: str, database_name: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, f"/{database_name}", parts.query, parts.fragment))
