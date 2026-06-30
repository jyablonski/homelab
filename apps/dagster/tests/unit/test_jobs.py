import pytest
from dagster import AssetSelection, ScheduleDefinition

from dagster_project.defs.jobs.utils import (
    Audience,
    Domain,
    UnresolvedAssetJobDefinition,
    create_job,
    schedule_for_job,
    standard_tags,
)

pytestmark = pytest.mark.unit


def test_create_job_without_schedule_returns_job_only():
    job = create_job(
        name="j",
        selection=AssetSelection.all(),
        audience=Audience.INTERNAL,
        domain=Domain.EVENTS,
        pii=False,
    )
    assert isinstance(job, UnresolvedAssetJobDefinition)


def test_create_job_with_schedule_returns_pair():
    job, schedule = create_job(
        name="j",
        selection=AssetSelection.all(),
        audience=Audience.INTERNAL,
        domain=Domain.EVENTS,
        pii=False,
        schedule="0 0 * * *",
    )
    assert isinstance(job, UnresolvedAssetJobDefinition)
    assert isinstance(schedule, ScheduleDefinition)
    assert schedule.cron_schedule == "0 0 * * *"
    assert schedule.name == "j_schedule"


def test_create_job_sets_standard_tags():
    job = create_job(
        name="j",
        selection=AssetSelection.all(),
        audience=Audience.USER_FACING,
        domain=Domain.REMINDERS,
        pii=True,
    )
    tags = job.tags or {}
    assert tags["audience"] == "user-facing"
    assert tags["domain"] == "reminders"
    assert tags["pii"] == "true"


def test_create_job_accepts_assets_instead_of_selection():
    other = create_job(
        name="other",
        selection=AssetSelection.all(),
        audience=Audience.INTERNAL,
        domain=Domain.EVENTS,
        pii=False,
    )
    assert isinstance(other, UnresolvedAssetJobDefinition)


def test_create_job_requires_exactly_one_target():
    with pytest.raises(ValueError):
        create_job(
            name="j",
            audience=Audience.INTERNAL,
            domain=Domain.EVENTS,
            pii=False,
        )
    with pytest.raises(ValueError):
        create_job(
            name="j",
            assets=[],
            selection=AssetSelection.all(),
            audience=Audience.INTERNAL,
            domain=Domain.EVENTS,
            pii=False,
        )


def test_standard_tags_lowercases_pii():
    assert standard_tags(
        audience=Audience.INTERNAL, domain=Domain.EXAMPLES, pii=False
    ) == {"audience": "internal", "domain": "examples", "pii": "false"}


def test_schedule_for_job_honors_explicit_name_and_timezone():
    job = create_job(
        name="j",
        selection=AssetSelection.all(),
        audience=Audience.INTERNAL,
        domain=Domain.EVENTS,
        pii=False,
    )
    schedule = schedule_for_job(
        job=job,
        cron_schedule="0 6 * * *",
        name="custom_schedule",
        execution_timezone="America/Los_Angeles",
    )
    assert schedule.name == "custom_schedule"
    assert schedule.execution_timezone == "America/Los_Angeles"
