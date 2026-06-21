from dagster import AssetExecutionContext, MetadataValue, asset

from dagster_project.resources import PostgresResource
from dagster_project.sql import exports as sql

GROUP = "exports"


@asset(group_name=GROUP, compute_kind="postgres")
def reminders_summary_export(
    context: AssetExecutionContext,
    postgres: PostgresResource,
    reminders_daily: dict[str, int],
) -> None:
    """Upsert today's reminder count into ``source.reminders_summary``."""
    count = reminders_daily["reminder_count"]
    postgres.execute(sql.CREATE_REMINDERS_SUMMARY)
    postgres.execute(sql.UPSERT_REMINDERS_SUMMARY, (count,))

    context.add_output_metadata(
        {
            "destination": MetadataValue.text("source.reminders_summary"),
            "reminder_count": MetadataValue.int(count),
        }
    )
