from django.conf import settings


def test_settings_module_loads():
    assert settings.ROOT_URLCONF == "core.urls"
