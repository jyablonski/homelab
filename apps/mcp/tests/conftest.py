from datetime import UTC, datetime, timedelta

import pytest
from pydantic import AnyHttpUrl, SecretStr

from config import Settings


@pytest.fixture()
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture()
def settings() -> Settings:
    return Settings(
        environment="test",
        api_base_url=AnyHttpUrl("http://api.test"),
        api_key=SecretStr("test-api-key"),
        health_targets={
            "api": AnyHttpUrl("http://api.test/healthz"),
            "runner": AnyHttpUrl("http://runner.test/healthz"),
        },
    )


@pytest.fixture()
def agenda_payload() -> dict[str, object]:
    now = datetime(2026, 7, 25, 8, 0, tzinfo=UTC)
    return {
        "generated_at": now.isoformat(),
        "timezone": "America/Los_Angeles",
        "window": {
            "start": now.isoformat(),
            "end": (now + timedelta(hours=24)).isoformat(),
            "due_soon_days": 7,
        },
        "events": [
            {
                "id": "nba:1",
                "source": "nba",
                "category": "sports",
                "league": "NBA",
                "title": "Warriors game",
                "start_at": (now + timedelta(hours=3)).isoformat(),
                "status": "scheduled",
                "metadata": {"home_team": "Warriors"},
            }
        ],
        "freshness": [
            {
                "source": "nba",
                "last_success_at": now.isoformat(),
                "status": "fresh",
                "message": None,
            }
        ],
        "reminders": {
            "active": [
                {
                    "id": 1,
                    "type": "maintenance",
                    "message": "Replace filter",
                    "start_date": "2026-07-25",
                    "end_date": None,
                    "is_completed": False,
                }
            ],
            "due_soon": [],
            "completed": [],
        },
    }


@pytest.fixture()
def reminder_payload() -> dict[str, object]:
    now = datetime(2026, 7, 25, 8, 0, tzinfo=UTC).isoformat()
    return {
        "id": 1,
        "reminder_type": "maintenance",
        "reminder_message": "Replace filter",
        "reminder_start_date": "2026-07-25",
        "reminder_end_date": None,
        "is_completed": False,
        "completed_at": None,
        "created_at": now,
        "updated_at": now,
    }
