import pytest
from pydantic import AnyHttpUrl, SecretStr, ValidationError

from config import Settings


def test_settings_require_api_key_when_enabled() -> None:
    with pytest.raises(ValidationError, match="MCP_API_KEY is required"):
        Settings(require_api_key=True)


def test_settings_accept_required_api_key() -> None:
    settings = Settings(
        require_api_key=True,
        api_key=SecretStr("configured"),
    )

    assert settings.api_key.get_secret_value() == "configured"


def test_settings_require_inbound_bearer_token_when_enabled() -> None:
    with pytest.raises(
        ValidationError,
        match="MCP_INBOUND_BEARER_TOKEN is required",
    ):
        Settings(require_inbound_auth=True)


def test_settings_accept_required_inbound_bearer_token() -> None:
    settings = Settings(
        require_inbound_auth=True,
        inbound_bearer_token=SecretStr("a" * 32),
    )

    assert settings.inbound_bearer_token.get_secret_value() == "a" * 32


def test_settings_reject_short_inbound_bearer_token() -> None:
    with pytest.raises(
        ValidationError,
        match="MCP_INBOUND_BEARER_TOKEN must be at least 32 characters",
    ):
        Settings(inbound_bearer_token=SecretStr("too-short"))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "api_base_url",
            AnyHttpUrl("http://user:password@api.test"),
            "MCP_API_BASE_URL cannot contain credentials",
        ),
        (
            "api_base_url",
            AnyHttpUrl("http://api.test?query=true"),
            "MCP_API_BASE_URL cannot contain a query string",
        ),
        (
            "health_targets",
            {"Bad Name": AnyHttpUrl("http://api.test/healthz")},
            "invalid MCP_HEALTH_TARGETS name",
        ),
        (
            "health_targets",
            {},
            "MCP_HEALTH_TARGETS must include at least one target",
        ),
    ],
)
def test_settings_reject_unsafe_configuration(
    field: str,
    value: object,
    message: str,
) -> None:
    with pytest.raises(ValidationError, match=message):
        Settings.model_validate({field: value})


def test_settings_limit_health_target_count() -> None:
    targets = {
        f"service-{index}": AnyHttpUrl(f"http://service-{index}.test/healthz")
        for index in range(21)
    }

    with pytest.raises(ValidationError, match="more than 20 targets"):
        Settings(health_targets=targets)
