from typing import Any

import polars as pl
from dagster import (
    AssetCheckSpec,
    AssetExecutionContext,
    MaterializeResult,
    MetadataValue,
    asset,
)
from nba_api.stats.endpoints.scheduleleaguev2 import ScheduleLeagueV2

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

GROUP = "nba"
TARGET = "source.events_nba"
NBA_SCHEDULE_SOURCE = "https://stats.nba.com/stats/scheduleleaguev2"
HTTP_TIMEOUT_SECONDS = 20.0
SCHEMA = {
    "source_event_id": pl.String,
    "league": pl.String,
    "event_name": pl.String,
    "event_start": pl.Datetime(time_zone="UTC"),
    "status": pl.String,
    "home_team": pl.String,
    "away_team": pl.String,
    "venue": pl.String,
}
UPDATE_COLS = [
    "league",
    "event_name",
    "event_start",
    "status",
    "home_team",
    "away_team",
    "venue",
    "source",
    "modified_at",
]


@asset(
    group_name=GROUP,
    compute_kind="nba",
    dagster_type=ROW_COUNT_DAGSTER_TYPE,
    description=(
        "Fetch upcoming NBA games from stats.nba.com and land them into "
        "source.events_nba."
    ),
    check_specs=[
        AssetCheckSpec(
            name="source_event_id_present",
            asset="events_nba",
            blocking=True,
            description="Every parsed NBA event row has a non-empty source_event_id.",
        ),
        AssetCheckSpec(
            name="event_start_valid",
            asset="events_nba",
            blocking=True,
            description="Every parsed NBA event row has a non-null event_start.",
        ),
    ],
)
def events_nba(
    context: AssetExecutionContext,
    postgres: PostgresResource,
) -> MaterializeResult:
    raw = fetch_nba_schedule()
    schedule = raw.get("leagueSchedule", {})
    game_dates = schedule.get("gameDates", [])
    fetched = sum(len(game_date.get("games", [])) for game_date in game_dates)
    season = schedule.get("seasonYear")
    window_days = event_forward_window_days()
    detail = f"season={season}, game_dates={len(game_dates)}" if season else ""
    df = _schedule_to_frame(raw)

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
        source="nba",
        conflict_keys=["source_event_id"],
        update_cols=UPDATE_COLS,
        forward_window_days=window_days,
        fetched=fetched,
        log_source="nba",
        detail=detail,
        extra_metadata={"source": MetadataValue.url(NBA_SCHEDULE_SOURCE)},
        output_name="result",
    )
    return MaterializeResult(
        value=rows,
        check_results=[source_event_id_check, event_start_check],
    )


def fetch_nba_schedule() -> dict[str, Any]:
    schedule = ScheduleLeagueV2(timeout=HTTP_TIMEOUT_SECONDS)
    response = schedule.nba_response
    if response is None:
        return {"leagueSchedule": {"gameDates": []}}
    return response.get_dict()


def _schedule_to_frame(payload: dict[str, Any]) -> pl.DataFrame:
    games = []
    for game_date in payload.get("leagueSchedule", {}).get("gameDates", []):
        games.extend(game_date.get("games", []))

    rows = [row for row in (_game_to_row(game) for game in games) if row is not None]
    if not rows:
        return empty_frame(SCHEMA)
    return pl.DataFrame(rows, schema=SCHEMA, orient="row")


def _game_to_row(game: dict[str, Any]) -> dict[str, Any] | None:
    source_event_id = game.get("gameId") or game.get("gameCode")
    if not source_event_id:
        return None

    event_start = parse_iso_utc(game.get("gameDateTimeUTC") or game.get("gameDateUTC"))
    if event_start is None:
        return None

    home = game.get("homeTeam") or {}
    away = game.get("awayTeam") or {}
    home_name = _team_name(home)
    away_name = _team_name(away)
    event_name = (
        f"{away_name} at {home_name}" if home_name and away_name else "NBA game"
    )

    return {
        "source_event_id": str(source_event_id),
        "league": "NBA",
        "event_name": event_name,
        "event_start": event_start,
        "status": game.get("gameStatusText"),
        "home_team": home_name,
        "away_team": away_name,
        "venue": game.get("arenaName") or game.get("arenaCity"),
    }


def _team_name(team: dict[str, Any]) -> str | None:
    pieces = [team.get("teamCity"), team.get("teamName")]
    name = " ".join(str(piece) for piece in pieces if piece)
    return name or team.get("teamTricode")
