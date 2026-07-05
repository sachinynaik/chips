from __future__ import annotations
from unittest.mock import MagicMock
from chips.harvester.enrichment.cochange import CochangeFetcher

def _mock_conn(rows):
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = rows
    return conn

def test_fetch_returns_cochange_pairs():
    conn = _mock_conn([("src/auth/token.py", "src/auth/session.py", 5)])
    result = CochangeFetcher().fetch(conn, ["src/auth/token.py"])
    assert len(result) == 1
    assert result[0]["frequency"] == 5

def test_fetch_returns_empty_for_no_files():
    result = CochangeFetcher().fetch(MagicMock(), [])
    assert result == []

def test_fetch_returns_empty_on_db_error():
    conn = MagicMock()
    conn.execute.side_effect = Exception("db error")
    result = CochangeFetcher().fetch(conn, ["src/auth/token.py"])
    assert result == []


def test_last_status_defaults_to_skipped():
    assert CochangeFetcher().last_status == "skipped"


def test_last_status_ok_on_success():
    conn = _mock_conn([("src/auth/token.py", "src/auth/session.py", 5)])
    fetcher = CochangeFetcher()
    fetcher.fetch(conn, ["src/auth/token.py"])
    assert fetcher.last_status == "ok"


def test_last_status_skipped_for_no_files():
    fetcher = CochangeFetcher()
    fetcher.fetch(MagicMock(), [])
    assert fetcher.last_status == "skipped"


def test_last_status_failed_on_db_error():
    conn = MagicMock()
    conn.execute.side_effect = Exception("db error")
    fetcher = CochangeFetcher()
    fetcher.fetch(conn, ["src/auth/token.py"])
    assert fetcher.last_status == "failed"
