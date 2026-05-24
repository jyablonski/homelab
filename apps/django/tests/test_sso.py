from types import SimpleNamespace
from typing import cast

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponseRedirect
from django.test import override_settings

from core import sso


class FakeAuthentikClient:
    def __init__(self, userinfo=None):
        self.callback_url = None
        self.userinfo = userinfo or {
            "sub": "authentik-user-1",
            "preferred_username": "jacob",
            "email": "jacob@example.test",
            "given_name": "Jacob",
            "family_name": "Homelab",
            "groups": ["homelab-admins"],
        }

    def authorize_redirect(self, _request, callback_url):
        self.callback_url = callback_url
        return HttpResponseRedirect("http://authentik.home/application/o/authorize/")

    def authorize_access_token(self, _request):
        return {"userinfo": self.userinfo}


def test_sso_disabled_redirects_to_local_admin_login(client):
    response = client.get("/django/sso/login/")

    assert response.status_code == 302
    assert response["Location"] == "/django/admin/login/"


@override_settings(
    DJANGO_SSO_ENABLED=True,
    DJANGO_OIDC_CLIENT_ID="django",
    DJANGO_OIDC_CLIENT_SECRET="secret",
    DJANGO_OIDC_CALLBACK_URL="http://apps.home/django/sso/callback/",
    SESSION_ENGINE="django.contrib.sessions.backends.signed_cookies",
)
def test_admin_login_redirects_to_authentik_when_sso_enabled(client, monkeypatch):
    fake_client = FakeAuthentikClient()
    monkeypatch.setattr(sso, "_oauth", lambda: SimpleNamespace(authentik=fake_client))

    response = client.get("/django/admin/login/?next=/django/admin/")

    assert response.status_code == 302
    assert response["Location"] == "http://authentik.home/application/o/authorize/"
    assert fake_client.callback_url == "http://apps.home/django/sso/callback/"


@override_settings(
    DJANGO_SSO_ENABLED=True,
    DJANGO_OIDC_CLIENT_ID="",
    DJANGO_OIDC_CLIENT_SECRET="",
)
def test_sso_enabled_requires_client_credentials(client):
    sso._oauth.cache_clear()

    with pytest.raises(ImproperlyConfigured):
        client.get("/django/sso/login/")


@override_settings(
    DJANGO_SSO_ENABLED=True,
    DJANGO_SSO_STAFF_GROUP="homelab-admins",
    DJANGO_OIDC_CLIENT_ID="django",
    DJANGO_OIDC_CLIENT_SECRET="secret",
    SESSION_ENGINE="django.contrib.sessions.backends.signed_cookies",
)
def test_sso_callback_creates_django_user_and_logs_in(client, monkeypatch):
    fake_client = FakeAuthentikClient()
    monkeypatch.setattr(sso, "_oauth", lambda: SimpleNamespace(authentik=fake_client))
    monkeypatch.setattr(
        sso,
        "_user_from_claims",
        lambda userinfo: SimpleNamespace(
            pk="1",
            is_active=True,
            get_session_auth_hash=lambda: "",
            get_backend=lambda: "django.contrib.auth.backends.ModelBackend",
        ),
    )
    monkeypatch.setattr(
        sso,
        "django_login",
        lambda request, _user, backend: request.session.__setitem__(
            "_auth_user_id",
            "1",
        ),
    )
    session = client.session
    session[sso.SESSION_NEXT_URL] = "/django/admin/"
    session.save()

    response = client.get("/django/sso/callback/")

    assert response.status_code == 302
    assert response["Location"] == "/django/admin/"
    assert "_auth_user_id" in client.session


@override_settings(
    DJANGO_SSO_ENABLED=True,
    DJANGO_SSO_STAFF_GROUP="homelab-admins",
    DJANGO_OIDC_CLIENT_ID="django",
    DJANGO_OIDC_CLIENT_SECRET="secret",
    SESSION_ENGINE="django.contrib.sessions.backends.signed_cookies",
)
def test_sso_callback_denies_users_without_admin_group(client, monkeypatch):
    fake_client = FakeAuthentikClient(
        userinfo={
            "sub": "authentik-user-2",
            "preferred_username": "guest",
            "groups": ["other-group"],
        }
    )
    monkeypatch.setattr(sso, "_oauth", lambda: SimpleNamespace(authentik=fake_client))
    monkeypatch.setattr(
        sso,
        "django_login",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("django_login should not run")
        ),
    )

    response = client.get("/django/sso/callback/")

    assert response.status_code == 302
    assert response["Location"] == "/django/admin/login/"
    assert "_auth_user_id" not in client.session


def test_sso_allowed_requires_staff_group():
    with override_settings(DJANGO_SSO_STAFF_GROUP="homelab-admins"):
        assert sso._sso_allowed({"groups": ["homelab-admins"]}) is True
        assert sso._sso_allowed({"groups": ["other"]}) is False
        assert sso._sso_allowed({}) is False


def test_sso_user_from_claims_creates_unusable_password_user(monkeypatch):
    class FakeUser:
        email = ""
        first_name = ""
        last_name = ""
        is_staff = False
        is_superuser = False

        def __init__(self, username):
            self.username = username
            self.saved = False
            self.password_unusable = False

        def set_unusable_password(self):
            self.password_unusable = True

        def save(self):
            self.saved = True

    class FakeManager:
        def get_or_create(self, username, defaults):
            user = FakeUser(username)
            user.email = defaults["email"]
            user.first_name = defaults["first_name"]
            user.last_name = defaults["last_name"]
            return user, True

    class FakeUserModel:
        objects = FakeManager()

    monkeypatch.setattr(sso, "get_user_model", lambda: FakeUserModel)

    user = cast(
        FakeUser,
        sso._user_from_claims(
            {
                "sub": "authentik-user-1",
                "preferred_username": "jacob!",
                "email": "jacob@example.test",
                "given_name": "Jacob",
                "family_name": "Homelab",
                "groups": ["homelab-admins"],
            }
        ),
    )

    assert user.username == "jacob"
    assert user.email == "jacob@example.test"
    assert user.password_unusable is True
    assert user.is_staff is False
    assert user.is_superuser is False
    assert user.saved is True


@override_settings(
    DJANGO_SSO_STAFF_GROUP="homelab-admins",
    DJANGO_SSO_SUPERUSER_GROUP="homelab-admins",
)
def test_sso_user_from_claims_maps_admin_group_to_privileges(monkeypatch):
    class FakeUser:
        email = ""
        first_name = ""
        last_name = ""
        is_staff = False
        is_superuser = False

        def __init__(self, username):
            self.username = username
            self.saved = False
            self.password_unusable = False

        def set_unusable_password(self):
            self.password_unusable = True

        def save(self):
            self.saved = True

    class FakeManager:
        def get_or_create(self, username, defaults):
            return FakeUser(username), True

    class FakeUserModel:
        objects = FakeManager()

    monkeypatch.setattr(sso, "get_user_model", lambda: FakeUserModel)

    user = cast(
        FakeUser,
        sso._user_from_claims(
            {
                "sub": "authentik-user-1",
                "preferred_username": "akadmin",
                "groups": ["homelab-admins"],
            }
        ),
    )

    assert user.is_staff is True
    assert user.is_superuser is True
    assert user.saved is True


@override_settings(
    DJANGO_SSO_STAFF_GROUP="homelab-admins",
    DJANGO_SSO_SUPERUSER_GROUP="homelab-admins",
)
def test_sso_user_from_claims_removes_privileges_when_group_missing(monkeypatch):
    class FakeUser:
        email = ""
        first_name = ""
        last_name = ""
        is_staff = True
        is_superuser = True

        def __init__(self, username):
            self.username = username
            self.saved = False

        def save(self):
            self.saved = True

    class FakeManager:
        def get_or_create(self, username, defaults):
            return FakeUser(username), False

    class FakeUserModel:
        objects = FakeManager()

    monkeypatch.setattr(sso, "get_user_model", lambda: FakeUserModel)

    user = cast(
        FakeUser,
        sso._user_from_claims(
            {
                "sub": "authentik-user-1",
                "preferred_username": "akadmin",
                "groups": [],
            }
        ),
    )

    assert user.is_staff is False
    assert user.is_superuser is False
    assert user.saved is True
