"""Guard: the span contract tests must not *silently* skip in CI.

tests/unit/test_tracing_spans.py and tests/compiler/test_builder_spans.py skip
when the full OpenTelemetry stack is absent (honest on Windows dev, which lacks
the exporter/instrumentation packages). The risk: if those deps ever drift out
of the lockfile, CI would skip the span gate and read green.

This test closes that hole. The intended env (the container runner and CI both
set CHIPS_REQUIRE_OTEL=1) asserts the stack is importable, so a drift turns CI
red instead of hiding the gate. Locally (env unset) it skips like the rest.
"""

from __future__ import annotations

import os

import pytest

from chips.observability import tracing


def test_full_otel_stack_present_when_required():
    if not os.getenv("CHIPS_REQUIRE_OTEL"):
        pytest.skip("CHIPS_REQUIRE_OTEL not set (local dev may lack the full OTel stack)")
    assert tracing._OTEL_AVAILABLE, (
        "CHIPS_REQUIRE_OTEL is set but the full OpenTelemetry stack failed to import; "
        "the span contract tests would silently skip. Check the opentelemetry-* deps."
    )
