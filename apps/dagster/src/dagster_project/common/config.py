from __future__ import annotations
from os import getenv


def event_forward_window_days() -> int:
    return int(getenv("EVENT_FORWARD_WINDOW_DAYS", "21"))


def calendar_lookback_days() -> int:
    return int(getenv("CALENDAR_LOOKBACK_DAYS", "1"))


def calendar_forward_window_days() -> int:
    return int(getenv("CALENDAR_FORWARD_WINDOW_DAYS", "14"))
