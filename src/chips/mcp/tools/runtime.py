from __future__ import annotations

import os

import requests

from chips.compiler.models import SourceStatus


def probe_runtime() -> SourceStatus:
    """Lightweight availability probe — does not fetch data."""
    base_url = os.getenv("SIGNOZ_API_URL")
    if not base_url:
        return SourceStatus(status="not_configured")
    try:
        requests.get(f"{base_url.rstrip('/')}/api/v1/services", timeout=1)
        return SourceStatus(status="available")
    except Exception as exc:
        return SourceStatus(status="error", detail=str(exc))


def get_runtime_context(scope: str | None = None) -> dict:
    """Return recent service spans from SigNoz. Returns status 'unavailable' if unconfigured."""
    base_url = os.getenv("SIGNOZ_API_URL")
    if not base_url:
        return {"spans": [], "scope": scope, "status": "unavailable"}

    try:
        resp = requests.get(
            f"{base_url.rstrip('/')}/api/v1/services",
            timeout=5,
        )
        resp.raise_for_status()
        services = resp.json().get("data", [])
        if scope:
            services = [
                s for s in services
                if scope.lower() in s.get("serviceName", "").lower()
            ]
        return {"spans": services, "scope": scope, "status": "ok"}
    except Exception as exc:
        return {"spans": [], "scope": scope, "status": f"error: {type(exc).__name__}"}
