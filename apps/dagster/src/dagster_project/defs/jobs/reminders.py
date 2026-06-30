from __future__ import annotations

from dagster_project.defs.assets.exports.reminders import reminders_summary_export
from dagster_project.defs.assets.ingestion.reminders import reminders_raw
from dagster_project.defs.assets.transformations.reminders import reminders_daily
from dagster_project.defs.jobs.utils import Audience, Domain, create_job

reminders_job, reminders_schedule = create_job(
    name="reminders_pipeline",
    assets=[reminders_raw, reminders_daily, reminders_summary_export],
    audience=Audience.INTERNAL,
    domain=Domain.REMINDERS,
    pii=False,
    description="Refresh the daily reminders summary from the source database.",
    schedule="0 6 * * *",
)
