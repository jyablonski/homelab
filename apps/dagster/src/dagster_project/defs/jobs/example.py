from __future__ import annotations
from dagster import AssetSelection

from dagster_project.defs.jobs.utils import Audience, Domain, create_job

example_job = create_job(
    name="example_job",
    selection=AssetSelection.groups("examples"),
    audience=Audience.INTERNAL,
    domain=Domain.EXAMPLES,
    pii=False,
    description="Materialize the demo example assets.",
)
