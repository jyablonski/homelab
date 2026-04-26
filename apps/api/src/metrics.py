from time import perf_counter

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

REQUEST_COUNT = Counter(
    "api_http_requests_total",
    "Total HTTP requests served by the API.",
    ("method", "path", "status_code"),
)

REQUEST_LATENCY = Histogram(
    "api_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ("method", "path", "status_code"),
)


def _route_path(request: Request) -> str:
    route = request.scope.get("route")
    return getattr(route, "path", "unmatched")


def setup_metrics(app: FastAPI) -> None:
    @app.middleware("http")
    async def prometheus_metrics_middleware(request: Request, call_next):
        start = perf_counter()
        response = await call_next(request)
        path = _route_path(request)
        status_code = str(response.status_code)
        REQUEST_COUNT.labels(request.method, path, status_code).inc()
        REQUEST_LATENCY.labels(request.method, path, status_code).observe(
            perf_counter() - start
        )
        return response

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
