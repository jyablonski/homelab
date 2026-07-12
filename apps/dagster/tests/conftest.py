from __future__ import annotations
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
SOURCE_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "django/schema/source.sql"


@pytest.fixture(scope="session")
def postgres_container():
    container = PostgresContainer(
        "postgres:17-alpine",
        username="postgres",
        password="postgres",
        dbname="postgres",
    )
    container.with_volume_mapping(
        str(SOURCE_SCHEMA_PATH),
        "/docker-entrypoint-initdb.d/01-source.sql",
        mode="ro",
    )
    with container as running_container:
        yield running_container


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
