from __future__ import annotations

try:  # pragma: no cover - platform guard
    import resource as _resource

    if not hasattr(_resource, "getpagesize"):
        _resource.getpagesize = lambda: 4096  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover
    _resource = None

try:
    from prometheus_client.exposition import generate_latest
    from prometheus_client.metrics import Counter, Histogram
    from prometheus_client.registry import CollectorRegistry

    _METRICS_AVAILABLE = True
except ImportError:  # pragma: no cover
    CollectorRegistry = Counter = Histogram = None  # type: ignore[assignment]
    generate_latest = None  # type: ignore[assignment]
    _METRICS_AVAILABLE = False

if _METRICS_AVAILABLE:
    REGISTRY = CollectorRegistry(auto_describe=True)
    _BRIEF_BUILD_TOTAL = Counter(
        "chips_brief_build_total",
        "Count of brief build attempts by final status.",
        ("status",),
        registry=REGISTRY,
    )
    _BRIEF_BUILD_LATENCY_SECONDS = Histogram(
        "chips_brief_build_latency_seconds",
        "Latency of successful brief builds.",
        registry=REGISTRY,
    )
    _FEEDBACK_TOTAL = Counter(
        "chips_feedback_submission_total",
        "Count of brief feedback submissions.",
        ("outcome", "deduplicated"),
        registry=REGISTRY,
    )
    _FEEDBACK_LATENCY_SECONDS = Histogram(
        "chips_feedback_submission_latency_seconds",
        "Latency of brief feedback submission handling.",
        registry=REGISTRY,
    )
    _LEARNING_RECOMPUTE_TOTAL = Counter(
        "chips_learning_recompute_total",
        "Count of learning recompute attempts.",
        ("status",),
        registry=REGISTRY,
    )
    _LEARNING_RECOMPUTE_SECONDS = Histogram(
        "chips_learning_recompute_seconds",
        "Latency of learning recompute operations.",
        registry=REGISTRY,
    )
    _GOVERNOR_DECISION_TOTAL = Counter(
        "chips_governor_decision_total",
        "Count of governor decisions by trigger state.",
        ("triggered",),
        registry=REGISTRY,
    )
    _RERANK_TOTAL = Counter(
        "chips_rerank_total",
        "Count of reranker outcomes.",
        ("status",),
        registry=REGISTRY,
    )
    _STRUCTURAL_TOTAL = Counter(
        "chips_structural_retrieval_total",
        "Count of structural retrieval outcomes.",
        ("status",),
        registry=REGISTRY,
    )
else:  # pragma: no cover
    REGISTRY = None


def observe_brief_build(*, status: str, latency_ms: int | None = None) -> None:
    if not _METRICS_AVAILABLE:
        return
    _BRIEF_BUILD_TOTAL.labels(status=status).inc()
    if latency_ms is not None and status == "success":
        _BRIEF_BUILD_LATENCY_SECONDS.observe(max(latency_ms, 0) / 1000.0)


def observe_feedback_submission(
    *, outcome: str, deduplicated: bool, latency_ms: int
) -> None:
    if not _METRICS_AVAILABLE:
        return
    _FEEDBACK_TOTAL.labels(
        outcome=outcome, deduplicated=str(deduplicated).lower()
    ).inc()
    _FEEDBACK_LATENCY_SECONDS.observe(max(latency_ms, 0) / 1000.0)


def observe_learning_recompute(*, status: str, duration_s: float) -> None:
    if not _METRICS_AVAILABLE:
        return
    _LEARNING_RECOMPUTE_TOTAL.labels(status=status).inc()
    _LEARNING_RECOMPUTE_SECONDS.observe(max(duration_s, 0.0))


def observe_governor_decision(*, triggered: bool) -> None:
    if not _METRICS_AVAILABLE:
        return
    _GOVERNOR_DECISION_TOTAL.labels(triggered=str(triggered).lower()).inc()


def observe_rerank(*, status: str) -> None:
    if not _METRICS_AVAILABLE:
        return
    _RERANK_TOTAL.labels(status=status).inc()


def observe_structural_retrieval(*, status: str) -> None:
    if not _METRICS_AVAILABLE:
        return
    _STRUCTURAL_TOTAL.labels(status=status).inc()


def render_latest_metrics() -> str:
    if not _METRICS_AVAILABLE:
        return ""
    return generate_latest(REGISTRY).decode("utf-8")
