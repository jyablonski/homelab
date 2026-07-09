from __future__ import annotations
import json
from dataclasses import dataclass
from datetime import datetime
from os import getenv
from typing import Any

from dagster import ConfigurableResource
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar.events.readonly"]


@dataclass(frozen=True)
class GoogleCalendarAccount:
    """One Google account/calendar pair configured for read-only sync."""

    email: str
    refresh_token: str
    calendar_id: str = "primary"
    label: str = ""


class GoogleCalendarResource(ConfigurableResource):
    """Fetches upcoming events from Google Calendar for configured accounts.

    Each account authorizes this app separately (see
    ``scripts/authorize_google_calendar.py``); a missing/blank refresh token for
    one account must not prevent the others from syncing, so account config
    parsing here never raises for an individual account's shape.
    """

    client_id: str = ""
    client_secret: str = ""
    accounts_json: str = "[]"
    request_timeout: float = 20.0

    def accounts(self) -> list[GoogleCalendarAccount]:
        raw = self.accounts_json.strip() or "[]"
        try:
            entries = json.loads(raw)
        except json.JSONDecodeError as exc:
            msg = "GOOGLE_CALENDAR_ACCOUNTS_JSON is not valid JSON"
            raise ValueError(msg) from exc

        return [
            GoogleCalendarAccount(
                email=entry["email"],
                refresh_token=entry["refresh_token"],
                calendar_id=entry.get("calendar_id") or "primary",
                label=entry.get("label") or "",
            )
            for entry in entries
        ]

    def fetch_events(
        self,
        account: GoogleCalendarAccount,
        *,
        time_min: datetime,
        time_max: datetime,
    ) -> list[dict[str, Any]]:
        """Fetch all pages of expanded events for one account/calendar window."""
        service = self._build_service(account)
        events: list[dict[str, Any]] = []
        page_token: str | None = None

        while True:
            response = (
                service.events()
                .list(
                    calendarId=account.calendar_id,
                    timeMin=_isoformat(time_min),
                    timeMax=_isoformat(time_max),
                    singleEvents=True,
                    showDeleted=True,
                    orderBy="startTime",
                    pageToken=page_token,
                )
                .execute()
            )
            events.extend(response.get("items", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return events

    def _build_service(self, account: GoogleCalendarAccount) -> Any:
        credentials = Credentials(
            token=None,
            refresh_token=account.refresh_token,
            token_uri=GOOGLE_TOKEN_URI,
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=CALENDAR_SCOPES,
        )
        return build(
            "calendar",
            "v3",
            credentials=credentials,
            cache_discovery=False,
        )


def _isoformat(value: datetime) -> str:
    return value.isoformat()


google_calendar_resource = GoogleCalendarResource(
    client_id=getenv("GOOGLE_CALENDAR_CLIENT_ID", ""),
    client_secret=getenv("GOOGLE_CALENDAR_CLIENT_SECRET", ""),
    accounts_json=getenv("GOOGLE_CALENDAR_ACCOUNTS_JSON", "[]"),
)
