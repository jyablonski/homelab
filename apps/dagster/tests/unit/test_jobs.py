import pytest
from dagster import AssetSelection, ScheduleDefinition

from dagster_project.jobs.utils import (
    DEFAULT_APP,
    DEFAULT_AUDIENCE,
    JobTag,
    UnresolvedAssetJobDefinition,
    create_job,
)

pytestmark = pytest.mark.unit


def test_create_job_without_schedule_returns_job_only():
    job = create_job("j", AssetSelection.all(), domain="d")
    assert isinstance(job, UnresolvedAssetJobDefinition)


def test_create_job_with_schedule_returns_pair():
    result = create_job(
        "j",
        AssetSelection.all(),
        domain="d",
        cron_schedule="0 0 * * *",
    )
    job, schedule = result
    assert isinstance(job, UnresolvedAssetJobDefinition)
    assert isinstance(schedule, ScheduleDefinition)
    assert schedule.cron_schedule == "0 0 * * *"


def test_create_job_sets_standard_tags():
    job = create_job(
        "j",
        AssetSelection.all(),
        audience="jacob",
        domain="sales",
        app="dashboard",
    )
    tags = job.tags or {}
    assert tags[JobTag.AUDIENCE] == "jacob"
    assert tags[JobTag.DOMAIN] == "sales"
    assert tags[JobTag.APP] == "dashboard"


def test_create_job_defaults_audience_and_app():
    job = create_job("j", AssetSelection.all(), domain="d")
    tags = job.tags or {}
    assert tags[JobTag.AUDIENCE] == DEFAULT_AUDIENCE
    assert tags[JobTag.APP] == DEFAULT_APP


def test_create_job_merges_extra_tags():
    job = create_job(
        "j",
        AssetSelection.all(),
        domain="d",
        extra_tags={"team": "data"},
    )
    assert (job.tags or {})["team"] == "data"
