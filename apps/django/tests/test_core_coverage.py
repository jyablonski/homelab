import importlib

from core.models import Reminder
from django.test import override_settings


def test_healthz_endpoint(client):
    response = client.get("/django/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_reminder_str():
    reminder = Reminder(reminder_type="maintenance", reminder_message="Replace filter")
    assert str(reminder) == "maintenance: Replace filter"


def test_asgi_and_wsgi_modules_expose_application():
    asgi_module = importlib.import_module("core.asgi")
    wsgi_module = importlib.import_module("core.wsgi")

    assert asgi_module.application is not None
    assert wsgi_module.application is not None


def test_create_superuser_noop_without_env(monkeypatch):
    migration_module = importlib.import_module("core.migrations.0001_create_superuser")
    monkeypatch.delenv("DJANGO_SUPERUSER_USERNAME", raising=False)
    monkeypatch.delenv("DJANGO_SUPERUSER_PASSWORD", raising=False)

    class FakeApps:
        def __init__(self):
            self.called = False

        def get_model(self, _app_label, _model_name):
            self.called = True
            return None

    fake_apps = FakeApps()
    migration_module.create_or_update_superuser(fake_apps, None)

    assert fake_apps.called is False


def test_create_superuser_creates_or_updates_user(monkeypatch):
    migration_module = importlib.import_module("core.migrations.0001_create_superuser")
    monkeypatch.setenv("DJANGO_SUPERUSER_USERNAME", "postgres")
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "postgres")

    class FakeUser:
        def __init__(self):
            self.is_staff = False
            self.is_superuser = False
            self.password = None
            self.saved = False

        def save(self):
            self.saved = True

    class FakeManager:
        def __init__(self, user):
            self.user = user
            self.kwargs = None

        def get_or_create(self, **kwargs):
            self.kwargs = kwargs
            return self.user, False

    fake_user = FakeUser()
    fake_manager = FakeManager(fake_user)
    fake_user_model = type("UserModel", (), {"objects": fake_manager})

    class FakeApps:
        def get_model(self, app_label, model_name):
            assert app_label == "auth"
            assert model_name == "User"
            return fake_user_model

    migration_module.create_or_update_superuser(FakeApps(), None)

    assert fake_manager.kwargs["username"] == "postgres"
    assert fake_manager.kwargs["defaults"] == {"is_staff": True, "is_superuser": True}
    assert fake_user.is_staff is True
    assert fake_user.is_superuser is True
    assert fake_user.password is not None
    assert fake_user.password != "postgres"
    assert fake_user.saved is True


def test_reminders_table_migration_shape():
    migration_module = importlib.import_module("core.migrations.0003_reminders_table")
    migration = migration_module.Migration

    assert migration.dependencies == [("core", "0002_create_source_schema")]
    assert len(migration.operations) == 1
    assert migration.operations[0].name == "Reminder"
    assert migration.operations[0].options["db_table"] == "personal_reminders"


def test_source_schema_migration_shape():
    migration_module = importlib.import_module(
        "core.migrations.0002_create_source_schema"
    )
    migration = migration_module.Migration

    assert migration.dependencies == [("core", "0001_create_superuser")]
    assert len(migration.operations) == 1


def test_default_database_search_path_prefers_source():
    settings_module = importlib.import_module("core.settings")
    assert (
        "search_path=source,public"
        in settings_module.DATABASES["default"]["OPTIONS"]["options"]
    )


@override_settings(SESSION_ENGINE="django.contrib.sessions.backends.signed_cookies")
def test_admin_append_slash_under_django_prefix(client):
    response = client.get("/django/admin", HTTP_HOST="apps.home")
    assert response.status_code == 301
    assert response["Location"] == "/django/admin/"
