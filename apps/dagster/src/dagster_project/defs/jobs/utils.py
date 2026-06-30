from __future__ import annotations
from collections.abc import Iterable
from enum import StrEnum
from typing import Any, cast, overload

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

# What the definitions autoloader collects from the jobs package.
JobLike = JobDefinition | UnresolvedAssetJobDefinition


class Audience(StrEnum):
    """Allowed job audience tag values."""

    INTERNAL = "internal"
    USER_FACING = "user-facing"


class Domain(StrEnum):
    """Allowed job domain tag values."""

    EVENTS = "events"
    REMINDERS = "reminders"
    EXAMPLES = "examples"


def standard_tags(*, audience: Audience, domain: Domain, pii: bool) -> dict[str, str]:
    """Build the standard tag set expected on every registered Dagster job."""
    return {
        "audience": Audience(audience).value,
        "domain": Domain(domain).value,
        "pii": str(pii).lower(),
    }


def schedule_for_job(
    *,
    job: Any,
    cron_schedule: str,
    name: str | None = None,
    execution_timezone: str | None = None,
) -> ScheduleDefinition:
    """Create a schedule for a job with optional explicit name and timezone."""
    return ScheduleDefinition(
        name=name or f"{job.name}_schedule",
        job=job,
        cron_schedule=cron_schedule,
        execution_timezone=execution_timezone,
    )


@overload
def create_job(
    *,
    name: str,
    audience: Audience,
    domain: Domain,
    pii: bool,
    assets: Iterable[Any] | None = ...,
    selection: AssetSelection | None = ...,
    schedule: None = None,
    schedule_name: str | None = ...,
    execution_timezone: str | None = ...,
    description: str | None = ...,
    hooks: Any = ...,
) -> JobLike: ...


@overload
def create_job(
    *,
    name: str,
    audience: Audience,
    domain: Domain,
    pii: bool,
    assets: Iterable[Any] | None = ...,
    selection: AssetSelection | None = ...,
    schedule: str,
    schedule_name: str | None = ...,
    execution_timezone: str | None = ...,
    description: str | None = ...,
    hooks: Any = ...,
) -> tuple[JobLike, ScheduleDefinition]: ...


def create_job(
    *,
    name: str,
    audience: Audience,
    domain: Domain,
    pii: bool,
    assets: Iterable[Any] | None = None,
    selection: AssetSelection | None = None,
    schedule: str | None = None,
    schedule_name: str | None = None,
    execution_timezone: str | None = None,
    description: str | None = None,
    hooks: Any = None,
) -> JobLike | tuple[JobLike, ScheduleDefinition]:
    """Create a standard asset job, optionally paired with a cron schedule.

    Pass either ``assets`` for direct asset definitions/keys or ``selection`` for
    a prebuilt Dagster selection. Returns the job when ``schedule`` is omitted,
    or ``(job, schedule)`` when ``schedule`` is provided.
    """
    if assets is None and selection is None:
        raise ValueError("Pass exactly one of assets or selection")

    if assets is not None and selection is not None:
        raise ValueError("Pass exactly one of assets or selection")

    if selection is not None:
        job_selection: AssetSelection = selection
    else:
        selected_assets = cast(Iterable[Any], assets)
        job_selection = AssetSelection.assets(*selected_assets)

    job = define_asset_job(
        name=name,
        selection=job_selection,
        tags=standard_tags(audience=audience, domain=domain, pii=pii),
        description=description,
        hooks=hooks,
    )

    if schedule is None:
        return job

    return job, schedule_for_job(
        job=job,
        cron_schedule=schedule,
        name=schedule_name,
        execution_timezone=execution_timezone,
    )
