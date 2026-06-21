import asyncio
import sys
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pytest
from bs4 import BeautifulSoup

from dagster_project.resources import (
    HLTVResource,
    PostgresResource,
    RESOURCES,
    SlackResource,
)
from dagster_project.resources.hltv import (
    _event_overlaps_window,
    _parse_event_match_wrappers,
    _parse_hltv_event_date,
    _parse_match_unix,
)
from dagster_project.resources.postgres import _split_table_name

pytestmark = pytest.mark.unit


def test_registry_keys_present():
    assert set(RESOURCES) >= {"hltv", "postgres", "slack"}
    assert "nba" not in RESOURCES
    assert "ufcstats" not in RESOURCES


class TestPostgresResource:
    def test_dsn_escapes_userinfo(self):
        resource = PostgresResource(
            host="db.local",
            port="5433",
            database="events",
            user="user/name",
            password="p@ss/word",
        )
        assert (
            resource.dsn
            == "postgresql://user%2Fname:p%40ss%2Fword@db.local:5433/events"
        )

    def test_split_table_name_defaults_public_schema(self):
        assert _split_table_name("events_nba") == ("public", "events_nba")

    def test_split_table_name_rejects_invalid_target(self):
        with pytest.raises(ValueError, match="target must be"):
            _split_table_name("too.many.parts")


class TestHLTVResource:
    def test_fetch_upcoming_uses_get_matches_when_available(self, monkeypatch):
        class FakeHltv:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def get_matches(self, days, live, future):
                assert (days, live, future) == (9, False, True)
                return [{"id": 2}]

        monkeypatch.setitem(
            sys.modules,
            "hltv_async_api",
            SimpleNamespace(Hltv=lambda **kwargs: FakeHltv()),
        )
        resource = HLTVResource(forward_window_days=9)
        assert resource.fetch_upcoming() == [{"id": 2}]

    def test_fetch_upcoming_falls_back_to_event_pages(self, monkeypatch):
        class FakeHltv:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def get_matches(self, days, live, future):
                return []

        async def fake_event_fallback(self, hltv):
            assert isinstance(hltv, FakeHltv)
            return [{"id": "2395002", "team1": "FURIA", "team2": "Falcons"}]

        monkeypatch.setitem(
            sys.modules,
            "hltv_async_api",
            SimpleNamespace(Hltv=lambda **kwargs: FakeHltv()),
        )
        monkeypatch.setattr(
            HLTVResource,
            "_fetch_matches_from_events",
            fake_event_fallback,
        )
        resource = HLTVResource(forward_window_days=21)
        assert resource.fetch_upcoming()[0]["team1"] == "FURIA"

    def test_fetch_upcoming_passes_proxy_to_client(self, monkeypatch):
        captured: dict[str, object] = {}

        class FakeHltv:
            def __init__(self, **kwargs):
                captured.update(kwargs)

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def get_matches(self, days, live, future):
                return [{"id": 1}]

        monkeypatch.setitem(
            sys.modules,
            "hltv_async_api",
            SimpleNamespace(Hltv=FakeHltv),
        )
        HLTVResource(proxy_url="http://proxy.local:8080").fetch_upcoming()
        assert captured["proxy_list"] == ["http://proxy.local:8080"]

    def test_fetch_matches_from_events_parses_event_pages(self, monkeypatch):
        html = """
        <div class="match-wrapper" data-match-id="123" data-stars="2" team1="a" team2="b">
          <div class="match-teamname">Team A</div>
          <div class="match-teamname">Team B</div>
          <div class="match-time" data-unix="1700000000000"></div>
          <div class="match-meta">bo3</div>
        </div>
        """

        today = datetime.now(UTC).date()
        end = today + timedelta(days=7)

        class FakePage:
            def find_all(self, tag: str, class_: str | None = None):
                soup = BeautifulSoup(html, "lxml")
                if class_ is None:
                    return soup.find_all(name=tag)
                return soup.find_all(name=tag, class_=class_)

        class FakeHltv:
            async def get_events(self):
                return [
                    {
                        "id": "99",
                        "title": "IEM",
                        "start_date": f"{today.day}-{today.month}",
                        "end_date": f"{end.day}-{end.month}",
                    }
                ]

            async def _fetch(self, url):
                assert url.endswith("/events/99/matches")
                return FakePage()

        resource = HLTVResource(forward_window_days=21)
        matches = asyncio.run(resource._fetch_matches_from_events(FakeHltv()))
        assert matches[0]["id"] == "123"
        assert matches[0]["team1"] == "Team A"
        assert matches[0]["maps"] == "bo3"

    def test_fetch_matches_from_events_skips_missing_pages_and_duplicates(self):
        today = datetime.now(UTC).date()
        end = today + timedelta(days=7)

        class FakeHltv:
            async def get_events(self):
                return [
                    {
                        "id": "1",
                        "title": "Skip me",
                        "start_date": f"{today.day}-{today.month}",
                        "end_date": f"{end.day}-{end.month}",
                    },
                    {
                        "id": "2",
                        "title": "Keep me",
                        "start_date": f"{today.day}-{today.month}",
                        "end_date": f"{end.day}-{end.month}",
                    },
                ]

            async def _fetch(self, url):
                if url.endswith("/events/1/matches"):
                    return None
                page = BeautifulSoup(
                    """
                    <div class="match-wrapper" data-match-id="dup" data-stars="1">
                      <div class="match-teamname">A</div>
                      <div class="match-teamname">B</div>
                    </div>
                    <div class="match-wrapper" data-match-id="dup" data-stars="1">
                      <div class="match-teamname">C</div>
                      <div class="match-teamname">D</div>
                    </div>
                    """,
                    "lxml",
                )
                return page

        resource = HLTVResource(forward_window_days=21)
        matches = asyncio.run(resource._fetch_matches_from_events(FakeHltv()))
        assert len(matches) == 1
        assert matches[0]["id"] == "dup"


class TestHLTVHelpers:
    def test_parse_hltv_event_date(self):
        assert _parse_hltv_event_date("21-6") == date(datetime.now(UTC).year, 6, 21)
        assert _parse_hltv_event_date("not-a-date") is None
        assert _parse_hltv_event_date("31-2") is None

    def test_event_overlaps_window(self):
        today = date(2026, 6, 1)
        window_end = date(2026, 6, 30)
        assert _event_overlaps_window(
            {"start_date": "1-6", "end_date": "30-6"}, today, window_end
        )
        assert not _event_overlaps_window(
            {"start_date": "bad", "end_date": "30-6"}, today, window_end
        )

    def test_parse_event_match_wrappers_skips_incomplete_rows(self):
        page = BeautifulSoup(
            """
            <div class="match-wrapper">
              <div class="match-teamname">Only One Team</div>
            </div>
            <div class="match-wrapper" data-match-id="9" data-stars="bad">
              <div class="match-teamname">Alpha</div>
              <div class="match-teamname">Beta</div>
            </div>
            """,
            "lxml",
        )
        rows = _parse_event_match_wrappers(page, "Event")
        assert len(rows) == 1
        assert rows[0]["id"] == "9"
        assert rows[0]["rating"] == 1

    def test_parse_match_unix(self):
        assert _parse_match_unix(None) is None
        assert _parse_match_unix("not-a-number") is None
        parsed = _parse_match_unix("1700000000000")
        assert parsed == datetime.fromtimestamp(1700000000, tz=UTC)


class TestSlackResource:
    def test_disabled_when_no_webhook(self):
        assert SlackResource(webhook_url="").enabled is False

    def test_enabled_with_webhook(self):
        assert SlackResource(webhook_url="https://hooks.example/x").enabled is True

    def test_send_message_noop_when_disabled(self):
        # Must not raise or attempt any network call.
        SlackResource(webhook_url="").send_message("hello")

    def test_send_message_posts_when_enabled(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            "dagster_project.resources.slack.urllib.request.urlopen",
            lambda req, timeout=None: calls.append(req) or None,
        )
        SlackResource(webhook_url="https://hooks.example/x").send_message("hi")
        assert len(calls) == 1
