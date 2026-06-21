import pytest
from dagster import build_hook_context, job, op

from dagster_project.ops import slack_on_failure, slack_on_success
from dagster_project.ops.hooks import slack_on_failure as failure_hook
from dagster_project.ops.hooks import slack_on_success as success_hook
from dagster_project.resources import SlackResource

pytestmark = pytest.mark.unit


@op
def sample_op() -> None:
    return None


@job
def sample_job() -> None:
    sample_op()


def test_package_exports_hook_symbols():
    assert failure_hook is slack_on_failure
    assert success_hook is slack_on_success


def test_slack_on_failure_hook_posts_message(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(
        "dagster_project.resources.slack.urllib.request.urlopen",
        lambda req, timeout=None: calls.append(req.full_url) or None,
    )
    context = build_hook_context(
        op=sample_op,
        run_id="abcdef1234567890",
        resources={"slack": SlackResource(webhook_url="https://hooks.example/x")},
    )
    slack_on_failure.decorated_fn(context)
    assert len(calls) == 1


def test_slack_on_success_hook_posts_message(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(
        "dagster_project.resources.slack.urllib.request.urlopen",
        lambda req, timeout=None: calls.append(req.full_url) or None,
    )
    context = build_hook_context(
        op=sample_op,
        run_id="abcdef1234567890",
        resources={"slack": SlackResource(webhook_url="https://hooks.example/x")},
    )
    slack_on_success.decorated_fn(context)
    assert len(calls) == 1
