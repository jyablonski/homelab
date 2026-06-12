from __future__ import annotations

import re
from functools import lru_cache
from authlib.integrations.base_client import OAuthError
from authlib.integrations.django_client import OAuth
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model, login as django_login
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.sessions.backends.base import SessionBase
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

SESSION_NEXT_URL = "django_sso_next_url"


class HttpRequestWithSession(HttpRequest):
    """HttpRequest after SessionMiddleware attaches ``session``."""

    session: SessionBase


def sso_enabled() -> bool:
    return bool(getattr(settings, "DJANGO_SSO_ENABLED", False))


def _require_sso_config() -> None:
    missing = [
        name
        for name in ("DJANGO_OIDC_CLIENT_ID", "DJANGO_OIDC_CLIENT_SECRET")
        if not getattr(settings, name, "")
    ]
    if missing:
        raise ImproperlyConfigured(
            "Django SSO is enabled but missing required settings: " + ", ".join(missing)
        )


@lru_cache
def _oauth() -> OAuth:
    _require_sso_config()
    oauth = OAuth()
    oauth.register(
        "authentik",
        client_id=settings.DJANGO_OIDC_CLIENT_ID,
        client_secret=settings.DJANGO_OIDC_CLIENT_SECRET,
        authorize_url=settings.DJANGO_OIDC_AUTHORIZE_URL,
        access_token_url=settings.DJANGO_OIDC_TOKEN_URL,
        client_kwargs={"scope": settings.DJANGO_OIDC_SCOPES},
        issuer=settings.DJANGO_OIDC_ISSUER_URL.rstrip("/") + "/",
        userinfo_endpoint=settings.DJANGO_OIDC_USERINFO_URL,
        jwks_uri=settings.DJANGO_OIDC_JWKS_URL,
    )
    return oauth


def _safe_next_url(request: HttpRequest) -> str:
    next_url = request.GET.get("next") or settings.LOGIN_REDIRECT_URL
    if url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return settings.LOGIN_REDIRECT_URL


def admin_login(
    request: HttpRequestWithSession, extra_context: dict | None = None
) -> HttpResponse:
    if not sso_enabled() or request.GET.get("local") == "1":
        return admin.site.login(request, extra_context=extra_context)
    return sso_login(request)


def sso_login(request: HttpRequestWithSession) -> HttpResponse:
    if not sso_enabled():
        return redirect("/admin/login/")

    request.session[SESSION_NEXT_URL] = _safe_next_url(request)
    callback_url = settings.DJANGO_OIDC_CALLBACK_URL or request.build_absolute_uri(
        reverse("django_sso_callback")
    )
    return _oauth().authentik.authorize_redirect(request, callback_url)


def sso_callback(request: HttpRequestWithSession) -> HttpResponse:
    if not sso_enabled():
        return redirect("/admin/login/")

    client = _oauth().authentik
    try:
        token = client.authorize_access_token(request)
        userinfo = token.get("userinfo") or client.parse_id_token(request, token)
    except OAuthError:
        return redirect("/admin/login/")

    if not _sso_allowed(userinfo):
        return redirect("/admin/login/")

    user = _user_from_claims(userinfo)
    django_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    next_url = request.session.pop(SESSION_NEXT_URL, settings.LOGIN_REDIRECT_URL)
    return redirect(next_url)


def _user_from_claims(userinfo: dict) -> AbstractBaseUser:
    subject = str(userinfo.get("sub") or "").strip()
    if not subject:
        raise ImproperlyConfigured("OIDC userinfo response did not include a subject")

    email = str(userinfo.get("email") or "").strip()
    username = _username_from_claims(userinfo, subject)
    defaults = {
        "email": email,
        "first_name": str(userinfo.get("given_name") or "")[:150],
        "last_name": str(userinfo.get("family_name") or "")[:150],
    }

    user_model = get_user_model()
    user, created = user_model.objects.get_or_create(
        username=username, defaults=defaults
    )
    changed = False

    if created:
        user.set_unusable_password()
        changed = True
    for field, value in defaults.items():
        if value and getattr(user, field) != value:
            setattr(user, field, value)
            changed = True

    groups = _groups_from_claims(userinfo)
    staff_group = getattr(settings, "DJANGO_SSO_STAFF_GROUP", "")
    superuser_group = getattr(settings, "DJANGO_SSO_SUPERUSER_GROUP", "")
    if staff_group and user.is_staff != (staff_group in groups):
        user.is_staff = staff_group in groups
        changed = True
    if superuser_group and user.is_superuser != (superuser_group in groups):
        user.is_superuser = superuser_group in groups
        changed = True

    if changed:
        user.save()
    return user


def _groups_from_claims(userinfo: dict) -> set[str]:
    groups = userinfo.get("groups") or []
    if isinstance(groups, str):
        groups = [groups]
    return {str(group) for group in groups}


def _sso_allowed(userinfo: dict) -> bool:
    """Require membership in DJANGO_SSO_STAFF_GROUP when SSO is enabled."""
    required = getattr(settings, "DJANGO_SSO_STAFF_GROUP", "")
    if not required:
        return True
    return required in _groups_from_claims(userinfo)


def _username_from_claims(userinfo: dict, subject: str) -> str:
    raw = (
        userinfo.get("preferred_username")
        or userinfo.get("nickname")
        or userinfo.get("email")
        or subject
    )
    username = re.sub(r"[^A-Za-z0-9_.@+-]", "_", str(raw)).strip("._")
    return (username or subject.replace("|", "_"))[:150]
