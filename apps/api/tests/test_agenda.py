from datetime import date, datetime
from zoneinfo import ZoneInfo

from crud import agenda
from database import get_session
from database_models.reminder import ReminderRow

LA_TZ = ZoneInfo("America/Los_Angeles")


def test_today_agenda_returns_frontend_contract(reminders_table, postgres_settings):
    now = datetime(2026, 7, 3, 9, 0, tzinfo=LA_TZ)
    with get_session(postgres_settings) as session:
        session.add(
            ReminderRow(
                reminder_type="car",
                reminder_message="Get oil changed soon",
                reminder_start_date=date(2026, 7, 3),
            )
        )
        session.add(
            ReminderRow(
                reminder_type="house",
                reminder_message="Change water filter",
                reminder_start_date=date(2026, 7, 3),
                is_completed=True,
                completed_at=now,
            )
        )
        session.commit()

        payload = agenda.get_today_agenda(session=session, now=now)

    serialized = payload.model_dump(mode="json")
    assert serialized["timezone"] == "America/Los_Angeles"
    assert serialized["window"]["due_soon_days"] == 7
    assert serialized["reminders"]["active"][0]["message"] == "Get oil changed soon"
    assert serialized["reminders"]["active"][0]["type"] == "car"
    assert serialized["reminders"]["completed"][0]["message"] == "Change water filter"
    assert serialized["events"][0]["source"] == "dummy"
    assert serialized["events"][0]["metadata"]["venue"] == "Chase Center"
    assert serialized["freshness"][0]["source"] == "events_gold"
    assert serialized["freshness"][0]["status"] == "placeholder"


def test_upcoming_events_returns_dummy_contract():
    response = agenda.get_upcoming_events(
        hours=24,
        now=datetime(2026, 7, 3, 9, 0, tzinfo=LA_TZ),
    )

    assert response.timezone == "America/Los_Angeles"
    assert response.window.start.isoformat() == "2026-07-03T09:00:00-07:00"
    assert response.window.end.isoformat() == "2026-07-04T09:00:00-07:00"
    assert response.events[0].id == "dummy:nba:2026-07-03"
    assert response.events[0].start_at.isoformat() == "2026-07-03T12:00:00-07:00"
    assert response.freshness[0].status == "placeholder"


def test_today_agenda_groups_active_and_due_soon_without_duplicates(
    reminders_table,
    postgres_settings,
):
    now = datetime(2026, 7, 3, 9, 0, tzinfo=LA_TZ)
    with get_session(postgres_settings) as session:
        session.add(
            ReminderRow(
                reminder_type="car",
                reminder_message="Oil change",
                reminder_start_date=date(2026, 7, 3),
            )
        )
        session.add(
            ReminderRow(
                reminder_type="house",
                reminder_message="Filter change",
                reminder_start_date=date(2026, 7, 8),
            )
        )
        session.add(
            ReminderRow(
                reminder_type="house",
                reminder_message="Too far away",
                reminder_start_date=date(2026, 7, 20),
            )
        )
        session.commit()

        payload = agenda.get_today_agenda(session=session, now=now)

    assert [reminder.message for reminder in payload.reminders.active] == ["Oil change"]
    assert [reminder.message for reminder in payload.reminders.due_soon] == [
        "Filter change"
    ]
