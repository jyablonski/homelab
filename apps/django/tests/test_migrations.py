import importlib
import os
import subprocess

import pytest


def test_rss_feed_entries_migration_shape():
    migration_module = importlib.import_module("core.migrations.0007_rssfeedentry")
    migration = migration_module.Migration
    operation = migration.operations[0]

    assert migration.dependencies == [("core", "0006_eventsgooglecalendar")]
    assert operation.name == "RssFeedEntry"
    assert operation.options["db_table"] == "rss_feed_entries"
    assert any(
        constraint.name == "uniq_rss_feed_entries_feed_guid"
        for constraint in operation.options["constraints"]
    )


@pytest.mark.integration
def test_migrate_runs_against_container_db(django_db_env):
    if not os.path.exists("/var/run/docker.sock"):
        pytest.skip("Docker socket not available for testcontainers integration test")

    result = subprocess.run(
        ["python", "src/manage.py", "migrate", "--noinput"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
