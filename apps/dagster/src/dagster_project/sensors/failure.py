from dagster import (
    DefaultSensorStatus,
    RunFailureSensorContext,
    run_failure_sensor,
)

from dagster_project.resources import SlackResource


@run_failure_sensor(
    name="slack_run_failure_sensor",
    default_status=DefaultSensorStatus.RUNNING,
)
def slack_run_failure_sensor(
    context: RunFailureSensorContext, slack: SlackResource
) -> None:
    """Post a message when any run fails. No-op when Slack is unconfigured."""
    slack.send_message(
        f":x: Dagster run failed: *{context.dagster_run.job_name}* "
        f"({context.dagster_run.run_id[:8]})\n{context.failure_event.message}"
    )
