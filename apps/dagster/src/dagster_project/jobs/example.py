from __future__ import annotations
from dagster import AssetSelection

from dagster_project.jobs.utils import create_job

example_job = create_job(
    "example_job",
    AssetSelection.groups("examples"),
    domain="examples",
    description="Materialize the demo example assets.",
)
