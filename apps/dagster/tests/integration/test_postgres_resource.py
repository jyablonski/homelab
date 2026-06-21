from __future__ import annotations
from datetime import UTC, datetime, timedelta

import polars as pl
import pytest
from dagster import materialize

from dagster_project.assets.ingestion import events_nba as nba_module
from dagster_project.assets.ingestion import events_ufc as ufc_module
from dagster_project.assets.ingestion.events_cs import events_cs
from dagster_project.assets.ingestion.events_nba import events_nba
from dagster_project.assets.ingestion.events_ufc import (
    events_ufc,
    events_ufc_fighters,
    ufc_upcoming,
)
from dagster_project.resources import HLTVResource

pytestmark = pytest.mark.integration


class FakeHLTVResource(HLTVResource):
    def fetch_upcoming(self):
        event_start = datetime.now(UTC) + timedelta(days=1)
        return [
            {
                "id": "cs-1",
                "date": event_start.strftime("%Y-%m-%d"),
                "time": event_start.strftime("%H:%M"),
                "team1": "MOUZ",
                "team2": "FaZe",
                "event": "IEM",
            }
        ]


def test_execute_and_fetch_methods_use_real_postgres(real_postgres):
    real_postgres.execute(
        """
        CREATE TABLE source.integration_values (
            id integer PRIMARY KEY,
            name text NOT NULL
        )
        """
    )
    real_postgres.execute(
        "INSERT INTO source.integration_values (id, name) VALUES (%s, %s)",
        (1, "alpha"),
    )

    assert real_postgres.fetch_value("SELECT name FROM integration_values") == "alpha"
    assert real_postgres.fetch_all("SELECT id, name FROM integration_values") == [
        (1, "alpha")
    ]
    assert real_postgres.fetch_value("SELECT 1 WHERE false") is None


def test_merge_polars_empty_frame_noops(real_postgres):
    rows = real_postgres.merge_polars(
        pl.DataFrame(schema={"source_event_id": pl.String}),
        target="source.events_nba",
        conflict_keys=["source_event_id"],
        update_cols=["source_event_id"],
    )
    assert rows == 0
    assert real_postgres.fetch_value("SELECT count(*) FROM events_nba") == 0


def test_merge_polars_inserts_and_updates_rows(real_postgres):
    first = _nba_frame("nba-1", "Lakers at Nuggets", "Scheduled")
    second = _nba_frame("nba-1", "Lakers at Nuggets", "Final")

    assert (
        real_postgres.merge_polars(
            first,
            target="source.events_nba",
            conflict_keys=["source_event_id"],
            update_cols=[
                "league",
                "event_name",
                "event_start",
                "status",
                "home_team",
                "away_team",
                "venue",
                "source",
                "modified_at",
            ],
        )
        == 1
    )
    assert (
        real_postgres.merge_polars(
            second,
            target="source.events_nba",
            conflict_keys=["source_event_id"],
            update_cols=["status", "modified_at"],
        )
        == 1
    )

    assert real_postgres.fetch_all(
        "SELECT source_event_id, event_name, status FROM events_nba"
    ) == [("nba-1", "Lakers at Nuggets", "Final")]


def test_event_assets_materialize_into_real_postgres(
    monkeypatch,
    real_postgres,
):
    monkeypatch.setattr(nba_module, "fetch_nba_schedule", _fake_nba_payload)
    monkeypatch.setattr(ufc_module, "_fetch_espn_scoreboard", _fake_espn_payload)

    result = materialize(
        [events_nba, events_cs, ufc_upcoming, events_ufc, events_ufc_fighters],
        resources={
            "hltv": FakeHLTVResource(),
            "postgres": real_postgres,
        },
    )

    assert result.success
    assert real_postgres.fetch_value("SELECT count(*) FROM events_nba") == 1
    assert real_postgres.fetch_value("SELECT count(*) FROM events_cs") == 1
    assert real_postgres.fetch_value("SELECT count(*) FROM events_ufc") == 1
    assert real_postgres.fetch_value("SELECT count(*) FROM events_ufc_fighters") == 2


def _nba_frame(source_event_id: str, event_name: str, status: str) -> pl.DataFrame:
    event_start = datetime.now(UTC) + timedelta(days=1)
    modified_at = datetime.now(UTC)
    return pl.DataFrame(
        [
            {
                "source_event_id": source_event_id,
                "league": "NBA",
                "event_name": event_name,
                "event_start": event_start,
                "status": status,
                "home_team": "Denver Nuggets",
                "away_team": "Los Angeles Lakers",
                "venue": "Ball Arena",
                "source": "nba",
                "modified_at": modified_at,
            }
        ]
    )


def _fake_nba_payload() -> dict:
    event_start = datetime.now(UTC) + timedelta(days=1)
    return {
        "leagueSchedule": {
            "gameDates": [
                {
                    "games": [
                        {
                            "gameId": "nba-1",
                            "gameDateTimeUTC": event_start.isoformat(),
                            "homeTeam": {"teamName": "Nuggets"},
                            "awayTeam": {"teamName": "Lakers"},
                        }
                    ]
                }
            ]
        }
    }


def _fake_espn_payload() -> dict:
    event_start = datetime.now(UTC) + timedelta(days=1)
    return {
        "events": [
            {
                "id": "ufc-1",
                "date": event_start.isoformat().replace("+00:00", "Z"),
                "name": "UFC 999",
                "competitions": [
                    {
                        "id": "bout-1",
                        "competitors": [
                            {
                                "id": "fighter-1",
                                "athlete": {"displayName": "Example Fighter"},
                            },
                            {
                                "id": "fighter-2",
                                "athlete": {"displayName": "Other Fighter"},
                            },
                        ],
                    }
                ],
            }
        ]
    }
