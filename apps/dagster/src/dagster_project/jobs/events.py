from __future__ import annotations
from dagster import AssetSelection

from dagster_project.jobs.utils import create_job

daily_events_job, daily_events_schedule = create_job(
    "daily_events",
    AssetSelection.groups("nba", "cs", "ufc"),
    domain="events",
    description="Refresh upcoming event landing tables for all configured sources.",
    cron_schedule="0 6 * * *",
    execution_timezone="America/Los_Angeles",
)
