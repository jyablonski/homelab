from dagster import (
    AssetCheckResult,
    AssetExecutionContext,
    MetadataValue,
    asset,
    asset_check,
)

from dagster_project.resources import PostgresResource
from dagster_project.sql import ingestion as sql

GROUP = "ingestion"


@asset(
    group_name=GROUP,
    compute_kind="postgres",
    description="Read the source reminders table and publish row-count freshness metadata.",
)
def reminders_raw(context: AssetExecutionContext, postgres: PostgresResource) -> int:
    """Row count of the source reminders table, with the latest timestamp.

    Returns the count so downstream assets can depend on it via the parameter
    name ``reminders_raw``.
    """
    count = postgres.fetch_value(sql.COUNT_REMINDERS) or 0
    latest = postgres.fetch_value(sql.LATEST_REMINDER_TS)

    context.add_output_metadata(
        {
            "row_count": MetadataValue.int(count),
            "latest_created_at": MetadataValue.text(str(latest)),
        }
    )
    return count


@asset_check(asset=reminders_raw)
def reminders_raw_non_negative(reminders_raw: int) -> AssetCheckResult:
    """Reminder counts should never be negative."""
    return AssetCheckResult(
        passed=reminders_raw >= 0,
        metadata={"row_count": MetadataValue.int(reminders_raw)},
    )
