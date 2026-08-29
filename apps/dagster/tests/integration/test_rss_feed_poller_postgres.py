from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from dagster_project.ops import rss_feed_poller as poller

pytestmark = pytest.mark.integration

RSS_FEED = b"""
<rss version="2.0">
  <channel>
    <item>
      <title>Integration entry</title>
      <link>https://example.com/integration-entry</link>
      <guid>integration-guid</guid>
      <description>Integration description</description>
    </item>
  </channel>
</rss>
"""


@dataclass
class FakeResponse:
    status_code: int
    content: bytes

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300


class FakeClient:
    def __init__(self):
        self.posts: list[dict] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url: str, *, timeout: float):
        return FakeResponse(200, RSS_FEED)

    async def post(self, url: str, *, json: dict, timeout: float):
        self.posts.append(json)
        return FakeResponse(204, b"")


class FakeLog:
    def info(self, message: str):
        pass

    def warning(self, message: str):
        pass


class FakeContext:
    log = FakeLog()


def test_poll_persists_guids_in_postgres(postgres_resource, monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(poller.httpx, "AsyncClient", lambda: client)
    monkeypatch.setattr(poller, "POST_DELAY_SECONDS", 0)
    feed = poller.Feed("Integration", "https://example.com/integration-feed")

    first_result = asyncio.run(
        poller.poll_feeds(
            [feed], "https://discord.test/integration", postgres_resource, FakeContext()
        )
    )
    second_result = asyncio.run(
        poller.poll_feeds(
            [feed], "https://discord.test/integration", postgres_resource, FakeContext()
        )
    )
    stored_count = postgres_resource.fetch_value(
        "SELECT count(*) FROM source.rss_feed_entries"
    )

    assert first_result["entries_posted"] == 1
    assert second_result["entries_posted"] == 0
    assert stored_count == 1
    assert len(client.posts) == 1
