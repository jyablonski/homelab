import httpx
import pytest

from adapters import HomelabApiClient
from errors import (
    DownstreamRejectedError,
    DownstreamResponseError,
    DownstreamUnavailableError,
    ResourceNotFoundError,
)


@pytest.mark.anyio
async def test_api_adapter_returns_typed_models_and_bounded_params(
    agenda_payload: dict[str, object],
    reminder_payload: dict[str, object],
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/v1/agenda/today":
            return httpx.Response(200, json=agenda_payload)
        if request.url.path == "/v1/events/upcoming":
            events = {
                key: value
                for key, value in agenda_payload.items()
                if key != "reminders"
            }
            return httpx.Response(200, json=events)
        if request.url.path == "/v1/reminders":
            return httpx.Response(200, json=[reminder_payload])
        return httpx.Response(200, json=reminder_payload)

    async with httpx.AsyncClient(
        base_url="http://api.test",
        transport=httpx.MockTransport(handler),
    ) as http_client:
        client = HomelabApiClient(http_client)

        agenda = await client.get_agenda(hours=48, due_soon_days=10)
        events = await client.get_upcoming_events(hours=12)
        reminders = await client.list_reminders(
            include_completed=True,
            limit=25,
            offset=5,
        )
        reminder = await client.get_reminder(1)

    assert agenda.reminders.active[0].message == "Replace filter"
    assert events.events[0].league == "NBA"
    assert reminders[0].reminder_type == "maintenance"
    assert reminder.id == 1
    assert str(requests[0].url.params) == "hours=48&due_soon_days=10"
    assert str(requests[1].url.params) == "hours=12"
    assert str(requests[2].url.params) == ("include_completed=true&limit=25&offset=5")


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("status_code", "error_type", "message"),
    [
        (401, DownstreamRejectedError, "rejected"),
        (403, DownstreamRejectedError, "rejected"),
        (500, DownstreamResponseError, "could not return reminder"),
    ],
)
async def test_api_adapter_maps_http_failures(
    status_code: int,
    error_type: type[Exception],
    message: str,
) -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(status_code, json={"detail": "private"})
    )
    async with httpx.AsyncClient(
        base_url="http://api.test",
        transport=transport,
    ) as http_client:
        client = HomelabApiClient(http_client)

        with pytest.raises(error_type, match=message):
            await client.get_reminder(1)


@pytest.mark.anyio
async def test_api_adapter_maps_not_found() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(404, json={"detail": "private"})
    )
    async with httpx.AsyncClient(
        base_url="http://api.test",
        transport=transport,
    ) as http_client:
        with pytest.raises(ResourceNotFoundError, match="reminder not found"):
            await HomelabApiClient(http_client).get_reminder(42)


@pytest.mark.anyio
async def test_api_adapter_maps_unavailable_service() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("private connection detail", request=request)

    async with httpx.AsyncClient(
        base_url="http://api.test",
        transport=httpx.MockTransport(handler),
    ) as http_client:
        with pytest.raises(DownstreamUnavailableError, match="unavailable"):
            await HomelabApiClient(http_client).get_upcoming_events(hours=24)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="not-json"),
        httpx.Response(200, json={"unexpected": "shape"}),
    ],
)
async def test_api_adapter_rejects_invalid_responses(
    response: httpx.Response,
) -> None:
    transport = httpx.MockTransport(lambda _request: response)
    async with httpx.AsyncClient(
        base_url="http://api.test",
        transport=transport,
    ) as http_client:
        with pytest.raises(DownstreamResponseError, match="invalid"):
            await HomelabApiClient(http_client).get_upcoming_events(hours=24)


@pytest.mark.anyio
async def test_api_adapter_rejects_invalid_reminder_list() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(200, json={"not": "a list"})
    )
    async with httpx.AsyncClient(
        base_url="http://api.test",
        transport=transport,
    ) as http_client:
        with pytest.raises(DownstreamResponseError, match="invalid reminder list"):
            await HomelabApiClient(http_client).list_reminders(
                include_completed=False,
                limit=100,
                offset=0,
            )
