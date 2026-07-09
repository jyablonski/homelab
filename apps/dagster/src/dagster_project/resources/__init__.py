from __future__ import annotations
from dagster import ConfigurableResource

from .google_calendar import GoogleCalendarResource, google_calendar_resource
from .hltv import HLTVResource, hltv_resource
from .postgres import PostgresResource, postgres_resource
from .slack import SlackResource, slack_resource

RESOURCES: dict[str, ConfigurableResource] = {
    "google_calendar": google_calendar_resource,
    "hltv": hltv_resource,
    "postgres": postgres_resource,
    "slack": slack_resource,
}

__all__ = [
    "GoogleCalendarResource",
    "HLTVResource",
    "RESOURCES",
    "PostgresResource",
    "SlackResource",
    "google_calendar_resource",
    "hltv_resource",
    "postgres_resource",
    "slack_resource",
]
