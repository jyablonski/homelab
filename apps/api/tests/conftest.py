import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from testcontainers.postgres import PostgresContainer

from config import Settings, get_settings
from database import Base, get_engine
from main import create_app


@pytest.fixture()
def test_client():
    return TestClient(create_app(Settings()))


@pytest.fixture(scope="session")
def postgres_dsn():
    if not os.path.exists("/var/run/docker.sock"):
        pytest.skip("Docker socket not available for testcontainers integration test")

    with PostgresContainer("postgres:17") as postgres:
        yield postgres.get_connection_url().replace(
            "postgresql+psycopg2://",
            "postgresql://",
        )


@pytest.fixture(scope="session")
def postgres_settings(postgres_dsn):
    return Settings(database_url=postgres_dsn, db_search_path="source,public")


@pytest.fixture()
def api_database_env(postgres_settings):
    restore_env = _set_env(
        {
            "DATABASE_URL": postgres_settings.database_url,
            "DB_SEARCH_PATH": postgres_settings.db_search_path,
            "DB_CONNECT_TIMEOUT": "2",
        }
    )
    get_settings.cache_clear()
    get_engine.cache_clear()
    yield
    restore_env()
    get_settings.cache_clear()
    get_engine.cache_clear()


@pytest.fixture()
def db_test_client(api_database_env):
    return TestClient(create_app(Settings()))


@pytest.fixture()
def unavailable_database_env():
    restore_env = _set_env(
        {
            "DATABASE_URL": "postgresql://postgres:postgres@127.0.0.1:1/postgres",
            "DB_SEARCH_PATH": "source,public",
            "DB_CONNECT_TIMEOUT": "1",
        }
    )
    get_settings.cache_clear()
    get_engine.cache_clear()
    yield
    restore_env()
    get_settings.cache_clear()
    get_engine.cache_clear()


@pytest.fixture()
def unavailable_database_client(unavailable_database_env):
    return TestClient(create_app(Settings()))


@pytest.fixture()
def reminders_table(postgres_settings):
    engine = get_engine(postgres_settings)
    with engine.begin() as connection:
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS source"))
        Base.metadata.drop_all(bind=connection)
        Base.metadata.create_all(bind=connection)


def _set_env(values: dict[str, str]):
    original_values = {key: os.environ.get(key) for key in values}
    os.environ.update(values)

    def restore_env() -> None:
        for key, original_value in original_values.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value

    return restore_env
