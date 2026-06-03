from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from chips.observability.openinference import SPAN_KIND_KEY

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    _OTEL_AVAILABLE = True
except ImportError:  # pragma: no cover
    trace = None  # type: ignore[assignment]
    OTLPSpanExporter = HTTPXClientInstrumentor = PsycopgInstrumentor = None  # type: ignore[assignment]
    Resource = TracerProvider = BatchSpanProcessor = None  # type: ignore[assignment]
    _OTEL_AVAILABLE = False

_CONFIGURED = False
_HTTPX_INSTRUMENTED = False
_PSYCOPG_INSTRUMENTED = False


def _telemetry_requested() -> bool:
    flag = os.getenv("CHIPS_ENABLE_OTEL", "").strip().lower()
    return flag in {"1", "true", "yes", "on"} or bool(
        os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        or os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
    )


def configure_telemetry(service_name: str = "chips-cortex") -> bool:
    global _CONFIGURED, _HTTPX_INSTRUMENTED, _PSYCOPG_INSTRUMENTED
    if not _OTEL_AVAILABLE or not _telemetry_requested():
        return False

    if not _CONFIGURED:
        provider = trace.get_tracer_provider()
        if provider.__class__.__name__ == "ProxyTracerProvider":
            tracer_provider = TracerProvider(
                resource=Resource.create({"service.name": service_name})
            )
            tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
            trace.set_tracer_provider(tracer_provider)
        _CONFIGURED = True

    if not _HTTPX_INSTRUMENTED:
        try:
            HTTPXClientInstrumentor().instrument()
            _HTTPX_INSTRUMENTED = True
        except Exception:
            pass

    if not _PSYCOPG_INSTRUMENTED:
        try:
            PsycopgInstrumentor().instrument()
            _PSYCOPG_INSTRUMENTED = True
        except Exception:
            pass

    return True


def _get_tracer():
    """Resolve the ``chips`` tracer from the active provider.

    Isolated as a seam so tests can inject an in-memory provider without
    fighting OpenTelemetry's process-global set-once guard.
    """
    return trace.get_tracer("chips")


@contextmanager
def start_span(
    name: str, kind: str | None = None, **attributes: object
) -> Iterator[object | None]:
    if not _OTEL_AVAILABLE:
        yield None
        return

    tracer = _get_tracer()
    with tracer.start_as_current_span(name) as span:
        if kind is not None:
            span.set_attribute(SPAN_KIND_KEY, kind)
        for key, value in attributes.items():
            if value is not None:
                span.set_attribute(key, value)
        yield span
