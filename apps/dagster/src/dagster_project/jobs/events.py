from __future__ import annotations
from dagster import AssetSelection

from dagster_project.jobs.utils import create_job

nba_job = create_job(
    "nba_job",
    AssetSelection.groups("nba"),
    domain="events",
    description="Refresh upcoming NBA games.",
)

cs_job = create_job(
    "cs_job",
    AssetSelection.groups("cs"),
    domain="events",
    description="Refresh upcoming CS2 matches from HLTV.",
)

ufc_job = create_job(
    "ufc_job",
    AssetSelection.groups("ufc"),
    domain="events",
    description="Refresh upcoming UFC cards and fighters.",
)

daily_events_job, daily_events_schedule = create_job(
    "daily_events",
    AssetSelection.groups("nba", "cs", "ufc"),
    domain="events",
    description="Refresh upcoming event landing tables for all configured sources.",
    cron_schedule="0 6 * * *",
    execution_timezone="America/Los_Angeles",
)
