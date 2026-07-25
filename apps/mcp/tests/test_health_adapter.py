import httpx
import pytest
from pydantic import AnyHttpUrl

from adapters import HealthClient


@pytest.mark.anyio
async def test_health_client_summarizes_allowlisted_targets() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.test":
            return httpx.Response(200)
        if request.url.host == "runner.test":
            return httpx.Response(503)
        raise httpx.ConnectError("connection failed", request=request)

    targets = {
        "runner": AnyHttpUrl("http://runner.test/healthz"),
        "missing": AnyHttpUrl("http://missing.test/healthz"),
        "api": AnyHttpUrl("http://api.test/healthz"),
    }
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    ) as http_client:
        result = await HealthClient(http_client, targets).check_all()

    assert [service.name for service in result.services] == [
        "api",
        "missing",
        "runner",
    ]
    assert [service.status for service in result.services] == [
        "healthy",
        "unavailable",
        "unhealthy",
    ]
    assert result.services[0].status_code == 200
    assert result.services[1].status_code is None
    assert result.services[2].status_code == 503
