from contextlib import contextmanager
from time import perf_counter
from typing import Iterator

from prometheus_client import Counter, Histogram

HTTP_REQUESTS = Counter(
    "mcp_http_requests_total",
    "Total HTTP requests served by the MCP app.",
    ("method", "path", "status_code"),
)

HTTP_REQUEST_DURATION = Histogram(
    "mcp_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ("method", "path", "status_code"),
)

TOOL_CALLS = Counter(
    "mcp_tool_calls_total",
    "Total MCP tool calls.",
    ("tool", "result"),
)

TOOL_DURATION = Histogram(
    "mcp_tool_duration_seconds",
    "MCP tool latency in seconds.",
    ("tool",),
)


@contextmanager
def observe_tool(tool: str) -> Iterator[None]:
    start = perf_counter()
    result = "success"
    try:
        yield
    except Exception:
        result = "error"
        raise
    finally:
        TOOL_CALLS.labels(tool, result).inc()
        TOOL_DURATION.labels(tool).observe(perf_counter() - start)
