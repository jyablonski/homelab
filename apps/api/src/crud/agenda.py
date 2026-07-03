from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from api_models.agenda import (
    AgendaEvent,
    AgendaFreshness,
    AgendaReminder,
    AgendaReminderGroups,
    AgendaTodayResponse,
    AgendaWindow,
    EventsUpcomingResponse,
)
from database_models.reminder import ReminderRow

AGENDA_TIMEZONE = "America/Los_Angeles"
DEFAULT_DUE_SOON_DAYS = 7
DEFAULT_EVENT_HOURS = 24
LA_TZ = ZoneInfo(AGENDA_TIMEZONE)


def get_today_agenda(
    *,
    session: Session,
    hours: int = DEFAULT_EVENT_HOURS,
    due_soon_days: int = DEFAULT_DUE_SOON_DAYS,
    now: datetime | None = None,
) -> AgendaTodayResponse:
    generated_at = _local_now(now)
    today = generated_at.date()
    window = _window(generated_at, hours=hours, due_soon_days=due_soon_days)
    return AgendaTodayResponse(
        generated_at=generated_at,
        timezone=AGENDA_TIMEZONE,
        window=window,
        reminders=_reminder_groups(
            session=session,
            today=today,
            due_soon_days=due_soon_days,
        ),
        events=_dummy_events(generated_at, window=window),
        freshness=_dummy_freshness(generated_at),
    )


def get_upcoming_events(
    *,
    hours: int = DEFAULT_EVENT_HOURS,
    due_soon_days: int = DEFAULT_DUE_SOON_DAYS,
    now: datetime | None = None,
) -> EventsUpcomingResponse:
    generated_at = _local_now(now)
    window = _window(generated_at, hours=hours, due_soon_days=due_soon_days)
    return EventsUpcomingResponse(
        generated_at=generated_at,
        timezone=AGENDA_TIMEZONE,
        window=window,
        events=_dummy_events(generated_at, window=window),
        freshness=_dummy_freshness(generated_at),
    )


def _reminder_groups(
    *,
    session: Session,
    today: date,
    due_soon_days: int,
) -> AgendaReminderGroups:
    due_soon_end = today + timedelta(days=due_soon_days)

    active_statement = (
        select(ReminderRow)
        .where(ReminderRow.is_completed.is_(False))
        .where(ReminderRow.reminder_start_date <= today)
        .where(
            (ReminderRow.reminder_end_date.is_(None))
            | (ReminderRow.reminder_end_date >= today)
        )
        .order_by(ReminderRow.reminder_start_date.asc(), ReminderRow.id.asc())
    )
    due_soon_statement = (
        select(ReminderRow)
        .where(ReminderRow.is_completed.is_(False))
        .where(ReminderRow.reminder_start_date > today)
        .where(ReminderRow.reminder_start_date <= due_soon_end)
        .order_by(ReminderRow.reminder_start_date.asc(), ReminderRow.id.asc())
    )
    completed_statement = (
        select(ReminderRow)
        .where(ReminderRow.is_completed.is_(True))
        .order_by(ReminderRow.completed_at.desc(), ReminderRow.id.asc())
        .limit(25)
    )

    return AgendaReminderGroups(
        active=_serialize_reminders(session, active_statement),
        due_soon=_serialize_reminders(session, due_soon_statement),
        completed=_serialize_reminders(session, completed_statement),
    )


def _serialize_reminders(
    session: Session,
    statement: Select[tuple[ReminderRow]],
) -> list[AgendaReminder]:
    return [_agenda_reminder(row) for row in session.scalars(statement).all()]


def _agenda_reminder(row: ReminderRow) -> AgendaReminder:
    return AgendaReminder(
        id=row.id,
        type=row.reminder_type,
        message=row.reminder_message,
        start_date=row.reminder_start_date,
        end_date=row.reminder_end_date,
        is_completed=row.is_completed,
    )


def _window(
    generated_at: datetime,
    *,
    hours: int,
    due_soon_days: int,
) -> AgendaWindow:
    return AgendaWindow(
        start=generated_at,
        end=generated_at + timedelta(hours=hours),
        due_soon_days=due_soon_days,
    )


def _dummy_events(
    generated_at: datetime,
    *,
    window: AgendaWindow,
) -> list[AgendaEvent]:
    events = [
        AgendaEvent(
            id=f"dummy:nba:{generated_at.date().isoformat()}",
            source="dummy",
            category="sports",
            league="NBA",
            title="Dummy NBA game",
            start_at=generated_at + timedelta(hours=3),
            status="scheduled",
            metadata={
                "home_team": "Golden State Warriors",
                "away_team": "Los Angeles Lakers",
                "venue": "Chase Center",
            },
        ),
        AgendaEvent(
            id=f"dummy:ufc:{generated_at.date().isoformat()}",
            source="dummy",
            category="sports",
            league="UFC",
            title="Dummy UFC Fight Night",
            start_at=generated_at + timedelta(hours=8),
            status="scheduled",
            metadata={
                "location": "Las Vegas, NV",
                "source_note": "Placeholder until dbt gold event views exist",
            },
        ),
    ]
    return [event for event in events if window.start <= event.start_at <= window.end]


def _dummy_freshness(generated_at: datetime) -> list[AgendaFreshness]:
    return [
        AgendaFreshness(
            source="events_gold",
            last_success_at=None,
            status="placeholder",
            message=("Dummy event data until dbt silver/gold event models are built."),
        ),
        AgendaFreshness(
            source="dummy",
            last_success_at=generated_at,
            status="fresh",
            message=None,
        ),
    ]


def _local_now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(LA_TZ)
    if now.tzinfo is None:
        return now.replace(tzinfo=LA_TZ)
    return now.astimezone(LA_TZ)
