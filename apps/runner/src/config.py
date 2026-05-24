from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

SSO_REQUIRED_FIELDS = (
    "oidc_client_id",
    "oidc_client_secret",
    "oidc_issuer_url",
    "oidc_authorize_url",
    "oidc_token_url",
    "oidc_userinfo_url",
    "oidc_jwks_url",
    "oidc_scopes",
    "oidc_callback_url",
    "session_secret_key",
)


class Settings(BaseSettings):
    """Homelab config comes from RUNNER_* env (see values.yaml and runner-oauth-secret).

    BaseSettings reads the environment on init; field defaults below apply only when
    a variable is unset (local dev/tests).
    """

    model_config = SettingsConfigDict(env_prefix="RUNNER_")

    app_name: str = "Runner"
    environment: str = "local"
    # Ingress path prefix for browser-facing URLs only (not FastAPI root_path).
    url_prefix: str = ""
    namespace: str = "apps"
    cluster_name: str = ""
    grafana_base_url: str = ""
    loki_datasource_uid: str = ""
    sso_enabled: bool = False
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_issuer_url: str = ""
    oidc_authorize_url: str = ""
    oidc_token_url: str = ""
    oidc_userinfo_url: str = ""
    oidc_jwks_url: str = ""
    oidc_scopes: str = ""
    oidc_callback_url: str = ""
    session_secret_key: str = ""
    sso_allowed_group: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
