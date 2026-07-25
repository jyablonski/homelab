import asyncio
from datetime import UTC, datetime
from time import perf_counter

import httpx
from pydantic import AnyHttpUrl

from models import ServiceHealth, ServicesHealthResponse


class HealthClient:
    def __init__(
        self,
        client: httpx.AsyncClient,
        targets: dict[str, AnyHttpUrl],
    ) -> None:
        self.client = client
        self.targets = targets

    async def check_all(self) -> ServicesHealthResponse:
        services = await asyncio.gather(
            *(
                self._check_target(name=name, url=str(url))
                for name, url in sorted(self.targets.items())
            )
        )
        return ServicesHealthResponse(
            generated_at=datetime.now(UTC),
            services=list(services),
        )

    async def _check_target(self, *, name: str, url: str) -> ServiceHealth:
        start = perf_counter()
        try:
            response = await self.client.get(url)
        except httpx.RequestError:
            return ServiceHealth(
                name=name,
                status="unavailable",
                latency_ms=_latency_ms(start),
            )
        return ServiceHealth(
            name=name,
            status="healthy" if response.is_success else "unhealthy",
            status_code=response.status_code,
            latency_ms=_latency_ms(start),
        )


def _latency_ms(start: float) -> float:
    return round((perf_counter() - start) * 1000, 2)
