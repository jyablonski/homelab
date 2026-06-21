from __future__ import annotations
from dagster import ConfigurableResource

from .hltv import HLTVResource, hltv_resource
from .postgres import PostgresResource, postgres_resource
from .slack import SlackResource, slack_resource

RESOURCES: dict[str, ConfigurableResource] = {
    "hltv": hltv_resource,
    "postgres": postgres_resource,
    "slack": slack_resource,
}

__all__ = [
    "HLTVResource",
    "RESOURCES",
    "PostgresResource",
    "SlackResource",
    "hltv_resource",
    "postgres_resource",
    "slack_resource",
]
