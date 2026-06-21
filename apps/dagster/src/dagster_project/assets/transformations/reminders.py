from dagster import AssetExecutionContext, MetadataValue, asset

GROUP = "transformations"


@asset(
    group_name=GROUP,
    compute_kind="python",
    description="Shape raw reminder metrics into the daily reminder summary payload.",
)
def reminders_daily(
    context: AssetExecutionContext, reminders_raw: int
) -> dict[str, int]:
    """Shape the raw reminder count into the export payload.

    Depends on ``reminders_raw`` through the parameter name, so Dagster wires
    the dependency automatically.
    """
    payload = {"reminder_count": reminders_raw}
    context.add_output_metadata({"reminder_count": MetadataValue.int(reminders_raw)})
    return payload
