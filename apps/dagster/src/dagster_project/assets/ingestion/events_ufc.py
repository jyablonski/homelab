from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import polars as pl
from dagster import (
    AssetCheckSpec,
    AssetExecutionContext,
    MaterializeResult,
    MetadataValue,
    asset,
)

from dagster_project.common.config import event_forward_window_days
from dagster_project.common.event_checks import (
    event_start_valid_check,
    raise_for_failed_event_checks,
    required_string_columns_check,
)
from dagster_project.common.landing import (
    ROW_COUNT_DAGSTER_TYPE,
    empty_frame,
    land_events,
    parse_iso_utc,
)
from dagster_project.resources import PostgresResource

GROUP = "ufc"
EVENT_TARGET = "source.events_ufc"
FIGHTER_TARGET = "source.events_ufc_fighters"
ESPN_UFC_SCOREBOARD_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard"
)
HTTP_TIMEOUT_SECONDS = 20.0
EVENT_SCHEMA = {
    "source_event_id": pl.String,
    "league": pl.String,
    "event_name": pl.String,
    "event_start": pl.Datetime(time_zone="UTC"),
    "location": pl.String,
    "source_url": pl.String,
}
FIGHTER_SCHEMA = {
    "source_event_id": pl.String,
    "fighter_id": pl.String,
    "fighter_name": pl.String,
    "bout_id": pl.String,
    "corner": pl.String,
    "outcome": pl.String,
}
EVENT_UPDATE_COLS = [
    "league",
    "event_name",
    "event_start",
    "location",
    "source_url",
    "source",
    "modified_at",
]
FIGHTER_UPDATE_COLS = [
    "fighter_name",
    "bout_id",
    "corner",
    "outcome",
    "source",
    "modified_at",
]


@asset(
    group_name=GROUP,
    compute_kind="http",
    description=(
        "Fetch upcoming UFC event and fighter payloads from ESPN's public MMA "
        "scoreboard."
    ),
)
def ufc_upcoming() -> dict[str, Any]:
    payload = _fetch_espn_scoreboard()
    events, fighters, stats = _parse_espn_scoreboard(payload)
    stats["events_kept"] = len(events)
    stats["fighters_fetched"] = len(fighters)
    return {"events": events, "fighters": fighters, "stats": stats}


@asset(
    group_name=GROUP,
    compute_kind="http",
    dagster_type=ROW_COUNT_DAGSTER_TYPE,
    description=(
        "Land upcoming UFC cards from the ESPN scoreboard into source.events_ufc."
    ),
    check_specs=[
        AssetCheckSpec(
            name="source_event_id_present",
            asset="events_ufc",
            blocking=True,
            description="Every parsed UFC event row has a non-empty source_event_id.",
        ),
        AssetCheckSpec(
            name="event_start_valid",
            asset="events_ufc",
            blocking=True,
            description="Every parsed UFC event row has a non-null event_start.",
        ),
    ],
)
def events_ufc(
    context: AssetExecutionContext,
    ufc_upcoming: dict[str, Any],
    postgres: PostgresResource,
) -> MaterializeResult:
    events = ufc_upcoming["events"]
    scrape_stats = ufc_upcoming["stats"]
    window_days = event_forward_window_days()
    detail = (
        f"source=espn, events_in_payload={scrape_stats['events_in_payload']}, "
        f"skipped_past={scrape_stats['skipped_past']}, "
        f"skipped_future={scrape_stats['skipped_future']}, "
        f"skipped_unparsed_date={scrape_stats['skipped_unparsed_date']}"
    )
    df = _events_to_frame(events)
    source_event_id_check = required_string_columns_check(
        df,
        check_name="source_event_id_present",
        columns=["source_event_id"],
    )
    event_start_check = event_start_valid_check(df, check_name="event_start_valid")
    raise_for_failed_event_checks(source_event_id_check, event_start_check)

    rows = land_events(
        context,
        postgres,
        df=df,
        target=EVENT_TARGET,
        source="espn",
        conflict_keys=["source_event_id"],
        update_cols=EVENT_UPDATE_COLS,
        forward_window_days=window_days,
        fetched=len(events),
        log_source="ufc-events",
        detail=detail,
        apply_forward_window=False,
        extra_metadata={"source": MetadataValue.url(ESPN_UFC_SCOREBOARD_URL)},
        output_name="result",
    )
    return MaterializeResult(
        value=rows,
        check_results=[source_event_id_check, event_start_check],
    )


@asset(
    group_name=GROUP,
    compute_kind="http",
    dagster_type=ROW_COUNT_DAGSTER_TYPE,
    description="Land fighters for upcoming UFC cards into source.events_ufc_fighters.",
    check_specs=[
        AssetCheckSpec(
            name="fighter_key_present",
            asset="events_ufc_fighters",
            blocking=True,
            description=(
                "Every parsed UFC fighter row has non-empty source_event_id and "
                "fighter_id values."
            ),
        ),
    ],
)
def events_ufc_fighters(
    context: AssetExecutionContext,
    ufc_upcoming: dict[str, Any],
    events_ufc: int,
    postgres: PostgresResource,
) -> MaterializeResult:
    kept_event_ids = {event["source_event_id"] for event in ufc_upcoming["events"]}
    fighters = [
        fighter
        for fighter in ufc_upcoming["fighters"]
        if fighter.get("source_event_id") in kept_event_ids
    ]
    scrape_stats = ufc_upcoming["stats"]
    df = _fighters_to_frame(fighters)
    fighter_key_check = required_string_columns_check(
        df,
        check_name="fighter_key_present",
        columns=["source_event_id", "fighter_id"],
    )
    raise_for_failed_event_checks(fighter_key_check)

    rows = land_events(
        context,
        postgres,
        df=df,
        target=FIGHTER_TARGET,
        source="espn",
        conflict_keys=["source_event_id", "fighter_id"],
        update_cols=FIGHTER_UPDATE_COLS,
        forward_window_days=event_forward_window_days(),
        fetched=len(fighters),
        log_source="ufc-fighters",
        detail=(
            f"parent_events={scrape_stats['events_kept']}, "
            f"bouts={scrape_stats['bouts_kept']}"
        ),
        apply_forward_window=False,
        extra_metadata={"parent_event_rows": MetadataValue.int(events_ufc)},
        output_name="result",
    )
    return MaterializeResult(
        value=rows,
        check_results=[fighter_key_check],
    )


def _fetch_espn_scoreboard() -> dict[str, Any]:
    today = datetime.now(UTC).date()
    window_end = today + timedelta(days=event_forward_window_days())
    params = {
        "dates": f"{today.strftime('%Y%m%d')}-{window_end.strftime('%Y%m%d')}",
    }
    with httpx.Client(timeout=HTTP_TIMEOUT_SECONDS) as client:
        response = client.get(ESPN_UFC_SCOREBOARD_URL, params=params)
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, dict):
        msg = "ESPN UFC scoreboard returned unexpected payload"
        raise TypeError(msg)
    return payload


def _parse_espn_scoreboard(
    payload: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    now = datetime.now(UTC)
    window_end = now + timedelta(days=event_forward_window_days())
    stats = {
        "events_in_payload": 0,
        "skipped_past": 0,
        "skipped_future": 0,
        "skipped_unparsed_date": 0,
        "bouts_kept": 0,
    }
    events: list[dict[str, Any]] = []
    fighters: list[dict[str, Any]] = []

    for raw_event in payload.get("events", []):
        if not isinstance(raw_event, dict):
            continue
        stats["events_in_payload"] += 1

        event_start = parse_iso_utc(raw_event.get("date"))
        if event_start is None:
            stats["skipped_unparsed_date"] += 1
            continue

        if event_start < now:
            stats["skipped_past"] += 1
            continue
        if event_start > window_end:
            stats["skipped_future"] += 1
            continue

        event_id = str(raw_event.get("id") or "")
        if not event_id:
            stats["skipped_unparsed_date"] += 1
            continue

        location = _format_espn_location(raw_event)
        source_url = f"https://www.espn.com/mma/fightcenter/_/id/{event_id}/league/ufc"
        events.append(
            {
                "source_event_id": event_id,
                "event_name": str(
                    raw_event.get("name") or raw_event.get("shortName") or "UFC event"
                ),
                "event_start": event_start,
                "location": location,
                "source_url": source_url,
            }
        )

        for competition in raw_event.get("competitions", []):
            if not isinstance(competition, dict):
                continue
            bout_id = str(competition.get("id") or "")
            competitors = [
                comp
                for comp in competition.get("competitors", [])
                if isinstance(comp, dict) and comp.get("athlete")
            ]
            if len(competitors) < 2:
                continue
            stats["bouts_kept"] += 1
            outcome = (
                competition.get("status", {}).get("type", {}).get("name")
                if isinstance(competition.get("status"), dict)
                else None
            )
            for index, competitor in enumerate(competitors[:2]):
                athlete = competitor.get("athlete") or {}
                fighter_id = str(competitor.get("id") or athlete.get("id") or "")
                fighter_name = str(
                    athlete.get("displayName") or athlete.get("fullName") or ""
                ).strip()
                if not fighter_id or not fighter_name:
                    continue
                fighters.append(
                    {
                        "source_event_id": event_id,
                        "fighter_id": fighter_id,
                        "fighter_name": fighter_name,
                        "bout_id": bout_id or None,
                        "corner": "red" if index == 0 else "blue",
                        "outcome": outcome,
                    }
                )

    return events, fighters, stats


def _format_espn_location(raw_event: dict[str, Any]) -> str | None:
    competitions = raw_event.get("competitions") or []
    if not competitions:
        return None
    venue = (competitions[0] or {}).get("venue") or {}
    address = venue.get("address") or {}
    pieces = [
        venue.get("fullName"),
        address.get("city"),
        address.get("state"),
        address.get("country"),
    ]
    location = ", ".join(str(piece) for piece in pieces if piece)
    return location or None


def _events_to_frame(events: list[dict[str, Any]]) -> pl.DataFrame:
    rows = [
        {
            "source_event_id": str(event["source_event_id"]),
            "league": "UFC",
            "event_name": str(event["event_name"]),
            "event_start": event["event_start"],
            "location": event.get("location"),
            "source_url": event.get("source_url"),
        }
        for event in events
        if event.get("source_event_id")
        and isinstance(event.get("event_start"), datetime)
    ]
    if not rows:
        return empty_frame(EVENT_SCHEMA)
    return pl.DataFrame(rows, schema=EVENT_SCHEMA, orient="row")


def _fighters_to_frame(fighters: list[dict[str, Any]]) -> pl.DataFrame:
    rows = [
        {
            "source_event_id": str(fighter["source_event_id"]),
            "fighter_id": str(fighter["fighter_id"]),
            "fighter_name": str(fighter["fighter_name"]),
            "bout_id": fighter.get("bout_id"),
            "corner": fighter.get("corner"),
            "outcome": fighter.get("outcome"),
        }
        for fighter in fighters
        if fighter.get("source_event_id")
        and fighter.get("fighter_id")
        and fighter.get("fighter_name")
    ]
    if not rows:
        return empty_frame(FIGHTER_SCHEMA)
    return pl.DataFrame(rows, schema=FIGHTER_SCHEMA, orient="row")
