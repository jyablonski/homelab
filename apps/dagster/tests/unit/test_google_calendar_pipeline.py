from __future__ import annotations
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import cast

import polars as pl
import pytest
from dagster import materialize

from dagster_project.common.docs import load_doc
from dagster_project.defs.assets.ingestion.events_google_calendar import (
    _event_to_row,
    _mark_stale_rows,
    events_google_calendar,
)
from dagster_project.defs.jobs.calendar import calendar_sync_job, calendar_sync_schedule
from dagster_project.resources.google_calendar import GoogleCalendarAccount
from dagster_project.resources.postgres import PostgresResource

pytestmark = pytest.mark.unit

ACCOUNT = GoogleCalendarAccount(
    email="jyablonski9@gmail.com",
    refresh_token="rt",
    calendar_id="primary",
    label="personal",
)
NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_event_to_row_parses_timed_event():
    event = {
        "id": "abc123",
        "summary": "Team planning",
        "status": "confirmed",
        "start": {"dateTime": "2026-01-02T10:00:00-08:00"},
        "end": {"dateTime": "2026-01-02T11:00:00-08:00"},
        "htmlLink": "https://calendar.google.com/abc123",
    }
    row = _event_to_row(event, account=ACCOUNT, seen_at=NOW)
    assert row is not None
    assert row["source_event_id"] == "abc123"
    assert row["source_instance_id"] == "abc123"
    assert row["event_name"] == "Team planning"
    assert row["is_all_day"] is False
    assert row["account_email"] == "jyablonski9@gmail.com"
    assert row["calendar_summary"] == "personal"


def test_event_to_row_parses_all_day_event():
    event = {
        "id": "allday1",
        "summary": "Company holiday",
        "status": "confirmed",
        "start": {"date": "2026-01-05"},
        "end": {"date": "2026-01-06"},
    }
    row = _event_to_row(event, account=ACCOUNT, seen_at=NOW)
    assert row is not None
    assert row["is_all_day"] is True
    assert row["event_start"] == datetime(2026, 1, 5, tzinfo=UTC)


def test_event_to_row_parses_recurring_expanded_instance():
    event = {
        "id": "series1_20260102T100000Z",
        "recurringEventId": "series1",
        "summary": "Standup",
        "status": "confirmed",
        "start": {"dateTime": "2026-01-02T10:00:00Z"},
        "end": {"dateTime": "2026-01-02T10:15:00Z"},
    }
    row = _event_to_row(event, account=ACCOUNT, seen_at=NOW)
    assert row is not None
    assert row["source_event_id"] == "series1"
    assert row["source_instance_id"] == "series1_20260102T100000Z"


def test_event_to_row_keeps_cancelled_events():
    event = {
        "id": "cancelled1",
        "status": "cancelled",
        "start": {"dateTime": "2026-01-02T10:00:00Z"},
    }
    row = _event_to_row(event, account=ACCOUNT, seen_at=NOW)
    assert row is not None
    assert row["status"] == "cancelled"


def test_event_to_row_defaults_missing_summary_to_busy():
    event = {"id": "e1", "start": {"dateTime": "2026-01-02T10:00:00Z"}}
    row = _event_to_row(event, account=ACCOUNT, seen_at=NOW)
    assert row is not None
    assert row["event_name"] == "Busy"


def test_event_to_row_skips_missing_start():
    assert _event_to_row({"id": "e1"}, account=ACCOUNT, seen_at=NOW) is None
    assert (
        _event_to_row({"id": "e1", "start": {}}, account=ACCOUNT, seen_at=NOW) is None
    )


def test_event_to_row_skips_invalid_all_day_date():
    event = {"id": "e1", "start": {"date": "not-a-date"}}
    assert _event_to_row(event, account=ACCOUNT, seen_at=NOW) is None


def test_event_to_row_skips_missing_id():
    event = {"start": {"dateTime": "2026-01-02T10:00:00Z"}}
    assert _event_to_row(event, account=ACCOUNT, seen_at=NOW) is None


def test_event_to_row_labels_work_and_personal_accounts():
    work = GoogleCalendarAccount(
        email="jacob.yablonski@axios.com",
        refresh_token="rt",
        calendar_id="primary",
        label="work",
    )
    event = {"id": "e1", "start": {"dateTime": "2026-01-02T10:00:00Z"}}
    personal_row = _event_to_row(event, account=ACCOUNT, seen_at=NOW)
    work_row = _event_to_row(event, account=work, seen_at=NOW)
    assert personal_row is not None
    assert work_row is not None
    assert personal_row["account_email"] == "jyablonski9@gmail.com"
    assert work_row["account_email"] == "jacob.yablonski@axios.com"


class _FakeCursor:
    def __init__(self, rowcount: int):
        self.rowcount = rowcount
        self.executed: list[tuple] = []

    def execute(self, query, params):
        self.executed.append((query, params))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeConnection:
    def __init__(self, cursor: _FakeCursor):
        self._cursor = cursor
        self.committed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True


class _FakePostgres:
    def __init__(self, *, stale_rowcount: int = 0):
        self.merged_frames: list[pl.DataFrame] = []
        self.cursor = _FakeCursor(stale_rowcount)
        self._conn = _FakeConnection(self.cursor)

    def merge_polars(self, df, **_kwargs):
        self.merged_frames.append(df)
        return df.height

    @contextmanager
    def connection(self):
        yield self._conn

    def fetch_value(self, query, *_args):
        return None


class _FakeGoogleCalendar:
    def __init__(self, events_by_email: dict[str, list[dict]], accounts=None):
        self._events_by_email = events_by_email
        self._accounts = accounts if accounts is not None else [ACCOUNT]

    def accounts(self):
        return self._accounts

    def fetch_events(self, account, *, time_min, time_max):
        events = self._events_by_email.get(account.email)
        if events is None:
            raise RuntimeError(f"boom for {account.email}")
        return events


def test_events_google_calendar_materializes_with_fake_resources():
    events = {
        ACCOUNT.email: [
            {
                "id": "e1",
                "summary": "Meeting",
                "start": {"dateTime": "2026-01-02T10:00:00Z"},
            }
        ]
    }
    postgres = _FakePostgres()
    result = materialize(
        [events_google_calendar],
        resources={
            "google_calendar": _FakeGoogleCalendar(events),
            "postgres": postgres,
        },
    )
    assert result.success
    assert result.output_for_node("events_google_calendar") == 1
    assert postgres.merged_frames[0].height == 1


def test_events_google_calendar_skips_events_with_missing_start():
    events = {ACCOUNT.email: [{"id": "e1", "summary": "No start"}]}
    postgres = _FakePostgres()
    result = materialize(
        [events_google_calendar],
        resources={
            "google_calendar": _FakeGoogleCalendar(events),
            "postgres": postgres,
        },
    )
    assert result.success
    assert result.output_for_node("events_google_calendar") == 0
    assert postgres.merged_frames[0].is_empty()


def test_events_google_calendar_continues_when_one_account_fails():
    work = GoogleCalendarAccount(
        email="jacob.yablonski@axios.com", refresh_token="rt", label="work"
    )
    events = {
        ACCOUNT.email: [
            {
                "id": "e1",
                "summary": "Personal",
                "start": {"dateTime": "2026-01-02T10:00:00Z"},
            }
        ]
        # work account intentionally missing -> fetch_events raises for it
    }
    postgres = _FakePostgres()
    result = materialize(
        [events_google_calendar],
        resources={
            "google_calendar": _FakeGoogleCalendar(events, accounts=[ACCOUNT, work]),
            "postgres": postgres,
        },
    )
    assert result.success
    assert result.output_for_node("events_google_calendar") == 1


def test_events_google_calendar_raises_when_all_accounts_fail():
    postgres = _FakePostgres()
    with pytest.raises(Exception, match="failed for all accounts"):
        materialize(
            [events_google_calendar],
            resources={
                "google_calendar": _FakeGoogleCalendar({}, accounts=[ACCOUNT]),
                "postgres": postgres,
            },
        )


def test_mark_stale_rows_updates_unseen_rows_in_window():
    postgres = _FakePostgres(stale_rowcount=3)
    seen_at = datetime(2026, 1, 1, tzinfo=UTC)
    affected = _mark_stale_rows(
        cast(PostgresResource, postgres),
        account=ACCOUNT,
        time_min=seen_at - timedelta(days=1),
        time_max=seen_at + timedelta(days=14),
        seen_at=seen_at,
    )
    assert affected == 3
    assert postgres._conn.committed is True
    query, params = postgres.cursor.executed[0]
    assert "UPDATE" in query
    assert params[1] == ACCOUNT.email
    assert params[2] == ACCOUNT.calendar_id


def test_calendar_sync_schedule_cadence_and_timezone():
    assert calendar_sync_schedule.cron_schedule == "0 6 * * *"
    assert calendar_sync_schedule.execution_timezone == "America/Los_Angeles"
    assert calendar_sync_job.name == "calendar_sync"


def test_calendar_sync_job_description_is_loaded_from_doc():
    assert calendar_sync_job.description is not None
    assert "Google Calendar Sync" in calendar_sync_job.description
    assert "authorize_google_calendar.py" in calendar_sync_job.description


def test_load_doc_reads_events_google_calendar_markdown():
    assert load_doc("events_google_calendar.md") == calendar_sync_job.description
