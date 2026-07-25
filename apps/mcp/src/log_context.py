from contextvars import ContextVar
import logging

request_id_context: ContextVar[str] = ContextVar("request_id", default="")


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        request_id = request_id_context.get()
        if request_id:
            record.request_id = request_id
        return True
