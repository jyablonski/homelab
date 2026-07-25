import logging
from time import perf_counter
from uuid import uuid4

from starlette.requests import Request
from starlette.types import ASGIApp

from log_context import request_id_context
from metrics import HTTP_REQUEST_DURATION, HTTP_REQUESTS

REQUEST_ID_HEADER = "X-Request-ID"
logger = logging.getLogger("mcp.http")


class HttpObservabilityMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid4())
        request_id_token = request_id_context.set(request_id)
        path = _metric_path(request.url.path)
        start = perf_counter()
        status_code = 500

        async def send_with_request_id(message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = list(message.get("headers", []))
                headers.append(
                    (REQUEST_ID_HEADER.lower().encode(), request_id.encode())
                )
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception:
            logger.exception(
                "request failed",
                extra={
                    "method": request.method,
                    "path": path,
                    "duration_ms": round((perf_counter() - start) * 1000, 2),
                },
            )
            raise
        else:
            logger.info(
                "request completed",
                extra={
                    "method": request.method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": round((perf_counter() - start) * 1000, 2),
                },
            )
        finally:
            status = str(status_code)
            HTTP_REQUESTS.labels(request.method, path, status).inc()
            HTTP_REQUEST_DURATION.labels(request.method, path, status).observe(
                perf_counter() - start
            )
            request_id_context.reset(request_id_token)


def _metric_path(path: str) -> str:
    if path == "/mcp" or path.startswith("/mcp/"):
        return "/mcp"
    if path in {"/", "/healthz", "/readyz", "/metrics"}:
        return path
    return "unmatched"
