import json
import logging
import logging.config
from datetime import datetime, timezone
from typing import Any

from config import Settings
from log_context import RequestContextFilter
from version import __version__

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


# Matches the Loki `app` label and the Helm release name. Field names follow
# the shared log schema in notes/services/monitoring.md.
SERVICE_NAME = "runner"

# uvicorn attaches an ANSI-colored duplicate of each message.
IGNORED_EXTRA_FIELDS = frozenset({"color_message"})

LEVEL_NAMES = {"WARNING": "warn"}


class AppContextFilter(logging.Filter):
    def __init__(self, service: str, environment: str, version: str) -> None:
        super().__init__()
        self.service = service
        self.environment = environment
        self.version = version

    def filter(self, record: logging.LogRecord) -> bool:
        record.service = self.service
        record.environment = self.environment
        record.version = self.version
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "time": datetime.fromtimestamp(
                record.created,
                tz=timezone.utc,
            ).isoformat(),
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


def configure_logging(settings: Settings) -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "app_context": {
                    "()": AppContextFilter,
                    "service": SERVICE_NAME,
                    "environment": settings.environment,
                    "version": __version__,
                },
                "request_context": {
                    "()": RequestContextFilter,
                },
            },
            "formatters": {
                "json": {
                    "()": JsonFormatter,
                },
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                    "filters": ["app_context", "request_context"],
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "handlers": ["default"],
                "level": settings.log_level.upper(),
            },
            "loggers": {
                "uvicorn": {
                    "handlers": ["default"],
                    "level": settings.log_level.upper(),
                    "propagate": False,
                },
                "uvicorn.error": {
                    "level": settings.log_level.upper(),
                },
                # HttpObservabilityMiddleware writes the structured access
                # log; silence uvicorn's so each request logs exactly once,
                # even under the dev overlay that drops --no-access-log.
                "uvicorn.access": {
                    "handlers": [],
                    "propagate": False,
                },
            },
        }
    )
