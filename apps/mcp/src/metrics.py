from contextlib import contextmanager
from time import perf_counter
from typing import Iterator

from prometheus_client import Counter, Histogram

# Shared HTTP metric names across every homelab app; Prometheus adds the `app`
# label from the ServiceMonitor, so names carry no service prefix.
HTTP_REQUESTS = Counter(
    "http_server_requests_total",
    "Total HTTP requests handled.",
    ("method", "route", "status"),
)

HTTP_REQUEST_DURATION = Histogram(
    "http_server_request_duration_seconds",
    "HTTP request duration in seconds.",
    ("method", "route"),
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
