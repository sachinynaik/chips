from __future__ import annotations

from datetime import datetime, timezone

from chips.mcp.tools.health_tracker import get_probe_observations
from chips.mcp.tools.runtime import probe_runtime
from chips.mcp.tools.workflow import probe_workflow


def _serialize_source_status(source: str, status) -> dict:
    observation = get_probe_observations().get(source)
    return {
        "status": status.status,
        "detail": status.detail,
        "checked_at": status.checked_at.isoformat() if status.checked_at else None,
        "last_latency_ms": observation.last_latency_ms if observation else None,
        "consecutive_errors": observation.consecutive_errors if observation else 0,
        "state_counts": dict(observation.state_counts) if observation else {},
    }


def get_source_health() -> dict:
    runtime_status = probe_runtime()
    workflow_status = probe_workflow()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "runtime": _serialize_source_status("runtime", runtime_status),
            "workflow": _serialize_source_status("workflow", workflow_status),
        },
    }
