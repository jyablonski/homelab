from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.requests import Request
from starlette.responses import Response

# Shared HTTP metric names across every homelab app; Prometheus adds the `app`
# label from the ServiceMonitor, so names carry no service prefix.
HTTP_REQUESTS = Counter(
    "http_server_requests_total",
    "Total HTTP requests handled.",
    ("method", "route", "status"),
)

HTTP_REQUEST_DURATION = Histogram(
    "http_server_request_duration_seconds",
    "HTTP request duration in seconds.",
    ("method", "route"),
)


def metrics_endpoint(_request: Request) -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
