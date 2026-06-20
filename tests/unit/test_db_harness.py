from __future__ import annotations

from unittest.mock import MagicMock
from unittest.mock import patch

import psycopg
import pytest

from chips.testing.db_harness import (
    build_test_database_plan,
    can_connect_root,
    cleanup_temporary_databases,
    create_temporary_database,
    drop_temporary_database,
    replace_database_name,
    resolve_runtime_database_urls,
    resolve_test_database_plan,
)


def test_build_test_database_plan_prefers_explicit_url():
    plan = build_test_database_plan(
        explicit_url="postgresql://u:p@h/db",
        root_url="postgresql://u:p@h/postgres",
    )

    assert plan.mode == "explicit"
    assert plan.url == "postgresql://u:p@h/db"


def test_build_test_database_plan_uses_root_mode_when_only_root_url_is_set():
    plan = build_test_database_plan(
        explicit_url=None,
        root_url="postgresql://u:p@h/postgres",
    )

    assert plan.mode == "root"
    assert plan.root_url == "postgresql://u:p@h/postgres"


def test_build_test_database_plan_falls_back_to_container_mode():
    plan = build_test_database_plan(
        explicit_url=None,
        root_url=None,
    )

    assert plan.mode == "container"


def test_resolve_test_database_plan_prefers_explicit_without_connect_probe():
    with patch("chips.testing.db_harness.can_connect_root") as probe:
        plan = resolve_test_database_plan(
            explicit_url="postgresql://u:p@h/db",
            root_url="postgresql://u:p@h/postgres",
        )

    assert plan.mode == "explicit"
    probe.assert_not_called()


def test_resolve_test_database_plan_uses_root_when_root_is_reachable():
    with patch("chips.testing.db_harness.can_connect_root", return_value=True) as probe:
        plan = resolve_test_database_plan(
            explicit_url=None,
            root_url="postgresql://u:p@h/postgres",
        )

    assert plan.mode == "root"
    probe.assert_called_once_with("postgresql://u:p@h/postgres")


def test_resolve_test_database_plan_falls_back_to_container_when_root_is_unreachable():
    with patch("chips.testing.db_harness.can_connect_root", return_value=False) as probe:
        plan = resolve_test_database_plan(
            explicit_url=None,
            root_url="postgresql://u:p@h/postgres",
        )

    assert plan.mode == "container"
    probe.assert_called_once_with("postgresql://u:p@h/postgres")


def test_replace_database_name_swaps_path_only():
    assert (
        replace_database_name("postgresql://u:p@localhost:5432/postgres?sslmode=disable", "chips_test_1234")
        == "postgresql://u:p@localhost:5432/chips_test_1234?sslmode=disable"
    )


def test_create_temporary_database_creates_db_and_returns_derived_url():
    fake_cursor = MagicMock()
    fake_conn = MagicMock()
    fake_conn.cursor.return_value.__enter__.return_value = fake_cursor
    fake_connect = MagicMock()
    fake_connect.return_value.__enter__.return_value = fake_conn

    with patch("chips.testing.db_harness.psycopg.connect", fake_connect):
        with patch("chips.testing.db_harness.uuid.uuid4") as mock_uuid:
            mock_uuid.return_value.hex = "abcdef1234567890"
            db_name, db_url = create_temporary_database("postgresql://u:p@h/postgres")

    assert db_name == "chips_test_abcdef12"
    assert db_url == "postgresql://u:p@h/chips_test_abcdef12"
    assert fake_connect.call_args.kwargs["connect_timeout"] == 5
    fake_cursor.execute.assert_called_once_with('CREATE DATABASE "chips_test_abcdef12"')


def test_drop_temporary_database_issues_drop_sql():
    fake_cursor = MagicMock()
    fake_conn = MagicMock()
    fake_conn.cursor.return_value.__enter__.return_value = fake_cursor
    fake_connect = MagicMock()
    fake_connect.return_value.__enter__.return_value = fake_conn

    with patch("chips.testing.db_harness.psycopg.connect", fake_connect):
        drop_temporary_database("postgresql://u:p@h/postgres", "chips_test_deadbeef")

    assert fake_connect.call_args.kwargs["connect_timeout"] == 5
    assert fake_cursor.execute.call_args_list[0].args == (
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()",
        ("chips_test_deadbeef",),
    )
    assert fake_cursor.execute.call_args_list[1].args == ('DROP DATABASE IF EXISTS "chips_test_deadbeef"',)


def test_cleanup_temporary_databases_drops_only_matching_prefix():
    fake_cursor = MagicMock()
    fake_cursor.fetchall.return_value = [("chips_test_one",), ("chips_test_two",), ("other_db",)]
    fake_conn = MagicMock()
    fake_conn.cursor.return_value.__enter__.return_value = fake_cursor
    fake_connect = MagicMock()
    fake_connect.return_value.__enter__.return_value = fake_conn

    with patch("chips.testing.db_harness.psycopg.connect", fake_connect):
        dropped = cleanup_temporary_databases("postgresql://u:p@h/postgres", prefix="chips_test_")

    assert dropped == ["chips_test_one", "chips_test_two"]
    assert fake_connect.call_args.kwargs["connect_timeout"] == 5
    assert fake_cursor.execute.call_args_list[0].args[0].startswith("SELECT datname FROM pg_database")
    assert fake_cursor.execute.call_args_list[1].args == (
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()",
        ("chips_test_one",),
    )
    assert fake_cursor.execute.call_args_list[2].args == ('DROP DATABASE IF EXISTS "chips_test_one"',)
    assert fake_cursor.execute.call_args_list[3].args == (
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()",
        ("chips_test_two",),
    )
    assert fake_cursor.execute.call_args_list[4].args == ('DROP DATABASE IF EXISTS "chips_test_two"',)


def test_cleanup_temporary_databases_raises_clear_error_on_connection_failure():
    with patch(
        "chips.testing.db_harness.psycopg.connect",
        side_effect=psycopg.OperationalError("connect timed out"),
    ):
        with pytest.raises(RuntimeError, match="Unable to connect to test database root URL"):
            cleanup_temporary_databases("postgresql://u:p@h/postgres", prefix="chips_test_")


def test_can_connect_root_returns_false_on_operational_error():
    with patch(
        "chips.testing.db_harness.psycopg.connect",
        side_effect=psycopg.OperationalError("connect timed out"),
    ):
        assert can_connect_root("postgresql://u:p@h/postgres") is False


def test_resolve_runtime_database_urls_prefers_explicit_url():
    urls = resolve_runtime_database_urls(
        explicit_url="postgresql://u:p@h/db",
        temp_db=None,
        container=None,
    )

    assert urls == (
        "postgresql://u:p@h/db",
        "postgresql+psycopg://u:p@h/db",
    )


def test_resolve_runtime_database_urls_uses_temp_db_when_available():
    urls = resolve_runtime_database_urls(
        explicit_url=None,
        temp_db={"url": "postgresql://u:p@h/chips_test_1234"},
        container=None,
    )

    assert urls == (
        "postgresql://u:p@h/chips_test_1234",
        "postgresql+psycopg://u:p@h/chips_test_1234",
    )


def test_resolve_runtime_database_urls_uses_container_url_when_available():
    container = MagicMock()
    container.get_connection_url.return_value = "postgresql+psycopg2://u:p@h/test"

    urls = resolve_runtime_database_urls(
        explicit_url=None,
        temp_db=None,
        container=container,
    )

    assert urls == (
        "postgresql://u:p@h/test",
        "postgresql+psycopg://u:p@h/test",
    )


def test_resolve_runtime_database_urls_returns_none_when_no_backend_is_available():
    urls = resolve_runtime_database_urls(
        explicit_url=None,
        temp_db=None,
        container=None,
    )

    assert urls is None
