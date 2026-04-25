import os

import pytest
from testcontainers.postgres import PostgresContainer


@pytest.fixture()
def postgres_url():
    if not os.path.exists("/var/run/docker.sock"):
        pytest.skip("Docker socket not available for testcontainers integration test")
    with PostgresContainer("postgres:17") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture()
def django_db_env(postgres_url):
    # Convert SQLAlchemy-style URL returned by testcontainers into Django env vars.
    # Example: postgresql+psycopg2://test:test@localhost:32768/test
    url = postgres_url.replace("postgresql+psycopg2://", "postgresql://")
    # Lazy parse to avoid adding extra deps.
    creds_and_host = url.split("://", 1)[1]
    creds, host_and_db = creds_and_host.split("@", 1)
    user, password = creds.split(":", 1)
    host_port, dbname = host_and_db.split("/", 1)
    host, port = host_port.split(":", 1)

    os.environ["DB_USER"] = user
    os.environ["DB_PASSWORD"] = password
    os.environ["DB_HOST"] = host
    os.environ["DB_PORT"] = port
    os.environ["DB_NAME"] = dbname
