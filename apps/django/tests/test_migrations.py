import os
import subprocess

import pytest


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
