from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RUNNER_")

    app_name: str = "Runner"
    environment: str = "local"
    # Ingress path prefix for browser-facing URLs only (not FastAPI root_path).
    url_prefix: str = ""
    namespace: str = "apps"
    cluster_name: str = "homelab-prod"
    grafana_base_url: str = "http://grafana.home"
    loki_datasource_uid: str = "Loki"
    sso_enabled: bool = False
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_issuer_url: str = (
        "http://authentik-server.authentik.svc.cluster.local/application/o/runner/"
    )
    oidc_authorize_url: str = "http://authentik.home/application/o/authorize/"
    oidc_token_url: str = (
        "http://authentik-server.authentik.svc.cluster.local/application/o/token/"
    )
    oidc_userinfo_url: str = (
        "http://authentik-server.authentik.svc.cluster.local/application/o/userinfo/"
    )
    oidc_jwks_url: str = (
        "http://authentik-server.authentik.svc.cluster.local/application/o/runner/jwks/"
    )
    oidc_scopes: str = "openid email profile"
    oidc_callback_url: str = "http://apps.home/runner/auth/callback"
    session_secret_key: str = "unsafe-local-runner-session-key"


@lru_cache
def get_settings() -> Settings:
    return Settings()
