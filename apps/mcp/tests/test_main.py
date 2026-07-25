import httpx
import pytest
from pydantic import AnyHttpUrl, SecretStr

from main import create_app

INITIALIZE_REQUEST = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "test-client", "version": "1"},
    },
}


@pytest.mark.anyio
async def test_http_metadata_health_and_metrics(
    settings,
    agenda_payload: dict[str, object],
) -> None:
    api_transport = httpx.MockTransport(
        lambda _request: httpx.Response(200, json=agenda_payload)
    )
    health_transport = httpx.MockTransport(lambda _request: httpx.Response(200))
    app = create_app(
        settings,
        api_transport=api_transport,
        health_transport=health_transport,
    )

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            root = await client.get(
                "/",
                headers={"X-Request-ID": "test-request"},
            )
            health = await client.get("/healthz")
            ready = await client.get("/readyz")
            metrics = await client.get("/metrics")
            missing = await client.get("/missing")

    assert root.status_code == 200
    assert root.headers["X-Request-ID"] == "test-request"
    assert root.json()["mcp_endpoint"] == "/mcp"
    assert root.json()["read_only"] is True
    assert health.json() == {"status": "ok"}
    assert ready.json() == {"status": "ready"}
    assert "mcp_http_requests_total" in metrics.text
    assert missing.status_code == 404


@pytest.mark.anyio
async def test_app_sends_api_key_without_exposing_it(
    settings,
    agenda_payload: dict[str, object],
) -> None:
    observed_headers: list[httpx.Headers] = []

    def api_handler(request: httpx.Request) -> httpx.Response:
        observed_headers.append(request.headers)
        return httpx.Response(200, json=agenda_payload)

    app = create_app(
        settings,
        api_transport=httpx.MockTransport(api_handler),
        health_transport=httpx.MockTransport(lambda _request: httpx.Response(200)),
    )

    api_client = app.state.dependencies.api
    health_client = app.state.dependencies.health
    try:
        agenda = await api_client.get_agenda(hours=24, due_soon_days=7)
    finally:
        await api_client.client.aclose()
        await health_client.client.aclose()

    assert agenda.timezone == "America/Los_Angeles"
    assert observed_headers[0]["X-Homelab-Api-Key"] == "test-api-key"


@pytest.mark.anyio
async def test_mcp_transport_accepts_configured_ingress_host(settings) -> None:
    app = create_app(
        settings.model_copy(
            update={
                "allowed_hosts": ["mcp.home"],
                "allowed_origins": ["http://mcp.home"],
            }
        ),
        api_transport=httpx.MockTransport(lambda _request: httpx.Response(200)),
        health_transport=httpx.MockTransport(lambda _request: httpx.Response(200)),
    )

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://mcp.home",
        ) as client:
            accepted = await client.post(
                "/mcp",
                json=INITIALIZE_REQUEST,
                headers={"Accept": "application/json, text/event-stream"},
            )
            rejected = await client.post(
                "http://untrusted.home/mcp",
                json=INITIALIZE_REQUEST,
                headers={"Accept": "application/json, text/event-stream"},
            )

    assert accepted.status_code == 200
    assert accepted.json()["result"]["serverInfo"]["name"] == "Homelab MCP"
    assert rejected.status_code == 421


@pytest.mark.anyio
async def test_mcp_transport_requires_configured_bearer_token(settings) -> None:
    inbound_token = "test-inbound-token-that-is-long-enough"
    app = create_app(
        settings.model_copy(
            update={
                "allowed_hosts": ["mcp.home"],
                "allowed_origins": ["http://mcp.home"],
                "external_url": AnyHttpUrl("http://mcp.home/mcp"),
                "inbound_bearer_token": SecretStr(inbound_token),
                "require_inbound_auth": True,
            }
        ),
        api_transport=httpx.MockTransport(lambda _request: httpx.Response(200)),
        health_transport=httpx.MockTransport(lambda _request: httpx.Response(200)),
    )

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://mcp.home",
        ) as client:
            health = await client.get("/healthz")
            missing = await client.post(
                "/mcp",
                json=INITIALIZE_REQUEST,
                headers={"Accept": "application/json, text/event-stream"},
            )
            invalid = await client.post(
                "/mcp",
                json=INITIALIZE_REQUEST,
                headers={
                    "Accept": "application/json, text/event-stream",
                    "Authorization": "Bearer invalid-token",
                },
            )
            accepted = await client.post(
                "/mcp",
                json=INITIALIZE_REQUEST,
                headers={
                    "Accept": "application/json, text/event-stream",
                    "Authorization": f"Bearer {inbound_token}",
                },
            )

    assert health.status_code == 200
    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert accepted.status_code == 200
    assert accepted.json()["result"]["serverInfo"]["name"] == "Homelab MCP"
