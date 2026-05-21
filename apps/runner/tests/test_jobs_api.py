from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from jobs_api import (
    _relative_time,
    run_to_history_item,
    run_to_response,
    runnable_to_job,
)
from models import JobRun, Runnable


def test_runnable_to_job_maps_fields():
    runnable = Runnable(
        namespace="apps",
        cronjob_name="api-print-reminders-rows",
        app="api",
        job="print-reminders-rows",
        description="Print reminder table row count",
        schedule="0 */6 * * *",
        suspended=False,
        last_run="api-print-reminders-rows-manual-1",
        last_status="Succeeded",
        last_logs_url="http://grafana.home/explore?left=test",
    )
    runs = [
        JobRun(
            namespace="apps",
            name="api-print-reminders-rows-manual-1",
            app="api",
            job="print-reminders-rows",
            status="Succeeded",
            started_at=datetime(2026, 5, 21, 9, 0, tzinfo=UTC).isoformat(),
            logs_url="http://grafana.home/explore?left=test",
        ),
        JobRun(
            namespace="apps",
            name="api-print-reminders-rows-manual-0",
            app="api",
            job="print-reminders-rows",
            status="Failed",
        ),
    ]

    job = runnable_to_job(runnable, runs=runs)

    assert job["app"] == "api"
    assert job["name"] == "print-reminders-rows"
    assert job["schedule"]["manual"] is False
    assert job["status"] == "success"
    assert job["lastRun"]["id"] == "api-print-reminders-rows-manual-1"
    assert job["history"] == ["failed", "success"]


def test_run_to_history_item_maps_fields():
    run = JobRun(
        namespace="apps",
        name="api-print-reminders-rows-manual-1",
        app="api",
        job="print-reminders-rows",
        status="Succeeded",
        started_at="2026-05-21T12:00:00+00:00",
        completed_at="2026-05-21T12:00:30+00:00",
        logs_url="http://grafana.home/explore?left=test",
    )

    item = run_to_history_item(run)

    assert item["id"] == run.name
    assert item["status"] == "success"
    assert item["k8sStatus"] == "Succeeded"
    assert item["grafanaUrl"] == run.logs_url


def test_run_to_response_maps_fields():
    run = JobRun(
        namespace="apps",
        name="api-print-reminders-rows-manual-1",
        app="api",
        job="print-reminders-rows",
        status="Succeeded",
        logs_url="http://grafana.home/explore?left=test",
    )

    assert run_to_response(run) == {
        "runId": run.name,
        "namespace": "apps",
        "grafanaUrl": run.logs_url,
    }


@pytest.mark.parametrize(
    ("runnable", "runs", "expected_status"),
    [
        (
            Runnable(
                namespace="apps",
                cronjob_name="api-job",
                app="api",
                job="job",
                description="",
                schedule="0 0 * * *",
                suspended=True,
                active_run="api-job-active",
            ),
            [],
            "running",
        ),
        (
            Runnable(
                namespace="apps",
                cronjob_name="api-job",
                app="api",
                job="job",
                description="",
                schedule="0 0 * * *",
                suspended=True,
            ),
            [],
            "idle",
        ),
    ],
)
def test_runnable_to_job_status_variants(runnable, runs, expected_status):
    job = runnable_to_job(runnable, runs=runs)
    assert job["status"] == expected_status
    assert job["lastRun"] is None


def test_runnable_to_job_last_run_running_maps_to_running():
    runnable = Runnable(
        namespace="apps",
        cronjob_name="api-job",
        app="api",
        job="job",
        description="",
        schedule="0 0 * * *",
        suspended=False,
    )
    runs = [
        JobRun(
            namespace="apps",
            name="api-job-1",
            app="api",
            job="job",
            status="Running",
        ),
    ]

    assert runnable_to_job(runnable, runs=runs)["status"] == "running"


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("Succeeded", "success"),
        ("Failed", "failed"),
        ("Running", "running"),
        ("Pending", "pending"),
    ],
)
def test_history_state_mapping(status, expected):
    runnable = Runnable(
        namespace="apps",
        cronjob_name="api-job",
        app="api",
        job="job",
        description="",
        schedule="0 0 * * *",
        suspended=False,
    )
    runs = [
        JobRun(
            namespace="apps",
            name="api-job-1",
            app="api",
            job="job",
            status=status,
        ),
    ]

    assert runnable_to_job(runnable, runs=runs)["history"] == [expected]


@pytest.mark.parametrize(
    ("seconds_ago", "expected"),
    [
        (30, "just now"),
        (5 * 60, "5m ago"),
        (3 * 3600, "3h ago"),
        (2 * 86400, "2d ago"),
    ],
)
def test_relative_time_buckets(seconds_ago, expected):
    at = datetime(2026, 5, 21, 12, 0, tzinfo=UTC) - timedelta(seconds=seconds_ago)

    with patch("jobs_api.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2026, 5, 21, 12, 0, tzinfo=UTC)
        mock_datetime.fromisoformat = datetime.fromisoformat
        mock_datetime.UTC = UTC
        result = _relative_time(at.isoformat())

    assert result == expected


def test_relative_time_handles_z_suffix_and_naive_timestamps():
    with patch("jobs_api.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2026, 5, 21, 12, 0, tzinfo=UTC)
        mock_datetime.fromisoformat = datetime.fromisoformat
        mock_datetime.UTC = UTC

        assert _relative_time("2026-05-21T11:59:00Z") == "1m ago"
        assert _relative_time("2026-05-21T11:00:00") == "1h ago"


@pytest.mark.parametrize("value", [None, "", "not-a-date"])
def test_relative_time_returns_none_for_missing_or_invalid(value):
    assert _relative_time(value) is None
