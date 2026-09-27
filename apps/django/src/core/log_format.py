import json
import logging
import os
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

# Matches the Loki `app` label and the Helm release name. Field names follow
# the shared log schema in notes/services/monitoring.md.
SERVICE_NAME = "django"

request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)

RESERVED_LOG_RECORD_FIELDS = frozenset(
    logging.LogRecord(
        name="",
        level=0,
        pathname="",
        lineno=0,
        msg="",
        args=(),
        exc_info=None,
    ).__dict__
)

# django.request and django.server attach the request/socket objects, which
# only serialize to unhelpful reprs.
IGNORED_EXTRA_FIELDS = frozenset({"request", "server_time"})

LEVEL_NAMES = {"WARNING": "warn"}


class AppContextFilter(logging.Filter):
    def __init__(self) -> None:
        super().__init__()
        self.environment = os.getenv("DJANGO_ENVIRONMENT", "local")

    def filter(self, record: logging.LogRecord) -> bool:
        record.service = SERVICE_NAME
        record.environment = self.environment
        request_id = request_id_context.get()
        if request_id and not hasattr(record, "request_id"):
            record.request_id = request_id
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "time": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": LEVEL_NAMES.get(record.levelname, record.levelname.lower()),
            "msg": record.getMessage(),
            "logger": record.name,
        }

        for key, value in record.__dict__.items():
            if (
                key not in RESERVED_LOG_RECORD_FIELDS
                and key not in IGNORED_EXTRA_FIELDS
                and key not in payload
            ):
                payload[key] = value

        # One line per event: the traceback goes in a field instead of
        # spilling across lines that Loki would ingest separately.
        if record.exc_info and record.exc_info[1] is not None:
            exc = record.exc_info[1]
            payload["error"] = f"{type(exc).__name__}: {exc}"
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str, separators=(",", ":"))
