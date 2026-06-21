from types import SimpleNamespace

import pytest

from dagster_project.resources import SlackResource
from dagster_project.sensors.failure import slack_run_failure_sensor

pytestmark = pytest.mark.unit


def test_slack_run_failure_sensor_posts_message(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(
        "dagster_project.resources.slack.urllib.request.urlopen",
        lambda req, timeout=None: calls.append(req.full_url) or None,
    )

    context = SimpleNamespace(
        dagster_run=SimpleNamespace(job_name="nba_job", run_id="abcdef1234567890"),
        failure_event=SimpleNamespace(message="step failed"),
    )
    slack = SlackResource(webhook_url="https://hooks.example/x")

    slack_run_failure_sensor._run_status_sensor_fn(context, slack)

    assert len(calls) == 1
