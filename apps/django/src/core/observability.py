import logging
from collections.abc import Callable
from time import perf_counter
from uuid import uuid4

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from core.log_format import request_id_context

REQUEST_ID_HEADER = "X-Request-ID"

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

logger = logging.getLogger("core.access")


def metrics_view(_request: HttpRequest) -> HttpResponse:
    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)


def _route_template(request: HttpRequest, status: int) -> str:
    match = request.resolver_match
    if match is not None and match.route:
        return "/" + match.route
    # WhiteNoise answers static requests before URL resolution.
    if status != 404 and request.path.startswith(settings.STATIC_URL):
        return settings.STATIC_URL + "{path}"
    return "unmatched"


def _client_ip(request: HttpRequest) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", maxsplit=1)[0].strip()
    return request.META.get("REMOTE_ADDR")


class HttpObservabilityMiddleware:
    """Records one access log line and the shared HTTP metrics per request.

    Django turns view exceptions into 500 responses inside get_response (and
    logs the traceback via django.request), so this only ever sees responses.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid4())
        request_id_token = request_id_context.set(request_id)
        start = perf_counter()
        try:
            response = self.get_response(request)
            duration = perf_counter() - start
            status = response.status_code
            route = _route_template(request, status)
            HTTP_REQUESTS.labels(request.method, route, str(status)).inc()
            HTTP_REQUEST_DURATION.labels(request.method, route).observe(duration)
            response[REQUEST_ID_HEADER] = request_id
            logger.log(
                logging.ERROR if status >= 500 else logging.INFO,
                "request completed",
                extra={
                    "method": request.method,
                    "route": route,
                    "path": request.path,
                    "status": status,
                    "duration_ms": round(duration * 1000, 2),
                    "client_ip": _client_ip(request),
                },
            )
            return response
        finally:
            request_id_context.reset(request_id_token)
