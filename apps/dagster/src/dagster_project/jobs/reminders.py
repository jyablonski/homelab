from __future__ import annotations
from dagster import AssetSelection

from dagster_project.assets.exports.reminders import reminders_summary_export
from dagster_project.assets.ingestion.reminders import reminders_raw
from dagster_project.assets.transformations.reminders import reminders_daily
from dagster_project.jobs.utils import create_job

reminders_selection = AssetSelection.assets(
    reminders_raw,
    reminders_daily,
    reminders_summary_export,
)

reminders_job, reminders_schedule = create_job(
    "reminders_pipeline",
    reminders_selection,
    domain="reminders",
    description="Refresh the daily reminders summary from the source database.",
    cron_schedule="0 6 * * *",
)
