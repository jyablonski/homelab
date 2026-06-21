from types import SimpleNamespace
from typing import cast

import pytest
from dagster import RunFailureSensorContext

from dagster_project.resources import SlackResource
from dagster_project.sensors.failure import notify_slack_run_failure

pytestmark = pytest.mark.unit


def test_slack_run_failure_sensor_posts_message(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(
        "dagster_project.resources.slack.urllib.request.urlopen",
        lambda req, timeout=None: calls.append(req.full_url) or None,
    )

    context = SimpleNamespace(
        dagster_run=SimpleNamespace(job_name="daily_events", run_id="abcdef1234567890"),
        failure_event=SimpleNamespace(message="step failed"),
    )
    slack = SlackResource(webhook_url="https://hooks.example/x")

    notify_slack_run_failure(cast(RunFailureSensorContext, context), slack)

    assert len(calls) == 1
