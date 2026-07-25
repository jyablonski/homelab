from secrets import compare_digest

from mcp.server.auth.provider import AccessToken

MCP_READ_SCOPE = "mcp:read"


class StaticBearerTokenVerifier:
    def __init__(self, expected_token: str) -> None:
        self._expected_token = expected_token

    async def verify_token(self, token: str) -> AccessToken | None:
        if not compare_digest(token, self._expected_token):
            return None
        return AccessToken(
            token=token,
            client_id="homelab-codex",
            scopes=[MCP_READ_SCOPE],
        )
