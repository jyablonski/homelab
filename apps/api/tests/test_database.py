from database import ping_database


def test_ping_database_against_container(postgres_settings):
    assert ping_database(postgres_settings) is True
