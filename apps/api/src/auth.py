from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from config import Settings, get_settings

API_KEY_HEADER = "X-Homelab-Api-Key"


def require_api_key(
    settings: Annotated[Settings, Depends(get_settings)],
    api_key: Annotated[str | None, Header(alias=API_KEY_HEADER)] = None,
) -> None:
    if not settings.api_key:
        return
    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing API key",
        )
