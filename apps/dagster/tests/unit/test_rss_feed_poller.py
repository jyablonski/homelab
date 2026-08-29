from __future__ import annotations

import asyncio
from contextlib import contextmanager
from dataclasses import dataclass

import httpx
import pytest

from dagster_project.defs.jobs.rss_feed_poller import rss_feed_poller_job
from dagster_project.ops import rss_feed_poller as poller

pytestmark = pytest.mark.unit

RSS_FEED = b"""
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Example feed</title>
    <item>
      <title>RSS entry</title>
      <link>https://example.com/rss-entry</link>
      <guid>rss-guid</guid>
      <description>RSS description</description>
    </item>
  </channel>
</rss>
"""
ATOM_FEED = b"""
<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Example Atom feed</title>
  <entry>
    <title>Atom entry</title>
    <id>atom-id</id>
    <link href="https://example.com/atom-entry" />
    <summary>Atom summary</summary>
  </entry>
</feed>
"""


@dataclass
class FakeResponse:
    status_code: int
    content: bytes = b""

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300


class FakeClient:
    def __init__(
        self, responses: dict[str, object], post_statuses: list[int] | None = None
    ):
        self.responses = responses
        self.post_statuses = post_statuses or [204]
        self.posts: list[tuple[str, dict]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url: str, *, timeout: float):
        assert timeout == poller.REQUEST_TIMEOUT_SECONDS
        response = self.responses[url]
        if isinstance(response, Exception):
            raise response
        return response

    async def post(self, url: str, *, json: dict, timeout: float):
        assert timeout == poller.REQUEST_TIMEOUT_SECONDS
        self.posts.append((url, json))
        return FakeResponse(self.post_statuses.pop(0) if self.post_statuses else 204)


class FakeCursor:
    def __init__(self, connection: FakeConnection):
        self.connection = connection
        self.result: tuple[str] | None = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query: str, params: tuple[str, str]):
        key = params
        if key not in self.connection.database.state:
            self.connection.pending = key
            self.result = (params[1],)
        else:
            self.result = None

    def fetchone(self):
        return self.result


class FakeConnection:
    def __init__(self, database: FakePostgres):
        self.database = database
        self.pending: tuple[str, str] | None = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        if self.pending is not None:
            self.database.state.add(self.pending)
            self.pending = None

    def rollback(self):
        self.pending = None


class FakePostgres:
    def __init__(self):
        self.state: set[tuple[str, str]] = set()
        self.executed: list[str] = []

    def execute(self, query: str, params=None):
        self.executed.append(query)

    def fetch_all(self, query: str, params: tuple[str]):
        feed_url = params[0]
        return [
            (entry_guid,)
            for stored_feed_url, entry_guid in self.state
            if stored_feed_url == feed_url
        ]

    @contextmanager
    def connection(self):
        yield FakeConnection(self)


class FakeLog:
    def __init__(self):
        self.info_messages: list[str] = []
        self.warning_messages: list[str] = []

    def info(self, message: str):
        self.info_messages.append(message)

    def warning(self, message: str):
        self.warning_messages.append(message)


class FakeContext:
    def __init__(self):
        self.log = FakeLog()


def _run(feeds, database, context, webhook_url="https://discord.test/global"):
    return asyncio.run(poller.poll_feeds(feeds, webhook_url, database, context))


def test_parse_entries_supports_rss_and_atom():
    rss_entries = poller._parse_entries(RSS_FEED)
    atom_entries = poller._parse_entries(ATOM_FEED)

    assert rss_entries == [
        poller.FeedEntry(
            guid="rss-guid",
            title="RSS entry",
            link="https://example.com/rss-entry",
            description="RSS description",
        )
    ]
    assert atom_entries == [
        poller.FeedEntry(
            guid="atom-id",
            title="Atom entry",
            link="https://example.com/atom-entry",
            description="Atom summary",
        )
    ]


def test_parse_entries_strips_html_from_description():
    content = RSS_FEED.replace(
        b"RSS description", b"<![CDATA[<p>RSS</p><p>description</p>]]>"
    )

    assert poller._parse_entries(content)[0].description == "RSS description"


def test_embed_payload_truncates_description():
    entry = poller.FeedEntry("guid", "Title", "https://example.com", "x" * 301)

    assert poller._embed_payload(entry) == {
        "embeds": [
            {
                "title": "Title",
                "url": "https://example.com",
                "description": "x" * 300,
                "color": 7_506_394,
            }
        ]
    }


def test_poll_deduplicates_entries_across_runs(monkeypatch):
    client = FakeClient({"https://example.com/feed": FakeResponse(200, RSS_FEED)})
    monkeypatch.setattr(poller.httpx, "AsyncClient", lambda: client)
    monkeypatch.setattr(poller, "POST_DELAY_SECONDS", 0)
    database = FakePostgres()
    context = FakeContext()
    feed = poller.Feed("Example", "https://example.com/feed")

    first_result = _run([feed], database, context)
    second_result = _run([feed], database, context)

    assert first_result == {"feeds_processed": 1, "entries_posted": 1}
    assert second_result == {"feeds_processed": 1, "entries_posted": 0}
    assert len(client.posts) == 1
    assert len(database.state) == 1


def test_job_executes_configured_op(monkeypatch):
    client = FakeClient({"https://example.com/feed": FakeResponse(200, RSS_FEED)})
    monkeypatch.setattr(poller.httpx, "AsyncClient", lambda: client)
    monkeypatch.setattr(poller, "POST_DELAY_SECONDS", 0)
    database = FakePostgres()

    result = rss_feed_poller_job.execute_in_process(
        run_config={
            "ops": {
                "rss_feed_poller": {
                    "config": {
                        "discord_webhook_url": "https://discord.test/global",
                        "feeds": [
                            {
                                "name": "Example",
                                "url": "https://example.com/feed",
                            }
                        ],
                    }
                }
            }
        },
        resources={"postgres": database},
    )

    assert result.success
    assert result.output_for_node("rss_feed_poller") == {
        "feeds_processed": 1,
        "entries_posted": 1,
    }


def test_failed_discord_post_is_not_recorded(monkeypatch):
    client = FakeClient(
        {"https://example.com/feed": FakeResponse(200, RSS_FEED)},
        post_statuses=[500, 204],
    )
    monkeypatch.setattr(poller.httpx, "AsyncClient", lambda: client)
    monkeypatch.setattr(poller, "POST_DELAY_SECONDS", 0)
    database = FakePostgres()
    context = FakeContext()
    feed = poller.Feed("Example", "https://example.com/feed")

    first_result = _run([feed], database, context)
    second_result = _run([feed], database, context)

    assert first_result["entries_posted"] == 0
    assert second_result["entries_posted"] == 1
    assert len(database.state) == 1


def test_feed_failures_are_logged_and_do_not_stop_other_feeds(monkeypatch):
    good_url = "https://example.com/good"
    responses = {
        "https://example.com/status": FakeResponse(503),
        "https://example.com/timeout": httpx.ReadTimeout("timed out"),
        "https://example.com/malformed": FakeResponse(200, b"<rss><channel>"),
        good_url: FakeResponse(200, RSS_FEED),
    }
    client = FakeClient(responses)
    monkeypatch.setattr(poller.httpx, "AsyncClient", lambda: client)
    monkeypatch.setattr(poller, "POST_DELAY_SECONDS", 0)
    database = FakePostgres()
    context = FakeContext()
    feeds = [
        poller.Feed("Status", "https://example.com/status"),
        poller.Feed("Timeout", "https://example.com/timeout"),
        poller.Feed("Malformed", "https://example.com/malformed"),
        poller.Feed("Good", good_url),
    ]

    result = _run(feeds, database, context)

    assert result == {"feeds_processed": 4, "entries_posted": 1}
    assert len(client.posts) == 1
    assert any("HTTP 503" in message for message in context.log.warning_messages)
    assert any("timed out" in message for message in context.log.warning_messages)
    assert any(
        "malformed feed XML" in message for message in context.log.warning_messages
    )


def test_global_webhook_routes_all_feeds(monkeypatch):
    second_feed = RSS_FEED.replace(b"rss-guid", b"second-guid")
    client = FakeClient(
        {
            "https://example.com/one": FakeResponse(200, RSS_FEED),
            "https://example.com/two": FakeResponse(200, second_feed),
        }
    )
    monkeypatch.setattr(poller.httpx, "AsyncClient", lambda: client)
    monkeypatch.setattr(poller, "POST_DELAY_SECONDS", 0)
    database = FakePostgres()
    context = FakeContext()
    feeds = [
        poller.Feed("Feed one", "https://example.com/one"),
        poller.Feed("Feed two", "https://example.com/two"),
    ]

    result = _run(feeds, database, context)

    assert result["entries_posted"] == 2
    assert [url for url, _ in client.posts] == [
        "https://discord.test/global",
        "https://discord.test/global",
    ]


def test_delay_is_applied_between_multiple_posts(monkeypatch):
    two_entry_feed = RSS_FEED.replace(
        b"</channel>",
        b"""
        <item>
          <title>Second RSS entry</title>
          <link>https://example.com/rss-entry-2</link>
          <guid>rss-guid-2</guid>
          <description>Second description</description>
        </item>
        </channel>
        """,
    )
    client = FakeClient({"https://example.com/feed": FakeResponse(200, two_entry_feed)})
    sleep_calls: list[float] = []

    async def fake_sleep(seconds: float):
        sleep_calls.append(seconds)

    monkeypatch.setattr(poller.httpx, "AsyncClient", lambda: client)
    monkeypatch.setattr(poller.asyncio, "sleep", fake_sleep)
    database = FakePostgres()
    context = FakeContext()
    feed = poller.Feed("Example", "https://example.com/feed")

    result = _run([feed], database, context)

    assert result["entries_posted"] == 2
    assert sleep_calls == [poller.POST_DELAY_SECONDS]
