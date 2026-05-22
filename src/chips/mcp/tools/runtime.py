from __future__ import annotations

import os

import requests


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
