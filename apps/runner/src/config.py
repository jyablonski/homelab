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


@lru_cache
def get_settings() -> Settings:
    return Settings()
