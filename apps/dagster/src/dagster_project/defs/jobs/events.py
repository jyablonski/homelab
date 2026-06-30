from __future__ import annotations
from dagster import AssetSelection

from dagster_project.defs.jobs.utils import Audience, Domain, create_job

daily_events_job, daily_events_schedule = create_job(
    name="daily_events",
    selection=AssetSelection.groups("nba", "cs", "ufc"),
    audience=Audience.INTERNAL,
    domain=Domain.EVENTS,
    pii=False,
    description="Refresh upcoming event landing tables for all configured sources.",
    schedule="0 6 * * *",
    execution_timezone="America/Los_Angeles",
)
