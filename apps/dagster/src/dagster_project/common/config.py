from __future__ import annotations
from os import getenv


def event_forward_window_days() -> int:
    return int(getenv("EVENT_FORWARD_WINDOW_DAYS", "21"))
