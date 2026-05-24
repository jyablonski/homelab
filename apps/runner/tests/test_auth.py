from fastapi.testclient import TestClient
from starlette.responses import RedirectResponse

from config import Settings
from main import create_app, get_runner_client


class FakeOAuthClient:
    async def authorize_redirect(self, _request, redirect_uri):
        self.redirect_uri = redirect_uri
        return RedirectResponse("http://authentik.home/application/o/authorize/")

    async def authorize_access_token(self, _request):
        return {
            "userinfo": {
                "sub": "authentik-user-1",
                "preferred_username": "jacob",
                "email": "jacob@example.test",
                "name": "Jacob",
            }
        }


def sso_settings() -> Settings:
    return Settings(
        url_prefix="/runner",
        sso_enabled=True,
        oidc_client_id="runner",
        oidc_client_secret="secret",
        oidc_callback_url="http://apps.home/runner/auth/callback",
        session_secret_key="test-session-secret",
    )


def test_sso_enabled_protects_ui_and_api(fake_runner_client):
    app = create_app(sso_settings())
    app.dependency_overrides[get_runner_client] = lambda: fake_runner_client
    client = TestClient(app)

    ui_response = client.get("/", follow_redirects=False)
    api_response = client.get("/api/jobs")
    health_response = client.get("/healthz")
    metrics_response = client.get("/metrics")

    assert ui_response.status_code == 303
    assert ui_response.headers["location"] == "/runner/auth/login?next=/runner/"
    assert api_response.status_code == 401
    assert api_response.json() == {"detail": "Authentication required"}
    assert health_response.status_code == 200
    assert metrics_response.status_code == 200


def test_sso_login_and_callback_create_session(
    fake_runner_client,
    monkeypatch,
):
    import main

    fake_oauth_client = FakeOAuthClient()
    monkeypatch.setattr(main, "oauth_client", lambda _settings: fake_oauth_client)
    app = create_app(sso_settings())
    app.dependency_overrides[get_runner_client] = lambda: fake_runner_client
    client = TestClient(app)

    login_response = client.get("/auth/login?next=/runner/", follow_redirects=False)
    callback_response = client.get("/auth/callback", follow_redirects=False)
    home_response = client.get("/")

    assert login_response.status_code == 307
    assert login_response.headers["location"] == (
        "http://authentik.home/application/o/authorize/"
    )
    assert fake_oauth_client.redirect_uri == "http://apps.home/runner/auth/callback"
    assert callback_response.status_code == 303
    assert callback_response.headers["location"] == "/runner/"
    assert home_response.status_code == 200
    assert "jacob" in home_response.text


def test_sso_enabled_requires_client_settings():
    try:
        create_app(Settings(sso_enabled=True))
    except RuntimeError as exc:
        assert "RUNNER_OIDC_CLIENT_ID" in str(exc)
        assert "RUNNER_OIDC_CLIENT_SECRET" in str(exc)
    else:
        raise AssertionError("Expected missing SSO settings to raise RuntimeError")
