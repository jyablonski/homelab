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


class AppContextFilter(logging.Filter):
    def __init__(self, app_name: str, environment: str, version: str) -> None:
        super().__init__()
        self.app_name = app_name
        self.environment = environment
        self.version = version

    def filter(self, record: logging.LogRecord) -> bool:
        record.app = self.app_name
        record.environment = self.environment
        record.version = self.version
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=timezone.utc,
            ).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key not in RESERVED_LOG_RECORD_FIELDS and key not in payload:
                payload[key] = value

        if record.exc_info:
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
                    "app_name": settings.app_name,
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
                "uvicorn.access": {
                    "handlers": ["default"],
                    "level": settings.log_level.upper(),
                    "propagate": False,
                },
            },
        }
    )
