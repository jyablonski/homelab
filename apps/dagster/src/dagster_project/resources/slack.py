from __future__ import annotations
import json
import urllib.request
from os import getenv

from dagster import ConfigurableResource, get_dagster_logger


class SlackResource(ConfigurableResource):
    """Posts messages to a Slack incoming webhook."""

    webhook_url: str = ""

    @property
    def enabled(self) -> bool:
        return bool(self.webhook_url)

    def send_message(self, text: str) -> None:
        if not self.enabled:
            get_dagster_logger().info("Slack disabled, skipping message: %s", text)
            return

        payload = json.dumps({"text": text}).encode("utf-8")
        request = urllib.request.Request(
            self.webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(request, timeout=10)  # noqa: S310 (trusted webhook URL)


# Optional: read at definition time so a missing var disables Slack instead of
# raising on first use, unlike a required EnvVar(...) reference.
slack_resource = SlackResource(webhook_url=getenv("DAGSTER_SLACK_WEBHOOK_URL", ""))
