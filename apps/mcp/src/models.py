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


class Reminder(BaseModel):
    id: int
    reminder_type: str
    reminder_message: str
    reminder_start_date: date
    reminder_end_date: date | None
    is_completed: bool
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ReminderListResponse(BaseModel):
    reminders: list[Reminder]
    include_completed: bool
    limit: int
    offset: int


class ActiveRemindersResponse(BaseModel):
    generated_at: datetime
    reminders: list[AgendaReminder]


class ServiceHealth(BaseModel):
    name: str
    status: Literal["healthy", "unhealthy", "unavailable"]
    status_code: int | None = None
    latency_ms: float


class ServicesHealthResponse(BaseModel):
    generated_at: datetime
    services: list[ServiceHealth]
