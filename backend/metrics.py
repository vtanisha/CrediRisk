try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

    prediction_requests_total = Counter(
        "credirisk_prediction_requests_total",
        "Total prediction requests",
        ["model_type", "risk_tier"],
    )
    prediction_latency_seconds = Histogram(
        "credirisk_prediction_latency_seconds",
        "Prediction inference latency",
        ["model_type"],
        buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
    )
    inference_errors_total = Counter(
        "credirisk_inference_errors_total",
        "Total inference errors",
    )
    chat_requests_total = Counter(
        "credirisk_chat_requests_total",
        "Total AI chat requests",
    )

    PROMETHEUS_AVAILABLE = True

except ImportError:
    PROMETHEUS_AVAILABLE = False
    generate_latest = None
    CONTENT_TYPE_LATEST = "text/plain"

    class _Noop:
        def labels(self, **kwargs): return self
        def inc(self, *a, **kw): pass
        def observe(self, *a, **kw): pass
        def time(self): return self
        def __enter__(self): return self
        def __exit__(self, *a): pass

    prediction_requests_total = _Noop()
    prediction_latency_seconds = _Noop()
    inference_errors_total = _Noop()
    chat_requests_total = _Noop()
