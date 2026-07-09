import json
from datetime import UTC, datetime, timedelta
from typing import Any

import polars as pl
from dagster import (
    AssetCheckSpec,
    AssetExecutionContext,
    MaterializeResult,
    MetadataValue,
    asset,
)

from dagster_project.common.config import (
    calendar_forward_window_days,
    calendar_lookback_days,
)
from dagster_project.common.event_checks import (
    event_start_valid_check,
    raise_for_failed_event_checks,
    required_string_columns_check,
)
from dagster_project.common.landing import (
    ROW_COUNT_DAGSTER_TYPE,
    empty_frame,
    log_landing_summary,
    parse_iso_utc,
    stamp,
    utc_now,
)
from dagster_project.resources import GoogleCalendarResource, PostgresResource
from dagster_project.resources.google_calendar import GoogleCalendarAccount
from dagster_project.sql import ingestion as sql

GROUP = "google_calendar"
TARGET = "source.events_google_calendar"
SOURCE = "google_calendar"
SCHEMA = {
    "account_email": pl.String,
    "calendar_id": pl.String,
    "calendar_summary": pl.String,
    "source_event_id": pl.String,
    "source_instance_id": pl.String,
    "event_name": pl.String,
    "event_start": pl.Datetime(time_zone="UTC"),
    "event_end": pl.Datetime(time_zone="UTC"),
    "is_all_day": pl.Boolean,
    "status": pl.String,
    "transparency": pl.String,
    "visibility": pl.String,
    "location": pl.String,
    "html_link": pl.String,
    "raw": pl.String,
    "last_seen_at": pl.Datetime(time_zone="UTC"),
}
CONFLICT_KEYS = ["account_email", "calendar_id", "source_instance_id"]
UPDATE_COLS = [
    "calendar_summary",
    "event_name",
    "event_start",
    "event_end",
    "is_all_day",
    "status",
    "transparency",
    "visibility",
    "location",
    "html_link",
    "raw",
    "source",
    "last_seen_at",
    "modified_at",
]


@asset(
    group_name=GROUP,
    compute_kind="google_calendar",
    dagster_type=ROW_COUNT_DAGSTER_TYPE,
    description=(
        "Fetch upcoming Google Calendar events for configured accounts and land "
        "them into source.events_google_calendar."
    ),
    check_specs=[
        AssetCheckSpec(
            name="source_instance_id_present",
            asset="events_google_calendar",
            blocking=True,
            description=(
                "Every parsed calendar event row has a non-empty source_instance_id."
            ),
        ),
        AssetCheckSpec(
            name="event_start_valid",
            asset="events_google_calendar",
            blocking=True,
            description="Every parsed calendar event row has a non-null event_start.",
        ),
    ],
)
def events_google_calendar(
    context: AssetExecutionContext,
    google_calendar: GoogleCalendarResource,
    postgres: PostgresResource,
) -> MaterializeResult:
    accounts = google_calendar.accounts()
    forward_days = calendar_forward_window_days()
    now = utc_now()
    time_min = now - timedelta(days=calendar_lookback_days())
    time_max = now + timedelta(days=forward_days)

    rows: list[dict[str, Any]] = []
    fetched = 0
    failed_accounts: list[str] = []

    for account in accounts:
        try:
            raw_events = google_calendar.fetch_events(
                account,
                time_min=time_min,
                time_max=time_max,
            )
        except Exception as exc:  # noqa: BLE001 - one account failing must not block the rest
            context.log.error(
                f"google_calendar fetch failed for {account.email} "
                f"({account.calendar_id}): {exc}"
            )
            failed_accounts.append(account.email)
            continue

        fetched += len(raw_events)
        for event in raw_events:
            row = _event_to_row(event, account=account, seen_at=now)
            if row is not None:
                rows.append(row)

    if accounts and len(failed_accounts) == len(accounts):
        msg = f"google_calendar sync failed for all accounts: {failed_accounts}"
        raise RuntimeError(msg)

    df = (
        pl.DataFrame(rows, schema=SCHEMA, orient="row") if rows else empty_frame(SCHEMA)
    )

    source_instance_id_check = required_string_columns_check(
        df,
        check_name="source_instance_id_present",
        columns=["source_instance_id"],
    )
    event_start_check = event_start_valid_check(df, check_name="event_start_valid")
    raise_for_failed_event_checks(source_instance_id_check, event_start_check)

    parsed = df.height
    df = stamp(df, source=SOURCE, modified_at=now)
    merged = postgres.merge_polars(
        df,
        target=TARGET,
        conflict_keys=CONFLICT_KEYS,
        update_cols=UPDATE_COLS,
    )

    stale_marked = 0
    for account in accounts:
        if account.email in failed_accounts:
            continue
        stale_marked += _mark_stale_rows(
            postgres,
            account=account,
            time_min=time_min,
            time_max=time_max,
            seen_at=now,
        )

    detail = (
        f"accounts={len(accounts)} failed={len(failed_accounts)} "
        f"stale_marked={stale_marked}"
    )
    metadata = log_landing_summary(
        context,
        source="google_calendar",
        fetched=fetched,
        parsed=parsed,
        after_window=parsed,
        merged=merged,
        forward_window_days=forward_days,
        detail=detail,
    )
    metadata["stale_marked"] = MetadataValue.int(stale_marked)
    metadata["accounts_failed"] = MetadataValue.int(len(failed_accounts))
    context.add_output_metadata(metadata, output_name="result")

    return MaterializeResult(
        value=merged,
        check_results=[source_instance_id_check, event_start_check],
    )


def _event_to_row(
    event: dict[str, Any],
    *,
    account: GoogleCalendarAccount,
    seen_at: datetime,
) -> dict[str, Any] | None:
    source_instance_id = event.get("id")
    if not source_instance_id:
        return None

    start_info = event.get("start") or {}
    end_info = event.get("end") or {}
    event_start = _parse_event_datetime(start_info)
    if event_start is None:
        return None
    event_end = _parse_event_datetime(end_info)
    is_all_day = "date" in start_info and "dateTime" not in start_info

    return {
        "account_email": account.email,
        "calendar_id": account.calendar_id,
        "calendar_summary": account.label or None,
        "source_event_id": str(event.get("recurringEventId") or source_instance_id),
        "source_instance_id": str(source_instance_id),
        "event_name": event.get("summary") or "Busy",
        "event_start": event_start,
        "event_end": event_end,
        "is_all_day": is_all_day,
        "status": event.get("status") or "confirmed",
        "transparency": event.get("transparency") or "opaque",
        "visibility": event.get("visibility") or "default",
        "location": event.get("location"),
        "html_link": event.get("htmlLink"),
        "raw": json.dumps(event),
        "last_seen_at": seen_at,
    }


def _parse_event_datetime(info: dict[str, Any]) -> datetime | None:
    if "dateTime" in info:
        return parse_iso_utc(info["dateTime"])
    if "date" in info:
        try:
            parsed = datetime.fromisoformat(info["date"])
        except ValueError:
            return None
        return parsed.replace(tzinfo=UTC)
    return None


def _mark_stale_rows(
    postgres: PostgresResource,
    *,
    account: GoogleCalendarAccount,
    time_min: datetime,
    time_max: datetime,
    seen_at: datetime,
) -> int:
    """Cancel rows in the fetch window not seen in this run's successful pull."""
    params = (seen_at, account.email, account.calendar_id, time_min, time_max, seen_at)
    with postgres.connection() as conn, conn.cursor() as cur:
        cur.execute(sql.MARK_STALE_GOOGLE_CALENDAR_EVENTS, params)
        affected = cur.rowcount
        conn.commit()
        return affected
