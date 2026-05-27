from __future__ import annotations

import os
import time

import requests

from chips.compiler.models import SourceStatus
from chips.mcp.tools.health_tracker import record_source_probe


def probe_runtime() -> SourceStatus:
    """Lightweight availability probe that does not fetch business data."""
    from datetime import datetime, timezone

    base_url = os.getenv("SIGNOZ_API_URL")
    if not base_url:
        status = SourceStatus(status="not_configured")
        record_source_probe("runtime", status, 0)
        return status
    checked_at = datetime.now(timezone.utc)
    start = time.monotonic()
    try:
        resp = requests.get(f"{base_url.rstrip('/')}/api/v1/services", timeout=1)
        resp.raise_for_status()
        status = SourceStatus(status="available", checked_at=checked_at)
    except Exception as exc:
        status = SourceStatus(status="error", detail=str(exc), checked_at=checked_at)
    record_source_probe("runtime", status, int((time.monotonic() - start) * 1000))
    return status


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
