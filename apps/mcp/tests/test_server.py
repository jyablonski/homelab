import json

import httpx
import pytest
from mcp.shared.memory import create_connected_server_and_client_session
from mcp.types import TextContent, TextResourceContents
from pydantic import AnyUrl

from adapters import HealthClient, HomelabApiClient
from server import ServerDependencies, create_mcp_server


def _server(
    api_handler,
    health_handler,
    settings,
):
    api_http = httpx.AsyncClient(
        base_url=str(settings.api_base_url),
        transport=httpx.MockTransport(api_handler),
    )
    health_http = httpx.AsyncClient(
        transport=httpx.MockTransport(health_handler),
    )
    dependencies = ServerDependencies(
        api=HomelabApiClient(api_http),
        health=HealthClient(health_http, settings.health_targets),
    )
    return (
        create_mcp_server(
            dependencies,
            allowed_hosts=settings.allowed_hosts,
            allowed_origins=settings.allowed_origins,
            external_url=settings.external_url,
            inbound_bearer_token=settings.inbound_bearer_token.get_secret_value(),
        ),
        api_http,
        health_http,
    )


@pytest.mark.anyio
async def test_server_discovers_only_read_tools(
    settings,
    agenda_payload: dict[str, object],
) -> None:
    server, api_http, health_http = _server(
        lambda _request: httpx.Response(200, json=agenda_payload),
        lambda _request: httpx.Response(200),
        settings,
    )
    try:
        async with create_connected_server_and_client_session(server) as session:
            result = await session.list_tools()
    finally:
        await api_http.aclose()
        await health_http.aclose()

    assert [tool.name for tool in result.tools] == [
        "agenda_today",
        "events_upcoming",
        "reminders_list",
        "reminder_get",
        "services_health",
    ]
    assert all(
        tool.annotations is not None and tool.annotations.readOnlyHint
        for tool in result.tools
    )
    assert all(
        tool.annotations is not None and tool.annotations.openWorldHint is False
        for tool in result.tools
    )


@pytest.mark.anyio
async def test_server_calls_tools_with_structured_results(
    settings,
    agenda_payload: dict[str, object],
    reminder_payload: dict[str, object],
) -> None:
    def api_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/reminders":
            return httpx.Response(200, json=[reminder_payload])
        if request.url.path.startswith("/v1/reminders/"):
            return httpx.Response(200, json=reminder_payload)
        if request.url.path == "/v1/events/upcoming":
            return httpx.Response(
                200,
                json={
                    key: value
                    for key, value in agenda_payload.items()
                    if key != "reminders"
                },
            )
        return httpx.Response(200, json=agenda_payload)

    server, api_http, health_http = _server(
        api_handler,
        lambda _request: httpx.Response(200),
        settings,
    )
    try:
        async with create_connected_server_and_client_session(server) as session:
            agenda = await session.call_tool(
                "agenda_today",
                {"hours": 24, "due_soon_days": 7},
            )
            events = await session.call_tool("events_upcoming", {"hours": 12})
            reminders = await session.call_tool(
                "reminders_list",
                {"include_completed": False, "limit": 10, "offset": 0},
            )
            reminder = await session.call_tool("reminder_get", {"reminder_id": 1})
            health = await session.call_tool("services_health")
    finally:
        await api_http.aclose()
        await health_http.aclose()

    assert agenda.structuredContent is not None
    assert events.structuredContent is not None
    assert reminders.structuredContent is not None
    assert reminder.structuredContent is not None
    assert health.structuredContent is not None
    assert agenda.structuredContent["timezone"] == "America/Los_Angeles"
    assert events.structuredContent["events"][0]["league"] == "NBA"
    assert reminders.structuredContent["limit"] == 10
    assert reminder.structuredContent["id"] == 1
    assert health.structuredContent["services"][0]["status"] == "healthy"


@pytest.mark.anyio
async def test_server_returns_safe_tool_error(
    settings,
    agenda_payload: dict[str, object],
) -> None:
    def api_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/v1/reminders/"):
            return httpx.Response(404, json={"detail": "private downstream detail"})
        return httpx.Response(200, json=agenda_payload)

    server, api_http, health_http = _server(
        api_handler,
        lambda _request: httpx.Response(200),
        settings,
    )
    try:
        async with create_connected_server_and_client_session(server) as session:
            result = await session.call_tool("reminder_get", {"reminder_id": 404})
    finally:
        await api_http.aclose()
        await health_http.aclose()

    assert result.isError is True
    content = result.content[0]
    assert isinstance(content, TextContent)
    assert content.text.endswith("reminder not found")
    assert "private downstream detail" not in content.text


@pytest.mark.anyio
async def test_server_reads_json_resources(
    settings,
    agenda_payload: dict[str, object],
) -> None:
    server, api_http, health_http = _server(
        lambda _request: httpx.Response(200, json=agenda_payload),
        lambda _request: httpx.Response(200),
        settings,
    )
    try:
        async with create_connected_server_and_client_session(server) as session:
            agenda = await session.read_resource(AnyUrl("homelab://agenda/today"))
            reminders = await session.read_resource(
                AnyUrl("homelab://reminders/active")
            )
            health = await session.read_resource(AnyUrl("homelab://services/health"))
    finally:
        await api_http.aclose()
        await health_http.aclose()

    agenda_text = agenda.contents[0]
    reminders_text = reminders.contents[0]
    health_text = health.contents[0]
    assert isinstance(agenda_text, TextResourceContents)
    assert isinstance(reminders_text, TextResourceContents)
    assert isinstance(health_text, TextResourceContents)
    agenda_content = json.loads(agenda_text.text)
    reminders_content = json.loads(reminders_text.text)
    health_content = json.loads(health_text.text)
    assert agenda_content["timezone"] == "America/Los_Angeles"
    assert reminders_content["reminders"][0]["message"] == "Replace filter"
    assert health_content["services"][0]["name"] == "api"
