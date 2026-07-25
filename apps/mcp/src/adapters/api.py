from typing import Any

import httpx
from pydantic import BaseModel, TypeAdapter, ValidationError

from errors import (
    DownstreamRejectedError,
    DownstreamResponseError,
    DownstreamUnavailableError,
    ResourceNotFoundError,
)
from models import AgendaTodayResponse, EventsUpcomingResponse, Reminder

REMINDER_LIST_ADAPTER = TypeAdapter(list[Reminder])


class HomelabApiClient:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def get_agenda(
        self,
        *,
        hours: int,
        due_soon_days: int,
    ) -> AgendaTodayResponse:
        payload = await self._get_json(
            "/v1/agenda/today",
            params={"hours": hours, "due_soon_days": due_soon_days},
            operation="agenda",
        )
        return self._validate_model(
            AgendaTodayResponse,
            payload,
            operation="agenda",
        )

    async def get_upcoming_events(self, *, hours: int) -> EventsUpcomingResponse:
        payload = await self._get_json(
            "/v1/events/upcoming",
            params={"hours": hours},
            operation="upcoming events",
        )
        return self._validate_model(
            EventsUpcomingResponse,
            payload,
            operation="upcoming events",
        )

    async def list_reminders(
        self,
        *,
        include_completed: bool,
        limit: int,
        offset: int,
    ) -> list[Reminder]:
        payload = await self._get_json(
            "/v1/reminders",
            params={
                "include_completed": include_completed,
                "limit": limit,
                "offset": offset,
            },
            operation="reminder list",
        )
        try:
            return REMINDER_LIST_ADAPTER.validate_python(payload)
        except ValidationError:
            raise DownstreamResponseError(
                "Homelab API returned an invalid reminder list"
            ) from None

    async def get_reminder(self, reminder_id: int) -> Reminder:
        payload = await self._get_json(
            f"/v1/reminders/{reminder_id}",
            operation="reminder",
            not_found_message="reminder not found",
        )
        return self._validate_model(Reminder, payload, operation="reminder")

    async def _get_json(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        operation: str,
        not_found_message: str | None = None,
    ) -> object:
        try:
            response = await self.client.get(path, params=params)
        except httpx.RequestError:
            raise DownstreamUnavailableError(
                f"Homelab API is unavailable while reading {operation}"
            ) from None

        if response.status_code in {401, 403}:
            raise DownstreamRejectedError(
                "Homelab API rejected the MCP service credential"
            )
        if response.status_code == 404 and not_found_message:
            raise ResourceNotFoundError(not_found_message)
        if not response.is_success:
            raise DownstreamResponseError(f"Homelab API could not return {operation}")

        try:
            return response.json()
        except ValueError:
            raise DownstreamResponseError(
                f"Homelab API returned invalid JSON for {operation}"
            ) from None

    @staticmethod
    def _validate_model[ModelT: BaseModel](
        model: type[ModelT],
        payload: object,
        *,
        operation: str,
    ) -> ModelT:
        try:
            return model.model_validate(payload)
        except ValidationError:
            raise DownstreamResponseError(
                f"Homelab API returned an invalid {operation} response"
            ) from None
