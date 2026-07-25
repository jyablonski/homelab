from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from adapters import HealthClient, HomelabApiClient
from config import Settings, get_settings
from http_observability import HttpObservabilityMiddleware
from logging_config import configure_logging
from server import ServerDependencies, create_mcp_server
from version import __version__


def create_app(
    settings: Settings | None = None,
    *,
    api_transport: httpx.AsyncBaseTransport | None = None,
    health_transport: httpx.AsyncBaseTransport | None = None,
) -> Starlette:
    active_settings = settings or get_settings()
    configure_logging(active_settings)

    api_key = active_settings.api_key.get_secret_value()
    api_headers = {
        "User-Agent": f"homelab-mcp/{__version__}",
    }
    if api_key:
        api_headers["X-Homelab-Api-Key"] = api_key

    api_http_client = httpx.AsyncClient(
        base_url=str(active_settings.api_base_url),
        headers=api_headers,
        timeout=active_settings.request_timeout_seconds,
        transport=api_transport,
        trust_env=False,
    )
    health_http_client = httpx.AsyncClient(
        headers={"User-Agent": f"homelab-mcp/{__version__}"},
        timeout=active_settings.request_timeout_seconds,
        transport=health_transport,
        trust_env=False,
    )
    dependencies = ServerDependencies(
        api=HomelabApiClient(api_http_client),
        health=HealthClient(
            health_http_client,
            targets=active_settings.health_targets,
        ),
    )
    mcp = create_mcp_server(
        dependencies,
        name=active_settings.app_name,
        allowed_hosts=active_settings.allowed_hosts,
        allowed_origins=active_settings.allowed_origins,
        external_url=active_settings.external_url,
        inbound_bearer_token=active_settings.inbound_bearer_token.get_secret_value(),
    )

    @asynccontextmanager
    async def lifespan(_app: Starlette) -> AsyncIterator[None]:
        try:
            async with mcp.session_manager.run():
                yield
        finally:
            await api_http_client.aclose()
            await health_http_client.aclose()

    async def root(_request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "name": active_settings.app_name,
                "environment": active_settings.environment,
                "version": __version__,
                "mcp_endpoint": "/mcp",
                "read_only": True,
            }
        )

    async def healthz(_request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    async def readyz(_request: Request) -> JSONResponse:
        return JSONResponse({"status": "ready"})

    async def metrics(_request: Request) -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    app = Starlette(
        routes=[
            Route("/", root),
            Route("/healthz", healthz),
            Route("/readyz", readyz),
            Route("/metrics", metrics),
            Mount("/", app=mcp.streamable_http_app()),
        ],
        middleware=[Middleware(HttpObservabilityMiddleware)],
        lifespan=lifespan,
    )
    app.state.mcp_server = mcp
    app.state.dependencies = dependencies
    return app


app = create_app()
