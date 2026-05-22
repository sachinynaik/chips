"""Docker-free unit tests for get_runtime_context tool function."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from chips.mcp.tools.runtime import get_runtime_context


# ---------------------------------------------------------------------------
# Unavailable (no SIGNOZ_API_URL)
# ---------------------------------------------------------------------------

def test_returns_unavailable_when_env_not_set(monkeypatch):
    monkeypatch.delenv("SIGNOZ_API_URL", raising=False)
    result = get_runtime_context()
    assert result["status"] == "unavailable"
    assert result["spans"] == []


def test_unavailable_preserves_scope(monkeypatch):
    monkeypatch.delenv("SIGNOZ_API_URL", raising=False)
    result = get_runtime_context(scope="payments")
    assert result["scope"] == "payments"


def test_unavailable_scope_none_by_default(monkeypatch):
    monkeypatch.delenv("SIGNOZ_API_URL", raising=False)
    result = get_runtime_context()
    assert result["scope"] is None


# ---------------------------------------------------------------------------
# Success path (SIGNOZ_API_URL set, HTTP succeeds)
# ---------------------------------------------------------------------------

def _mock_response(data):
    resp = MagicMock()
    resp.json.return_value = {"data": data}
    resp.raise_for_status.return_value = None
    return resp


def test_returns_ok_status_when_signoz_responds(monkeypatch):
    monkeypatch.setenv("SIGNOZ_API_URL", "http://signoz:3301")
    with patch("chips.mcp.tools.runtime.requests.get", return_value=_mock_response([])):
        result = get_runtime_context()
    assert result["status"] == "ok"


def test_spans_contains_service_data(monkeypatch):
    monkeypatch.setenv("SIGNOZ_API_URL", "http://signoz:3301")
    services = [{"serviceName": "auth-service", "p99": 120.0}]
    with patch("chips.mcp.tools.runtime.requests.get", return_value=_mock_response(services)):
        result = get_runtime_context()
    assert result["spans"] == services


def test_scope_filters_services_by_name(monkeypatch):
    monkeypatch.setenv("SIGNOZ_API_URL", "http://signoz:3301")
    services = [
        {"serviceName": "auth-service"},
        {"serviceName": "parking-service"},
    ]
    with patch("chips.mcp.tools.runtime.requests.get", return_value=_mock_response(services)):
        result = get_runtime_context(scope="auth")
    assert len(result["spans"]) == 1
    assert result["spans"][0]["serviceName"] == "auth-service"


def test_no_scope_returns_all_services(monkeypatch):
    monkeypatch.setenv("SIGNOZ_API_URL", "http://signoz:3301")
    services = [{"serviceName": "auth"}, {"serviceName": "parking"}]
    with patch("chips.mcp.tools.runtime.requests.get", return_value=_mock_response(services)):
        result = get_runtime_context(scope=None)
    assert len(result["spans"]) == 2


def test_url_constructed_from_env(monkeypatch):
    monkeypatch.setenv("SIGNOZ_API_URL", "http://signoz:3301")
    with patch("chips.mcp.tools.runtime.requests.get", return_value=_mock_response([])) as mock_get:
        get_runtime_context()
    url = mock_get.call_args[0][0]
    assert "signoz:3301" in url
    assert "/api/v1/services" in url


def test_trailing_slash_stripped_from_base_url(monkeypatch):
    monkeypatch.setenv("SIGNOZ_API_URL", "http://signoz:3301/")
    with patch("chips.mcp.tools.runtime.requests.get", return_value=_mock_response([])) as mock_get:
        get_runtime_context()
    url = mock_get.call_args[0][0]
    assert "//" not in url.replace("http://", "").replace("https://", "")


# ---------------------------------------------------------------------------
# Error path (HTTP fails)
# ---------------------------------------------------------------------------

def test_returns_error_status_on_http_failure(monkeypatch):
    monkeypatch.setenv("SIGNOZ_API_URL", "http://signoz:3301")
    with patch("chips.mcp.tools.runtime.requests.get", side_effect=Exception("timeout")):
        result = get_runtime_context()
    assert result["status"].startswith("error:")
    assert result["spans"] == []


def test_error_preserves_scope(monkeypatch):
    monkeypatch.setenv("SIGNOZ_API_URL", "http://signoz:3301")
    with patch("chips.mcp.tools.runtime.requests.get", side_effect=Exception("timeout")):
        result = get_runtime_context(scope="auth")
    assert result["scope"] == "auth"
