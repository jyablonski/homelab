from functools import lru_cache
import re
from urllib.parse import urlsplit

from pydantic import AnyHttpUrl, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

TARGET_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]{0,62}$")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MCP_")

    app_name: str = "Homelab MCP"
    environment: str = "local"
    log_level: str = "INFO"
    allowed_hosts: list[str] = Field(
        default_factory=lambda: [
            "127.0.0.1:*",
            "localhost:*",
            "[::1]:*",
        ]
    )
    allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:*",
            "http://localhost:*",
            "http://[::1]:*",
        ]
    )
    api_base_url: AnyHttpUrl = AnyHttpUrl("http://api.apps.svc.cluster.local:8000")
    api_key: SecretStr = SecretStr("")
    require_api_key: bool = False
    external_url: AnyHttpUrl = AnyHttpUrl("http://localhost:8000/mcp")
    inbound_bearer_token: SecretStr = SecretStr("")
    require_inbound_auth: bool = False
    request_timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    health_targets: dict[str, AnyHttpUrl] = Field(
        default_factory=lambda: {
            "api": AnyHttpUrl("http://api.apps.svc.cluster.local:8000/healthz"),
        }
    )

    @model_validator(mode="after")
    def validate_runtime_settings(self) -> "Settings":
        if self.require_api_key and not self.api_key.get_secret_value():
            raise ValueError("MCP_API_KEY is required when MCP_REQUIRE_API_KEY is true")
        inbound_bearer_token = self.inbound_bearer_token.get_secret_value()
        if self.require_inbound_auth and not inbound_bearer_token:
            raise ValueError(
                "MCP_INBOUND_BEARER_TOKEN is required when "
                "MCP_REQUIRE_INBOUND_AUTH is true"
            )
        if inbound_bearer_token and len(inbound_bearer_token) < 32:
            raise ValueError("MCP_INBOUND_BEARER_TOKEN must be at least 32 characters")
        _validate_url(self.api_base_url, field_name="MCP_API_BASE_URL")
        _validate_url(self.external_url, field_name="MCP_EXTERNAL_URL")
        if not self.health_targets:
            raise ValueError("MCP_HEALTH_TARGETS must include at least one target")
        if len(self.health_targets) > 20:
            raise ValueError("MCP_HEALTH_TARGETS cannot contain more than 20 targets")
        for name, url in self.health_targets.items():
            if not TARGET_NAME_PATTERN.fullmatch(name):
                raise ValueError(f"invalid MCP_HEALTH_TARGETS name: {name}")
            _validate_url(url, field_name=f"MCP_HEALTH_TARGETS[{name}]")
        return self


def _validate_url(url: AnyHttpUrl, *, field_name: str) -> None:
    parsed = urlsplit(str(url))
    if parsed.username or parsed.password:
        raise ValueError(f"{field_name} cannot contain credentials")
    if parsed.query or parsed.fragment:
        raise ValueError(f"{field_name} cannot contain a query string or fragment")


@lru_cache
def get_settings() -> Settings:
    return Settings()
