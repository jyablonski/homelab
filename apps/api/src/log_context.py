import logging
from contextvars import ContextVar

request_id_context: ContextVar[str | None] = ContextVar(
    "request_id",
    default=None,
)


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        request_id = request_id_context.get()
        if request_id and not hasattr(record, "request_id"):
            record.request_id = request_id
        return True
