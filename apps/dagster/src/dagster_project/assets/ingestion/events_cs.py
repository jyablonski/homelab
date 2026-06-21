from datetime import UTC, datetime
from typing import Any

import polars as pl
from dagster import (
    AssetCheckSpec,
    AssetExecutionContext,
    MaterializeResult,
    asset,
)

from dagster_project.common.event_checks import (
    event_start_valid_check,
    raise_for_failed_event_checks,
    required_string_columns_check,
)
from dagster_project.common.landing import empty_frame, land_events
from dagster_project.resources import HLTVResource, PostgresResource

GROUP = "cs"
TARGET = "source.events_cs"
SCHEMA = {
    "source_event_id": pl.String,
    "league": pl.String,
    "event_name": pl.String,
    "event_start": pl.Datetime(time_zone="UTC"),
    "status": pl.String,
    "team1": pl.String,
    "team2": pl.String,
    "tournament": pl.String,
    "maps": pl.String,
    "rating": pl.Int64,
}
UPDATE_COLS = [
    "league",
    "event_name",
    "event_start",
    "status",
    "team1",
    "team2",
    "tournament",
    "maps",
    "rating",
    "source",
    "modified_at",
]


@asset(
    group_name=GROUP,
    compute_kind="hltv",
    dagster_type=int,
    description=(
        "Fetch upcoming CS2 matches from HLTV and land them into source.events_cs."
    ),
    check_specs=[
        AssetCheckSpec(
            name="source_event_id_present",
            asset="events_cs",
            blocking=True,
            description="Every parsed CS2 event row has a non-empty source_event_id.",
        ),
        AssetCheckSpec(
            name="event_start_valid",
            asset="events_cs",
            blocking=True,
            description="Every parsed CS2 event row has a non-null event_start.",
        ),
    ],
)
def events_cs(
    context: AssetExecutionContext,
    hltv: HLTVResource,
    postgres: PostgresResource,
) -> MaterializeResult:
    matches = hltv.fetch_upcoming()
    fetched = len(matches)
    df = _matches_to_frame(matches)
    missing_start = sum(
        1
        for match in matches
        if match.get("id")
        and _parse_match_datetime(match.get("date"), match.get("time")) is None
    )
    detail_parts = []
    if missing_start:
        detail_parts.append(f"missing_event_start={missing_start}")

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
        target=TARGET,
        source="hltv",
        conflict_keys=["source_event_id"],
        update_cols=UPDATE_COLS,
        forward_window_days=hltv.forward_window_days,
        fetched=fetched,
        log_source="hltv",
        detail=", ".join(detail_parts),
        output_name="result",
    )
    if fetched and rows == 0 and not detail_parts:
        context.log.info("all matches outside forward window or unparseable dates")
    return MaterializeResult(
        value=rows,
        check_results=[source_event_id_check, event_start_check],
    )


def _matches_to_frame(matches: list[dict[str, Any]]) -> pl.DataFrame:
    rows = [
        row for row in (_match_to_row(match) for match in matches) if row is not None
    ]
    if not rows:
        return empty_frame(SCHEMA)
    return pl.DataFrame(rows, schema=SCHEMA, orient="row")


def _match_to_row(match: dict[str, Any]) -> dict[str, Any] | None:
    match_id = match.get("id")
    if not match_id:
        return None

    event_start = _parse_match_datetime(match.get("date"), match.get("time"))
    if event_start is None:
        return None

    team1 = _as_optional_str(match.get("team1"))
    team2 = _as_optional_str(match.get("team2"))
    tournament = _as_optional_str(match.get("event"))
    event_name = " vs ".join(team for team in [team1, team2] if team) or "CS2 match"

    return {
        "source_event_id": str(match_id),
        "league": "CS2",
        "event_name": event_name,
        "event_start": event_start,
        "status": _as_optional_str(match.get("status")),
        "team1": team1,
        "team2": team2,
        "tournament": tournament,
        "maps": _as_optional_str(match.get("maps")),
        "rating": _as_optional_int(match.get("rating")),
    }


def _parse_match_datetime(raw_date: Any, raw_time: Any) -> datetime | None:
    if not raw_date:
        return None
    date_text = str(raw_date)
    if date_text.upper() == "LIVE":
        return datetime.now(UTC)
    time_text = str(raw_time or "00:00")
    for fmt in ("%Y-%m-%d %H:%M", "%d-%m-%Y %H:%M"):
        try:
            return datetime.strptime(f"{date_text} {time_text}", fmt).replace(
                tzinfo=UTC
            )
        except ValueError:
            continue
    return None


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
