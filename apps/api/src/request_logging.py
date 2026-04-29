import logging
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request

from log_context import request_id_context

REQUEST_ID_HEADER = "X-Request-ID"

logger = logging.getLogger("api.access")


def _route_path(request: Request) -> str:
    route = request.scope.get("route")
    return getattr(route, "path", "unmatched")


def _client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", maxsplit=1)[0].strip()

    return request.client.host if request.client else None


def setup_request_logging(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        start = perf_counter()
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid4())
        request_id_token = request_id_context.set(request_id)

        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "route": _route_path(request),
                    "client_ip": _client_ip(request),
                    "duration_ms": round((perf_counter() - start) * 1000, 2),
                },
            )
            raise
        else:
            response.headers[REQUEST_ID_HEADER] = request_id
            logger.info(
                "request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "route": _route_path(request),
                    "status_code": response.status_code,
                    "client_ip": _client_ip(request),
                    "duration_ms": round((perf_counter() - start) * 1000, 2),
                },
            )
            return response
        finally:
            request_id_context.reset(request_id_token)
