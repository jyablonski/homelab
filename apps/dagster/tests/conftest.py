from __future__ import annotations
import os
import subprocess
from pathlib import Path

import pytest
from testcontainers.postgres import PostgresContainer

from dagster_project.resources import PostgresResource

EVENT_LANDING_TABLES = (
    "source.events_nba",
    "source.events_cs",
    "source.events_ufc",
    "source.events_ufc_fighters",
)
DJANGO_APP_DIR = Path(__file__).resolve().parents[2] / "django"


def _run_django_migrate(container: PostgresContainer) -> None:
    env = os.environ.copy()
    env.update(
        {
            "DB_USER": "postgres",
            "DB_PASSWORD": "postgres",
            "DB_HOST": container.get_container_host_ip(),
            "DB_PORT": str(container.get_exposed_port(5432)),
            "DB_NAME": "postgres",
            "DJANGO_SUPERUSER_USERNAME": "postgres",
            "DJANGO_SUPERUSER_PASSWORD": "postgres",
            "DJANGO_SETTINGS_MODULE": "core.settings",
        }
    )
    subprocess.run(
        ["uv", "run", "python", "src/manage.py", "migrate", "--noinput"],
        cwd=DJANGO_APP_DIR,
        env=env,
        check=True,
    )


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer(
        "postgres:17-alpine",
        username="postgres",
        password="postgres",
        dbname="postgres",
    ) as container:
        _run_django_migrate(container)
        yield container


@pytest.fixture
def postgres_resource(postgres_container) -> PostgresResource:
    """A real PostgresResource with clean event landing tables for each test."""
    resource = PostgresResource(
        host=postgres_container.get_container_host_ip(),
        port=str(postgres_container.get_exposed_port(5432)),
        database="postgres",
        user="postgres",
        password="postgres",
        connect_timeout=10,
    )
    table_list = ", ".join(EVENT_LANDING_TABLES)
    resource.execute(f"TRUNCATE {table_list} RESTART IDENTITY CASCADE")
    resource.execute("DROP TABLE IF EXISTS source.integration_values")
    resource.execute("DROP TABLE IF EXISTS source.reminders CASCADE")
    resource.execute("DROP TABLE IF EXISTS source.reminders_summary CASCADE")
    return resource


@pytest.fixture
def real_postgres(postgres_resource) -> PostgresResource:
    return postgres_resource
