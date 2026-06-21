from __future__ import annotations
from datetime import UTC, datetime, timedelta
from typing import cast

import polars as pl
import pytest
from dagster import AssetExecutionContext, materialize

from dagster_project.assets.ingestion import events_nba as nba_module
from dagster_project.assets.ingestion import events_ufc as ufc_module
from dagster_project.assets.ingestion.events_cs import (
    _as_optional_int,
    _as_optional_str,
    _match_to_row,
    _matches_to_frame,
    _parse_match_datetime,
    events_cs,
)
from dagster_project.assets.ingestion.events_nba import (
    _schedule_to_frame,
    _team_name,
    events_nba,
)
from dagster_project.assets.ingestion.events_ufc import (
    _events_to_frame,
    _fighters_to_frame,
    _format_espn_location,
    events_ufc,
    events_ufc_fighters,
    ufc_upcoming,
)
from dagster_project.common.event_checks import (
    event_start_valid_check,
    required_string_columns_check,
)
from dagster_project.common.landing import (
    empty_frame,
    filter_forward_window,
    log_landing_summary,
    parse_iso_utc,
    stamp,
)
from dagster_project.jobs.events import daily_events_schedule

pytestmark = pytest.mark.unit


def test_stamp_adds_landing_metadata():
    modified_at = datetime(2026, 1, 1, tzinfo=UTC)
    df = stamp(
        pl.DataFrame({"source_event_id": ["1"]}),
        source="nba",
        modified_at=modified_at,
    )
    row = df.to_dicts()[0]
    assert row["source"] == "nba"
    assert row["modified_at"] == modified_at


def test_filter_forward_window_keeps_only_upcoming_rows():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    df = pl.DataFrame(
        {
            "source_event_id": ["past", "inside", "outside"],
            "event_start": [
                datetime(2025, 12, 31, tzinfo=UTC),
                datetime(2026, 1, 2, tzinfo=UTC),
                datetime(2026, 2, 1, tzinfo=UTC),
            ],
        }
    )
    filtered = filter_forward_window(
        df,
        timestamp_col="event_start",
        days=21,
        now=now,
    )
    assert filtered["source_event_id"].to_list() == ["inside"]


def test_filter_forward_window_returns_empty_frame_unchanged():
    empty = pl.DataFrame(
        schema={
            "source_event_id": pl.String,
            "event_start": pl.Datetime(time_zone="UTC"),
        }
    )
    assert filter_forward_window(empty, timestamp_col="event_start", days=21).is_empty()


def test_empty_frame_builds_typed_frame():
    frame = empty_frame({"source_event_id": pl.String})
    assert frame.is_empty()
    assert frame.schema == {"source_event_id": pl.String}


def test_nba_schedule_parser_returns_empty_frame_for_no_games():
    assert _schedule_to_frame({"leagueSchedule": {"gameDates": []}}).is_empty()


def test_nba_helpers_handle_missing_fields():
    assert parse_iso_utc(None) is None
    assert parse_iso_utc("bad-date") is None
    naive = parse_iso_utc("2026-01-02T03:00:00")
    assert naive is not None
    assert naive.replace(tzinfo=UTC) == parse_iso_utc("2026-01-02T03:00:00Z")
    assert _team_name({"teamTricode": "LAL"}) == "LAL"
    assert _schedule_to_frame(
        {
            "leagueSchedule": {
                "gameDates": [{"games": [{"homeTeam": {}, "awayTeam": {}}]}]
            }
        }
    ).is_empty()


def test_cs_helpers_handle_edge_cases():
    assert _parse_match_datetime(None, "12:00") is None
    live = _parse_match_datetime("LIVE", None)
    assert live is not None
    assert _parse_match_datetime("bad-date", "12:00") is None
    assert _as_optional_str("  ") is None
    assert _as_optional_int("bad") is None
    row = _match_to_row(
        {"id": "1", "date": "2026-01-02", "time": "12:30", "team1": None, "team2": None}
    )
    assert row is not None
    assert row["event_name"] == "CS2 match"
    assert _match_to_row({"id": "1", "team1": "A", "team2": "B"}) is None
    assert _match_to_row({"team1": "A", "team2": "B"}) is None
    assert _matches_to_frame([]).is_empty()


def test_ufc_parser_skips_invalid_and_out_of_window_events():
    past = datetime.now(UTC) - timedelta(days=2)
    today_past = datetime.now(UTC) - timedelta(hours=2)
    future = datetime.now(UTC) + timedelta(days=60)
    events, fighters, stats = ufc_module._parse_espn_scoreboard(
        {
            "events": [
                "not-a-dict",
                {
                    "id": "1",
                    "date": past.isoformat().replace("+00:00", "Z"),
                    "name": "Past",
                },
                {
                    "id": "4",
                    "date": today_past.isoformat().replace("+00:00", "Z"),
                    "name": "Today but earlier",
                },
                {
                    "id": "2",
                    "date": future.isoformat().replace("+00:00", "Z"),
                    "name": "Future",
                },
                {"date": "2026-01-02T03:00:00Z", "name": "Missing id"},
                {"id": "3", "date": "not-a-date", "name": "Bad date"},
            ]
        }
    )
    assert events == []
    assert fighters == []
    assert stats["skipped_past"] >= 2
    assert stats["skipped_future"] == 1
    assert stats["skipped_unparsed_date"] >= 1


def test_ufc_helpers_cover_empty_and_invalid_values():
    assert parse_iso_utc(None) is None
    assert parse_iso_utc("bad") is None
    assert _format_espn_location({"competitions": []}) is None
    assert _events_to_frame([]).is_empty()
    assert _fighters_to_frame([{"source_event_id": "1"}]).is_empty()


def test_fetch_espn_scoreboard_rejects_non_dict_payload(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return ["bad"]

    class FakeClient:
        def __init__(self, timeout):
            assert timeout == ufc_module.HTTP_TIMEOUT_SECONDS

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get(self, url, params):
            return FakeResponse()

    monkeypatch.setattr(ufc_module.httpx, "Client", FakeClient)
    with pytest.raises(TypeError, match="unexpected payload"):
        ufc_module._fetch_espn_scoreboard()


class _FakePostgres:
    def __init__(self):
        self.merged_frames: list[pl.DataFrame] = []

    def merge_polars(self, df, **_kwargs):
        self.merged_frames.append(df)
        return df.height

    def fetch_value(self, query, *_args):
        return None


def test_event_ingestion_checks_validate_dataframes_before_storage():
    df = pl.DataFrame(
        {
            "source_event_id": ["ok", " "],
            "event_start": [datetime(2026, 1, 1, tzinfo=UTC), None],
        },
        schema={
            "source_event_id": pl.String,
            "event_start": pl.Datetime(time_zone="UTC"),
        },
    )

    key_result = required_string_columns_check(
        df,
        check_name="source_event_id_present",
        columns=["source_event_id"],
    )
    date_result = event_start_valid_check(df, check_name="event_start_valid")

    assert not key_result.passed
    assert not date_result.passed


class _FakeHLTV:
    forward_window_days = 21

    def fetch_upcoming(self):
        return [
            {
                "id": "2371201",
                "date": (datetime.now(UTC) + timedelta(days=2)).strftime("%Y-%m-%d"),
                "time": "12:30",
                "team1": "MOUZ",
                "team2": "FaZe",
                "event": "IEM",
            }
        ]


def test_events_cs_materializes_with_fake_resources():
    result = materialize(
        [events_cs],
        resources={"hltv": _FakeHLTV(), "postgres": _FakePostgres()},
    )
    assert result.success
    assert result.output_for_node("events_cs") == 1


def test_events_cs_skips_matches_with_missing_start():
    class MissingStartHLTV(_FakeHLTV):
        def fetch_upcoming(self):
            return [{"id": "1", "team1": "A", "team2": "B", "event": "X"}]

    postgres = _FakePostgres()
    result = materialize(
        [events_cs],
        resources={"hltv": MissingStartHLTV(), "postgres": postgres},
    )

    assert result.success
    assert result.output_for_node("events_cs") == 0
    assert postgres.merged_frames[0].is_empty()


def test_events_cs_logs_when_matches_miss_window():
    class OutsideWindowHLTV:
        forward_window_days = 21

        def fetch_upcoming(self):
            far_future = datetime.now(UTC) + timedelta(days=60)
            return [
                {
                    "id": "2",
                    "date": far_future.strftime("%Y-%m-%d"),
                    "time": "12:30",
                    "team1": "A",
                    "team2": "B",
                    "event": "X",
                }
            ]

    outside = materialize(
        [events_cs],
        resources={"hltv": OutsideWindowHLTV(), "postgres": _FakePostgres()},
    )
    assert outside.success
    assert outside.output_for_node("events_cs") == 0


def test_events_nba_materializes_with_fake_resources(monkeypatch):
    monkeypatch.setattr(
        nba_module,
        "fetch_nba_schedule",
        lambda: {
            "leagueSchedule": {
                "gameDates": [
                    {
                        "games": [
                            {
                                "gameId": "1",
                                "gameDateTimeUTC": (
                                    datetime.now(UTC) + timedelta(days=2)
                                )
                                .isoformat()
                                .replace("+00:00", "Z"),
                                "homeTeam": {"teamName": "Nuggets"},
                                "awayTeam": {"teamName": "Lakers"},
                            }
                        ]
                    }
                ]
            }
        },
    )
    result = materialize(
        [events_nba],
        resources={"postgres": _FakePostgres()},
    )
    assert result.success


def test_events_ufc_assets_materialize_with_fake_resources(monkeypatch):
    event_start = datetime.now(UTC) + timedelta(days=2)
    monkeypatch.setattr(
        ufc_module,
        "_fetch_espn_scoreboard",
        lambda: {
            "events": [
                {
                    "id": "ufc-1",
                    "date": event_start.isoformat().replace("+00:00", "Z"),
                    "name": "UFC 999",
                    "competitions": [
                        {
                            "id": "401999",
                            "competitors": [
                                {
                                    "id": "f1",
                                    "athlete": {"displayName": "Example Fighter"},
                                },
                                {
                                    "id": "f2",
                                    "athlete": {"displayName": "Other Fighter"},
                                },
                            ],
                        }
                    ],
                }
            ]
        },
    )
    result = materialize(
        [ufc_upcoming, events_ufc, events_ufc_fighters],
        resources={"postgres": _FakePostgres()},
    )
    assert result.success
    assert result.output_for_node("events_ufc") == 1
    assert result.output_for_node("events_ufc_fighters") == 2


def test_nba_schedule_parser_builds_event_rows():
    frame = _schedule_to_frame(
        {
            "leagueSchedule": {
                "gameDates": [
                    {
                        "games": [
                            {
                                "gameId": "0022500001",
                                "gameDateTimeUTC": "2026-01-02T03:00:00Z",
                                "gameStatusText": "7:00 pm ET",
                                "arenaName": "Ball Arena",
                                "homeTeam": {
                                    "teamCity": "Denver",
                                    "teamName": "Nuggets",
                                },
                                "awayTeam": {
                                    "teamCity": "Los Angeles",
                                    "teamName": "Lakers",
                                },
                            }
                        ]
                    }
                ]
            }
        }
    )
    row = frame.to_dicts()[0]
    assert row["source_event_id"] == "0022500001"
    assert row["league"] == "NBA"
    assert row["event_name"] == "Los Angeles Lakers at Denver Nuggets"
    assert row["venue"] == "Ball Arena"


def test_fetch_nba_schedule_returns_json(monkeypatch):
    class FakeResponse:
        def get_dict(self):
            return {"leagueSchedule": {"gameDates": []}}

    class FakeScheduleLeagueV2:
        def __init__(self, timeout):
            assert timeout == nba_module.HTTP_TIMEOUT_SECONDS
            self.nba_response = FakeResponse()

    monkeypatch.setattr(nba_module, "ScheduleLeagueV2", FakeScheduleLeagueV2)
    assert nba_module.fetch_nba_schedule() == {"leagueSchedule": {"gameDates": []}}


def test_cs_parser_builds_event_rows():
    frame = _matches_to_frame(
        [
            {
                "id": "2371201",
                "date": "2026-01-02",
                "time": "12:30",
                "team1": "MOUZ",
                "team2": "FaZe",
                "event": "IEM",
                "maps": "3",
                "rating": "2",
            }
        ]
    )
    row = frame.to_dicts()[0]
    assert row["source_event_id"] == "2371201"
    assert row["event_name"] == "MOUZ vs FaZe"
    assert row["tournament"] == "IEM"
    assert row["rating"] == 2


def test_ufc_parsers_build_event_and_fighter_rows():
    events = _events_to_frame(
        [
            {
                "source_event_id": "abc",
                "event_name": "UFC 999",
                "event_start": datetime(2026, 1, 2, tzinfo=UTC),
                "location": "Las Vegas, Nevada, USA",
                "source_url": "http://ufcstats.com/event-details/abc",
            }
        ]
    )
    fighters = _fighters_to_frame(
        [
            {
                "source_event_id": "abc",
                "fighter_id": "f1",
                "fighter_name": "Example Fighter",
                "bout_id": "b1",
                "corner": "red",
                "outcome": "next",
            }
        ]
    )

    assert events.to_dicts()[0]["league"] == "UFC"
    assert fighters.to_dicts()[0]["fighter_id"] == "f1"


def test_espn_ufc_parser_builds_events_and_fighters():
    event_start = datetime.now(UTC) + timedelta(days=3)
    events, fighters, stats = ufc_module._parse_espn_scoreboard(
        {
            "events": [
                {
                    "id": "600123",
                    "date": event_start.isoformat().replace("+00:00", "Z"),
                    "name": "UFC Fight Night: Fiziev vs. Torres",
                    "competitions": [
                        {
                            "id": "401999",
                            "status": {"type": {"name": "STATUS_SCHEDULED"}},
                            "venue": {
                                "fullName": "Meta APEX",
                                "address": {
                                    "city": "Las Vegas",
                                    "state": "NV",
                                    "country": "USA",
                                },
                            },
                            "competitors": [
                                {
                                    "id": "1",
                                    "athlete": {"displayName": "Rafael Fiziev"},
                                },
                                {
                                    "id": "2",
                                    "athlete": {"displayName": "Manuel Torres"},
                                },
                            ],
                        }
                    ],
                }
            ]
        }
    )

    assert stats["events_in_payload"] == 1
    assert events[0]["source_event_id"] == "600123"
    assert events[0]["event_name"] == "UFC Fight Night: Fiziev vs. Torres"
    assert fighters[0]["fighter_name"] == "Rafael Fiziev"
    assert fighters[1]["corner"] == "blue"


def test_ufc_upcoming_asset_fetches_once_per_run(monkeypatch):
    calls: list[str] = []
    event_start = datetime.now(UTC) + timedelta(days=2)

    def fake_fetch():
        calls.append("fetch")
        return {
            "events": [
                {
                    "id": "600123",
                    "date": event_start.isoformat().replace("+00:00", "Z"),
                    "name": "UFC Fight Night",
                    "competitions": [
                        {
                            "id": "401999",
                            "competitors": [
                                {"id": "1", "athlete": {"displayName": "A"}},
                                {"id": "2", "athlete": {"displayName": "B"}},
                            ],
                        }
                    ],
                }
            ]
        }

    monkeypatch.setattr(ufc_module, "_fetch_espn_scoreboard", fake_fetch)
    result = materialize([ufc_upcoming])
    assert result.success
    assert calls == ["fetch"]
    payload = result.output_for_node("ufc_upcoming")
    assert len(payload["events"]) == 1
    assert len(payload["fighters"]) == 2


def test_log_landing_summary_emits_metadata():
    class FakeLog:
        messages: list[str] = []

        def info(self, message: str) -> None:
            self.messages.append(message)

    class FakeContext:
        log = FakeLog()

    metadata = log_landing_summary(
        cast(AssetExecutionContext, FakeContext()),
        source="test",
        fetched=10,
        parsed=9,
        after_window=3,
        merged=3,
        forward_window_days=21,
        detail="example",
    )
    assert "fetched=10" in FakeLog.messages[0]
    assert metadata["rows_merged"].value == 3


def test_daily_events_schedule_timezone():
    assert daily_events_schedule.cron_schedule == "0 6 * * *"
    assert daily_events_schedule.execution_timezone == "America/Los_Angeles"
