from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field

from chips.compiler.models import SourceStatus

logger = logging.getLogger(__name__)


@dataclass
class ProbeObservation:
    state_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    consecutive_errors: int = 0
    last_latency_ms: int | None = None
    last_status: SourceStatus | None = None


_OBSERVATIONS: dict[str, ProbeObservation] = {
    "runtime": ProbeObservation(),
    "workflow": ProbeObservation(),
}


def record_source_probe(source: str, status: SourceStatus, latency_ms: int) -> None:
    observation = _OBSERVATIONS.setdefault(source, ProbeObservation())
    observation.state_counts[status.status] += 1
    observation.last_latency_ms = latency_ms
    observation.last_status = status
    if status.status == "error":
        observation.consecutive_errors += 1
        logger.warning(
            "source probe failed",
            extra={"source": source, "status": status.status, "latency_ms": latency_ms},
        )
    else:
        observation.consecutive_errors = 0
        logger.info(
            "source probe succeeded",
            extra={"source": source, "status": status.status, "latency_ms": latency_ms},
        )


def get_probe_observations() -> dict[str, ProbeObservation]:
    return _OBSERVATIONS
