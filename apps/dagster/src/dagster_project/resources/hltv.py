from __future__ import annotations
import asyncio
import re
from datetime import UTC, date, datetime, timedelta
from os import getenv
from typing import Any

from dagster import ConfigurableResource

from dagster_project.common.config import event_forward_window_days


class HLTVResource(ConfigurableResource):
    """Fetch upcoming CS2 matches through hltv-async-api."""

    proxy_url: str = ""
    forward_window_days: int = 21
    max_retries: int = 3
    max_delay: float = 5.0

    def fetch_upcoming(self) -> list[dict[str, Any]]:
        return asyncio.run(self._fetch_upcoming())

    async def _fetch_upcoming(self) -> list[dict[str, Any]]:
        from hltv_async_api import Hltv

        kwargs: dict[str, Any] = {
            "max_retries": self.max_retries,
            "max_delay": self.max_delay,
        }
        if self.proxy_url:
            kwargs["proxy_list"] = [self.proxy_url]

        async with Hltv(**kwargs) as hltv:
            matches = await hltv.get_matches(
                days=self.forward_window_days,
                live=False,
                future=True,
            )
            if matches:
                return matches
            return await self._fetch_matches_from_events(hltv)

    async def _fetch_matches_from_events(self, hltv: Any) -> list[dict[str, Any]]:
        """Fallback when HLTV's /matches parser returns nothing (HTML drift)."""
        events = await hltv.get_events()
        today = datetime.now(UTC).date()
        window_end = today + timedelta(days=self.forward_window_days)
        matches: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for event in events:
            if not _event_overlaps_window(event, today, window_end):
                continue
            page = await hltv._fetch(
                f"https://www.hltv.org/events/{event['id']}/matches"
            )
            if page is None:
                continue
            for match in _parse_event_match_wrappers(page, event.get("title", "")):
                match_id = str(match.get("id") or "")
                if not match_id or match_id in seen_ids:
                    continue
                seen_ids.add(match_id)
                matches.append(match)

        return matches


def _event_overlaps_window(
    event: dict[str, Any],
    today: date,
    window_end: date,
) -> bool:
    start = _parse_hltv_event_date(str(event.get("start_date", "")))
    end = _parse_hltv_event_date(str(event.get("end_date", "")))
    if start is None or end is None:
        return False
    return end >= today and start <= window_end


def _parse_hltv_event_date(raw: str) -> date | None:
    """Parse HLTV event dates like ``21-6`` (day-month, current year)."""
    match = re.fullmatch(r"(\d{1,2})-(\d{1,2})", raw.strip())
    if not match:
        return None
    day, month = int(match.group(1)), int(match.group(2))
    year = datetime.now(UTC).year
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _parse_event_match_wrappers(page: Any, event_title: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for wrapper in page.find_all("div", class_="match-wrapper"):
        match_id = wrapper.get("data-match-id")
        if not match_id:
            continue

        team_names = [
            node.get_text(" ", strip=True)
            for node in wrapper.select("div.match-teamname")
            if node.get_text(" ", strip=True)
        ]
        team1 = team_names[0] if team_names else "TBD"
        team2 = team_names[1] if len(team_names) > 1 else "TBD"

        time_div = wrapper.find("div", class_="match-time")
        event_start = _parse_match_unix(time_div.get("data-unix") if time_div else None)
        date_text = event_start.strftime("%Y-%m-%d") if event_start else None
        time_text = event_start.strftime("%H:%M") if event_start else None

        meta_div = wrapper.find("div", class_="match-meta")
        maps = meta_div.get_text(" ", strip=True) if meta_div else None

        try:
            rating = int(wrapper.get("data-stars", "1"))
        except ValueError:
            rating = 1

        rows.append(
            {
                "id": str(match_id),
                "date": date_text,
                "time": time_text,
                "team1": team1,
                "team2": team2,
                "t1_id": wrapper.get("team1"),
                "t2_id": wrapper.get("team2"),
                "maps": maps,
                "rating": rating,
                "event": event_title,
                "status": None,
            }
        )
    return rows


def _parse_match_unix(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromtimestamp(int(raw) / 1000, tz=UTC)
    except (TypeError, ValueError, OSError):
        return None


hltv_resource = HLTVResource(
    proxy_url=getenv("HLTV_PROXY_URL", ""),
    forward_window_days=event_forward_window_days(),
)
