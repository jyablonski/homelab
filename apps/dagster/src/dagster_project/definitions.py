from __future__ import annotations
import importlib
import pkgutil
from os import getenv
from types import ModuleType
from typing import get_args

from dagster import (
    Definitions,
    ScheduleDefinition,
    SensorDefinition,
    load_asset_checks_from_modules,
    load_assets_from_modules,
)

from dagster_project.dbt_config import dbt_resource
from dagster_project.defs import assets as assets_pkg
from dagster_project.defs import jobs as jobs_pkg
from dagster_project.defs import sensors as sensors_pkg
from dagster_project.defs.jobs.utils import JobLike
from dagster_project.resources import RESOURCES


def include_examples() -> bool:
    return getenv("DAGSTER_INCLUDE_EXAMPLES", "").lower() in {"1", "true", "yes"}


def _is_example_module(name: str) -> bool:
    """Match demo modules: the ``internal`` asset package and ``example*`` files."""
    leaf = name.rsplit(".", 1)[-1]
    return ".internal" in name or leaf.startswith("example")


def discover_modules(package: ModuleType, *, with_examples: bool) -> list[ModuleType]:
    """Import and return every submodule of ``package`` (recursively)."""
    modules: list[ModuleType] = []
    for info in pkgutil.walk_packages(package.__path__, prefix=f"{package.__name__}."):
        if info.ispkg:
            continue
        if not with_examples and _is_example_module(info.name):
            continue
        modules.append(importlib.import_module(info.name))
    return modules


def _collect(modules: list[ModuleType], types: tuple[type, ...]) -> list:
    """Return distinct top-level objects of the given types across modules."""
    found: list = []
    seen: set[int] = set()
    for module in modules:
        for value in vars(module).values():
            if isinstance(value, types) and id(value) not in seen:
                seen.add(id(value))
                found.append(value)
    return found


def build_definitions(*, with_examples: bool | None = None) -> Definitions:
    with_examples = include_examples() if with_examples is None else with_examples

    asset_modules = discover_modules(assets_pkg, with_examples=with_examples)
    job_modules = discover_modules(jobs_pkg, with_examples=with_examples)
    sensor_modules = discover_modules(sensors_pkg, with_examples=with_examples)

    assets = load_assets_from_modules(asset_modules)
    asset_checks = load_asset_checks_from_modules(asset_modules)
    jobs = _collect(job_modules, get_args(JobLike))
    schedules = _collect(job_modules + sensor_modules, (ScheduleDefinition,))
    sensors = _collect(sensor_modules, (SensorDefinition,))

    resources = dict(RESOURCES)
    if dbt_resource is not None:
        resources["dbt"] = dbt_resource

    return Definitions(
        assets=assets,
        asset_checks=asset_checks,
        jobs=jobs,
        schedules=schedules,
        sensors=sensors,
        resources=resources,
    )


defs = build_definitions()
