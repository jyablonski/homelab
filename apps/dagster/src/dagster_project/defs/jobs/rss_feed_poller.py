from __future__ import annotations

from dagster_project.common.docs import load_doc
from dagster_project.defs.jobs.utils import Audience, Domain, create_op_job
from dagster_project.ops.rss_feed_poller import (
    DEFAULT_RUN_CONFIG,
    rss_feed_poller,
)

rss_feed_poller_job, rss_feed_poller_schedule = create_op_job(
    name="rss_feed_poller",
    op_fn=rss_feed_poller,
    audience=Audience.INTERNAL,
    domain=Domain.RSS,
    pii=False,
    description=load_doc("rss_feed_poller.md"),
    schedule="*/30 * * * *",
    execution_timezone="America/Los_Angeles",
    run_config=DEFAULT_RUN_CONFIG,
)
