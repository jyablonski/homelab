from dagster import HookContext, failure_hook, success_hook

from dagster_project.resources import SlackResource


@failure_hook(required_resource_keys={"slack"})
def slack_on_failure(context: HookContext) -> None:
    slack: SlackResource = context.resources.slack
    slack.send_message(f":x: op `{context.op.name}` failed in run {context.run_id[:8]}")


@success_hook(required_resource_keys={"slack"})
def slack_on_success(context: HookContext) -> None:
    slack: SlackResource = context.resources.slack
    slack.send_message(f":white_check_mark: op `{context.op.name}` succeeded")
