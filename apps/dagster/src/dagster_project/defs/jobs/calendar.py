from __future__ import annotations
from dagster import AssetSelection

from dagster_project.common.docs import load_doc
from dagster_project.defs.jobs.utils import Audience, Domain, create_job

# Kept separate from daily_events_job (jobs/events.py) so a Google auth failure
# does not make the sports event syncs look failed, and vice versa.
calendar_sync_job, calendar_sync_schedule = create_job(
    name="calendar_sync",
    selection=AssetSelection.groups("google_calendar"),
    audience=Audience.INTERNAL,
    domain=Domain.CALENDAR,
    pii=True,
    description=load_doc("events_google_calendar.md"),
    schedule="0 */6 * * *",
    execution_timezone="America/Los_Angeles",
)
