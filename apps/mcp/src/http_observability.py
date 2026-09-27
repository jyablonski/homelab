import logging
from time import perf_counter
from typing import Any
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from log_context import request_id_context
from metrics import HTTP_REQUEST_DURATION, HTTP_REQUESTS

REQUEST_ID_HEADER = "X-Request-ID"
logger = logging.getLogger("mcp.access")


class HttpObservabilityMiddleware:
    """Records one access log line and the shared HTTP metrics per request.

    Plain ASGI middleware so unhandled exceptions are still counted as 500s
    before Starlette's error handler turns them into a response.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        request_id = headers.get(REQUEST_ID_HEADER) or str(uuid4())
        request_id_token = request_id_context.set(request_id)
        start = perf_counter()
        status = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                MutableHeaders(scope=message).append(REQUEST_ID_HEADER, request_id)
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception:
            logger.exception(
                "request failed", extra=_observe(scope, headers, 500, start)
            )
            raise
        else:
            fields = _observe(scope, headers, status, start)
            if status >= 500:
                logger.error("request completed", extra=fields)
            else:
                logger.info("request completed", extra=fields)
        finally:
            request_id_context.reset(request_id_token)


def _observe(
    scope: Scope, headers: Headers, status: int, start: float
) -> dict[str, Any]:
    duration = perf_counter() - start
    method = scope["method"]
    route = _route_template(scope["path"], status)
    HTTP_REQUESTS.labels(method, route, str(status)).inc()
    HTTP_REQUEST_DURATION.labels(method, route).observe(duration)
    return {
        "method": method,
        "route": route,
        "path": scope["path"],
        "status": status,
        "duration_ms": round(duration * 1000, 2),
        "client_ip": _client_ip(headers, scope),
    }


def _route_template(path: str, status: int) -> str:
    # The MCP app is mounted at "/", so Starlette matches every path; map
    # explicitly and collapse the rest to keep metric cardinality bounded.
    if status == 404:
        return "unmatched"
    if path == "/mcp" or path.startswith("/mcp/"):
        return "/mcp"
    if path in {"/", "/healthz", "/readyz", "/metrics"}:
        return path
    return "unmatched"


def _client_ip(headers: Headers, scope: Scope) -> str | None:
    forwarded_for = headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", maxsplit=1)[0].strip()

    client = scope.get("client")
    return client[0] if client else None
