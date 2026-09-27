# API Service

FastAPI application scaffold for homelab-owned HTTP APIs.

After deployment, access the app through Traefik at:

- `http://api.home`
- `http://api.home/docs`
- `http://api.home/healthz`
- `http://api.home/readyz`
- `http://api.home/metrics`
- `http://api.home/reminders`

## Directory Structure

```text
apps/api/
├── src/
│   ├── crud/                      # Database operations
│   ├── database_models/           # Database-backed request/response models
│   ├── routers/                   # FastAPI routers
│   ├── config.py                  # Settings and shared configuration
│   ├── database.py                # Postgres connectivity helpers
│   ├── dependencies.py            # Shared FastAPI dependency aliases
│   ├── log_context.py             # Request-scoped logging context
│   ├── logging_config.py          # Structured logging configuration
│   ├── main.py                    # App factory and ASGI app
│   ├── metrics.py                 # Prometheus metrics endpoint + middleware
│   ├── request_logging.py         # Structured HTTP request logging middleware
│   └── version.py                 # Application version
├── tests/
│   ├── conftest.py                # Testcontainers fixtures
│   ├── test_database.py           # Postgres integration test
│   └── test_health.py             # HTTP smoke tests
├── Dockerfile                     # Container build
├── entrypoint.sh                  # Startup DB readiness gate
├── pyproject.toml                 # Dependencies and pytest config
├── secrets.sops.yaml              # Encrypted runtime secrets
└── values.yaml                    # Helm values for workload chart
```

## Local Development

```bash
cd apps/api
uv sync
uv run pytest
```

Integration tests use `testcontainers` and skip automatically when the Docker socket is unavailable.

## Logging and metrics

The API follows the shared observability contract in [`notes/services/monitoring.md`](../../notes/services/monitoring.md). It writes one JSON object per line to stdout, which Alloy ships to Loki. `src/http_observability.py` emits exactly one access log line per request and records the shared `http_server_requests_total` and `http_server_request_duration_seconds` metrics on `/metrics`. Uvicorn's own access log is silenced in `logging_config.py`.

Access log lines include:

- `request_id`: propagated from `X-Request-ID` or generated per request, and echoed in the response header.
- `method`, `route` (template), `path`, `status`, `duration_ms`, and `client_ip`.
- `service`, `environment`, and `version`.
- `error` and `exception` (single-line traceback) when a request fails with an unhandled exception, which is also counted as a `500`.

Application logs use normal `logging.getLogger(__name__)`. The active `request_id` is attached automatically when a log is emitted while handling a request, so endpoint and service logs can be correlated with the request log in Loki.

Use `API_LOG_LEVEL` to control verbosity. The Helm values default it to `INFO`.

Example Loki queries:

```logql
{app="api"} | json
{app="api"} | json | request_id="..."
{app="api"} | json | logger="routers.reminders"
{app="api"} | json | status >= 500
```

Keep Loki labels low-cardinality. Query request-specific fields such as `request_id`, `path`, `route`, and `reminder_id` from the JSON log body instead of promoting them to labels.

## Deployment

Build and push through the repository helper:

```bash
make image-build-push SERVICE=api
```

Runtime database credentials are sourced from `apps/api/secrets.sops.yaml`. Edit them with:

```bash
sops apps/api/secrets.sops.yaml
```
