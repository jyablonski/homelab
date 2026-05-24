from __future__ import annotations

from functools import lru_cache
from urllib.parse import quote

from authlib.integrations.starlette_client import OAuth
from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse, Response

from config import Settings

SESSION_NEXT_URL = "runner_sso_next_url"
SESSION_USER = "runner_user"
PUBLIC_PATHS = {
    "/auth/callback",
    "/auth/login",
    "/auth/logout",
    "/healthz",
    "/metrics",
}


def validate_sso_settings(settings: Settings) -> None:
    if not settings.sso_enabled:
        return

    missing = [
        name
        for name in ("oidc_client_id", "oidc_client_secret", "session_secret_key")
        if not getattr(settings, name)
    ]
    if missing:
        joined = ", ".join(f"RUNNER_{name.upper()}" for name in missing)
        raise RuntimeError(
            f"Runner SSO is enabled but missing required settings: {joined}"
        )


@lru_cache
def oauth_for_settings(
    client_id: str,
    client_secret: str,
    issuer_url: str,
    authorize_url: str,
    token_url: str,
    userinfo_url: str,
    jwks_url: str,
    scopes: str,
) -> OAuth:
    oauth = OAuth()
    oauth.register(
        "authentik",
        client_id=client_id,
        client_secret=client_secret,
        authorize_url=authorize_url,
        access_token_url=token_url,
        client_kwargs={"scope": scopes},
        issuer=issuer_url.rstrip("/") + "/",
        userinfo_endpoint=userinfo_url,
        jwks_uri=jwks_url,
    )
    return oauth


def oauth_client(settings: Settings):
    return oauth_for_settings(
        settings.oidc_client_id,
        settings.oidc_client_secret,
        settings.oidc_issuer_url,
        settings.oidc_authorize_url,
        settings.oidc_token_url,
        settings.oidc_userinfo_url,
        settings.oidc_jwks_url,
        settings.oidc_scopes,
    ).authentik


def is_public_path(path: str) -> bool:
    return path in PUBLIC_PATHS or path.startswith("/static/")


def prefixed_path(settings: Settings, path: str) -> str:
    prefix = settings.url_prefix.rstrip("/")
    if not prefix:
        return path
    if path == "/":
        return f"{prefix}/"
    return f"{prefix}{path}"


def safe_next_url(settings: Settings, value: str | None) -> str:
    if value and value.startswith(prefixed_path(settings, "/")):
        return value
    if (
        value
        and not value.startswith(("http://", "https://"))
        and value.startswith("/")
    ):
        return prefixed_path(settings, value)
    return prefixed_path(settings, "/")


def auth_required_response(request: Request, settings: Settings) -> Response:
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Authentication required"}, status_code=401)

    next_url = prefixed_path(settings, request.url.path)
    if request.url.query:
        next_url = f"{next_url}?{request.url.query}"
    login_url = f"{prefixed_path(settings, '/auth/login')}?next={quote(next_url)}"
    return RedirectResponse(login_url, status_code=303)


def userinfo_from_token(token: dict) -> dict[str, str]:
    userinfo = token.get("userinfo") or {}
    return {
        "sub": str(userinfo.get("sub") or ""),
        "username": str(
            userinfo.get("preferred_username")
            or userinfo.get("nickname")
            or userinfo.get("email")
            or userinfo.get("sub")
            or ""
        ),
        "email": str(userinfo.get("email") or ""),
        "name": str(userinfo.get("name") or userinfo.get("preferred_username") or ""),
    }
