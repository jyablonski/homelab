from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class AgendaWindow(BaseModel):
    start: datetime
    end: datetime
    due_soon_days: int


class AgendaReminder(BaseModel):
    id: int
    type: str
    message: str
    start_date: date
    end_date: date | None
    is_completed: bool


class AgendaReminderGroups(BaseModel):
    active: list[AgendaReminder]
    due_soon: list[AgendaReminder]
    completed: list[AgendaReminder]


class AgendaEvent(BaseModel):
    id: str
    source: str
    category: str
    league: str
    title: str
    start_at: datetime
    status: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgendaFreshness(BaseModel):
    source: str
    last_success_at: datetime | None
    # TODO(events-pipeline): "placeholder" only exists for the dummy event data in
    # crud/agenda.py; drop it once real per-source freshness (nba/ufc/cs2) lands.
    status: Literal["fresh", "stale", "fetch_failed", "placeholder"]
    message: str | None = None


class EventsUpcomingResponse(BaseModel):
    generated_at: datetime
    timezone: str
    window: AgendaWindow
    events: list[AgendaEvent]
    freshness: list[AgendaFreshness]


class AgendaTodayResponse(EventsUpcomingResponse):
    reminders: AgendaReminderGroups
