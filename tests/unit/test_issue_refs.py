from __future__ import annotations

from unittest.mock import MagicMock

import httpx

from chips.harvester.issue_refs import (
    IssueRefFetcher,
    IssueRefRecord,
    harvest_issue_refs,
    label_tier_sql,
    parse_github_issue_number,
    pending_refs,
    store_issue_ref,
)


def _client(status_code: int, payload: dict | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=payload or {})

    return httpx.Client(transport=httpx.MockTransport(handler))


# --- parse ---

def test_parse_github_numeric_ref():
    assert parse_github_issue_number("#123") == 123


def test_parse_key_style_ref_is_not_github():
    assert parse_github_issue_number("SPACE-42") is None


# --- fetch statuses are truthful (L11) ---

def test_fetch_ok_extracts_metadata():
    payload = {
        "state": "closed",
        "labels": [{"name": "bug"}, {"name": "p1"}],
        "title": "Checkout skips vehicle validation",
        "closed_at": "2025-11-20T10:00:00Z",
    }
    fetcher = IssueRefFetcher("org/spacemate", client=_client(200, payload))

    record = fetcher.fetch("#123")

    assert record.fetch_status == "ok"
    assert record.issue_number == 123
    assert record.state == "closed"
    assert record.labels == ["bug", "p1"]
    assert record.title == "Checkout skips vehicle validation"
    assert record.raw == payload


def test_fetch_404_is_not_found_never_silent():
    fetcher = IssueRefFetcher("org/spacemate", client=_client(404))
    assert fetcher.fetch("#999").fetch_status == "not_found"


def test_fetch_403_is_rate_limited():
    fetcher = IssueRefFetcher("org/spacemate", client=_client(403))
    assert fetcher.fetch("#1").fetch_status == "rate_limited"


def test_fetch_500_is_failed_not_missing():
    fetcher = IssueRefFetcher("org/spacemate", client=_client(500))
    assert fetcher.fetch("#1").fetch_status == "failed"


def test_fetch_transport_error_is_failed():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    fetcher = IssueRefFetcher("org/spacemate", client=client)
    assert fetcher.fetch("#1").fetch_status == "failed"


def test_key_style_ref_skipped_without_http_call():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no HTTP call expected for key-style refs")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    fetcher = IssueRefFetcher("org/spacemate", client=client)

    record = fetcher.fetch("SPACE-42")

    assert record.fetch_status == "skipped"
    assert record.issue_number is None


def test_fetch_sends_token_when_provided():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, json={})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    IssueRefFetcher("org/spacemate", token="tok", client=client).fetch("#1")

    assert seen["auth"] == "Bearer tok"


# --- storage ---

def test_store_issue_ref_upserts_on_repo_ref():
    conn = MagicMock()
    record = IssueRefRecord(ref="#123", repo="org/spacemate", fetch_status="ok", labels=["bug"])

    store_issue_ref(conn, record)

    sql = conn.execute.call_args.args[0]
    assert "INSERT INTO cortex_issue_refs" in sql
    assert "ON CONFLICT (repo, ref) DO UPDATE" in sql


def test_pending_refs_selects_unfetched_and_rate_limited():
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = [("#1",), ("#2",)]
    conn.execute.return_value = cursor

    refs = pending_refs(conn, "org/spacemate")

    assert refs == ["#1", "#2"]
    sql = conn.execute.call_args.args[0]
    assert "unnest(issue_refs)" in sql
    assert "i.ref IS NULL OR i.fetch_status = 'rate_limited'" in sql


def test_harvest_stops_batch_on_rate_limit():
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = [("#1",), ("#2",), ("#3",)]
    conn.execute.return_value = cursor

    fetcher = MagicMock()
    fetcher.fetch.side_effect = [
        IssueRefRecord(ref="#1", repo="r", fetch_status="ok"),
        IssueRefRecord(ref="#2", repo="r", fetch_status="rate_limited"),
    ]

    counts = harvest_issue_refs(conn, "r", fetcher=fetcher)

    assert counts["ok"] == 1
    assert counts["rate_limited"] == 1
    assert fetcher.fetch.call_count == 2  # '#3' stays pending


# --- label tiers computed at query time ---

def test_label_tier_sql_orders_t1_above_t2_above_t3_above_t4():
    sql = label_tier_sql("d", "i")
    assert sql.index("'T1'") < sql.index("'T2'") < sql.index("'T3'") < sql.index("'T4'")
    assert "i.fetch_status = 'ok'" in sql
    assert "d.revert_of_sha IS NOT NULL" in sql
    assert "ELSE NULL END" in sql
