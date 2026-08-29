from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import feedparser
import httpx
from bs4 import BeautifulSoup
from dagster import Field, Shape, StringSource, op

from dagster_project.resources import PostgresResource
from dagster_project.sql import rss_feed_poller as sql

REQUEST_TIMEOUT_SECONDS = 10.0
POST_DELAY_SECONDS = 2.0
EMBED_COLOR = 7_506_394

DEFAULT_FEEDS = [
    {
        "name": "DHH",
        "url": "https://world.hey.com/dhh/feed.atom",
    },
    {
        "name": "jyablonski.dev",
        "url": "https://jyablonski.dev/rss.xml",
    },
]

DEFAULT_RUN_CONFIG = {
    "ops": {
        "rss_feed_poller": {
            "config": {
                "discord_webhook_url": {"env": "RSS_FEED_DISCORD_WEBHOOK_URL"},
                "feeds": DEFAULT_FEEDS,
            }
        }
    }
}

RSS_FEED_CONFIG_SCHEMA = {
    "discord_webhook_url": StringSource,
    "feeds": Field(
        [Shape({"name": str, "url": str})],
        default_value=DEFAULT_FEEDS,
    ),
}


@dataclass(frozen=True)
class Feed:
    name: str
    url: str


@dataclass(frozen=True)
class FeedEntry:
    guid: str
    title: str
    link: str
    description: str


def _as_text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _clean_description(value: Any) -> str:
    return BeautifulSoup(_as_text(value), "html.parser").get_text(" ", strip=True)


def _feed_from_config(config: Mapping[str, str]) -> Feed | None:
    name = _as_text(config.get("name"))
    url = _as_text(config.get("url"))
    if not name or not url:
        return None
    return Feed(name=name, url=url)


def _parse_entries(content: bytes) -> list[FeedEntry]:
    parsed = feedparser.parse(content.lstrip(b"\xef\xbb\xbf \t\r\n"))
    if parsed.bozo:
        exception = getattr(parsed, "bozo_exception", None)
        detail = type(exception).__name__ if exception else "unknown parser error"
        raise ValueError(f"malformed feed XML ({detail})")

    entries: list[FeedEntry] = []
    for entry in parsed.entries:
        guid = _as_text(entry.get("guid") or entry.get("id"))
        if not guid:
            continue
        entries.append(
            FeedEntry(
                guid=guid,
                title=_as_text(entry.get("title")),
                link=_as_text(entry.get("link")),
                description=_clean_description(
                    entry.get("summary") or entry.get("description")
                ),
            )
        )
    return entries


def _embed_payload(entry: FeedEntry) -> dict[str, list[dict[str, Any]]]:
    return {
        "embeds": [
            {
                "title": entry.title,
                "url": entry.link,
                "description": entry.description[:300],
                "color": EMBED_COLOR,
            }
        ]
    }


def _seen_guids(postgres: PostgresResource, feed: Feed) -> set[str]:
    rows = postgres.fetch_all(sql.RSS_FEED_SEEN_GUIDS, (feed.url,))
    return {row[0] for row in rows}


async def _fetch_entries(
    client: httpx.AsyncClient, feed: Feed, context: Any
) -> list[FeedEntry]:
    try:
        response = await client.get(feed.url, timeout=REQUEST_TIMEOUT_SECONDS)
    except httpx.TimeoutException:
        context.log.warning(
            f"RSS feed {feed.name!r} timed out after {REQUEST_TIMEOUT_SECONDS:g} seconds; skipping"
        )
        return []
    except httpx.HTTPError as error:
        context.log.warning(
            f"RSS feed {feed.name!r} could not be fetched ({type(error).__name__}); skipping"
        )
        return []

    if response.status_code != 200:
        context.log.warning(
            f"RSS feed {feed.name!r} returned HTTP {response.status_code}; skipping"
        )
        return []

    try:
        return _parse_entries(response.content)
    except (TypeError, ValueError) as error:
        context.log.warning(
            f"RSS feed {feed.name!r} could not be parsed ({error}); skipping"
        )
        return []


async def _post_entry(
    client: httpx.AsyncClient,
    webhook_url: str,
    feed: Feed,
    entry: FeedEntry,
    context: Any,
) -> bool:
    try:
        response = await client.post(
            webhook_url,
            json=_embed_payload(entry),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except httpx.TimeoutException:
        context.log.warning(
            f"Discord post for RSS feed {feed.name!r} timed out; entry {entry.guid!r} was not recorded"
        )
        return False
    except httpx.HTTPError as error:
        context.log.warning(
            f"Discord post for RSS feed {feed.name!r} failed ({type(error).__name__}); "
            f"entry {entry.guid!r} was not recorded"
        )
        return False

    if not response.is_success:
        context.log.warning(
            f"Discord post for RSS feed {feed.name!r} returned HTTP {response.status_code}; "
            f"entry {entry.guid!r} was not recorded"
        )
        return False
    return True


async def _post_and_record(
    postgres: PostgresResource,
    client: httpx.AsyncClient,
    webhook_url: str,
    feed: Feed,
    entry: FeedEntry,
    context: Any,
) -> bool:
    # Keep the insert transaction open while posting. Concurrent runs then wait
    # for the first run to commit and cannot both send the same entry.
    with postgres.connection() as connection, connection.cursor() as cursor:
        cursor.execute(sql.RSS_FEED_CLAIM_ENTRY, (feed.url, entry.guid))
        if cursor.fetchone() is None:
            connection.rollback()
            return False

        if not await _post_entry(client, webhook_url, feed, entry, context):
            connection.rollback()
            return False

        connection.commit()
        return True


async def poll_feeds(
    feeds: list[Feed], webhook_url: str, postgres: PostgresResource, context: Any
) -> dict[str, int]:
    posted_count = 0

    async with httpx.AsyncClient() as client:
        for feed in feeds:
            entries = await _fetch_entries(client, feed, context)
            seen = _seen_guids(postgres, feed)
            new_entries = [entry for entry in entries if entry.guid not in seen]
            context.log.info(
                f"RSS feed {feed.name!r}: fetched {len(entries)} entries, "
                f"found {len(new_entries)} new entries"
            )

            for entry in new_entries:
                if posted_count:
                    await asyncio.sleep(POST_DELAY_SECONDS)
                if await _post_and_record(
                    postgres, client, webhook_url, feed, entry, context
                ):
                    seen.add(entry.guid)
                    posted_count += 1
                    context.log.info(
                        f"Posted RSS entry {entry.guid!r} from feed {feed.name!r}"
                    )

    context.log.info(f"RSS polling complete: posted {posted_count} new entries")
    return {"feeds_processed": len(feeds), "entries_posted": posted_count}


@op(
    config_schema=RSS_FEED_CONFIG_SCHEMA,
    required_resource_keys={"postgres"},
    description="Fetch configured RSS feeds and post unseen entries to Discord.",
)
def rss_feed_poller(context) -> dict[str, int]:
    webhook_url = _as_text(context.op_config["discord_webhook_url"])
    if not webhook_url:
        context.log.warning(
            "RSS polling skipped because no Discord webhook is configured"
        )
        return {"feeds_processed": 0, "entries_posted": 0}

    feeds: list[Feed] = []
    for raw_config in context.op_config["feeds"]:
        feed = _feed_from_config(raw_config)
        if feed is None:
            context.log.warning("Skipping RSS feed with missing name or URL")
            continue
        feeds.append(feed)

    return asyncio.run(
        poll_feeds(feeds, webhook_url, context.resources.postgres, context)
    )
