from __future__ import annotations
from typing import overload

from dagster import (
    AssetSelection,
    JobDefinition,
    ScheduleDefinition,
    define_asset_job,
)

# Not exported from the top-level package; this is what define_asset_job returns.
from dagster._core.definitions.unresolved_asset_job_definition import (
    UnresolvedAssetJobDefinition,
)

JobLike = JobDefinition | UnresolvedAssetJobDefinition

# Standard tag keys every job is expected to set. Enforced in the test suite so
# new jobs stay self-describing.
TAG_AUDIENCE = "audience"
TAG_DOMAIN = "domain"
TAG_APP = "app"

DEFAULT_AUDIENCE = "jacob"
DEFAULT_APP = "dashboard"

REQUIRED_JOB_TAGS = (TAG_AUDIENCE, TAG_DOMAIN, TAG_APP)


@overload
def create_job(
    name: str,
    selection: AssetSelection,
    *,
    domain: str,
    audience: str = ...,
    app: str = ...,
    description: str | None = ...,
    extra_tags: dict[str, str] | None = ...,
) -> UnresolvedAssetJobDefinition: ...


@overload
def create_job(
    name: str,
    selection: AssetSelection,
    *,
    domain: str,
    audience: str = ...,
    app: str = ...,
    cron_schedule: str,
    execution_timezone: str | None = ...,
    description: str | None = ...,
    extra_tags: dict[str, str] | None = ...,
) -> tuple[UnresolvedAssetJobDefinition, ScheduleDefinition]: ...


def create_job(
    name: str,
    selection: AssetSelection,
    *,
    domain: str,
    audience: str = DEFAULT_AUDIENCE,
    app: str = DEFAULT_APP,
    description: str | None = None,
    cron_schedule: str | None = None,
    execution_timezone: str | None = None,
    extra_tags: dict[str, str] | None = None,
) -> (
    UnresolvedAssetJobDefinition
    | tuple[UnresolvedAssetJobDefinition, ScheduleDefinition]
):
    """Build an asset job with standard tags.

    Returns just the job, or ``(job, schedule)`` when ``cron_schedule`` is set.
    """
    tags = {
        TAG_AUDIENCE: audience,
        TAG_DOMAIN: domain,
        TAG_APP: app,
    }
    if extra_tags:
        tags.update(extra_tags)

    job = define_asset_job(
        name=name,
        selection=selection,
        description=description,
        tags=tags,
    )

    if cron_schedule is None:
        return job

    schedule = ScheduleDefinition(
        name=f"{name}_schedule",
        job=job,
        cron_schedule=cron_schedule,
        execution_timezone=execution_timezone,
    )
    return job, schedule
