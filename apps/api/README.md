# API Service

FastAPI application scaffold for homelab-owned HTTP APIs.

After deployment, access the app through Traefik at:

- `http://apps.home/api`
- `http://apps.home/api/docs`
- `http://apps.home/api/healthz`
- `http://apps.home/api/readyz`
- `http://apps.home/api/metrics`
- `http://apps.home/api/reminders`

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

## Logging

The API writes structured JSON logs to stdout so Kubernetes, Promtail, and Loki can collect them without sidecar or file-based logging. Uvicorn's default access log is disabled in the container because `request_logging.py` emits one structured request log per HTTP request.

Request logs include:

- `request_id`: propagated from `X-Request-ID` or generated per request.
- `method`, `path`, `route`, `status_code`, `duration_ms`, and `client_ip`.
- `app`, `environment`, and `version` from application settings.

Application logs use normal `logging.getLogger(__name__)`. The active `request_id` is attached automatically when a log is emitted while handling a request, so endpoint and service logs can be correlated with the request log in Loki.

Use `API_LOG_LEVEL` to control verbosity. The Helm values default it to `INFO`.

Example Loki queries:

```logql
{app="api"} | json
{app="api"} | json | request_id="..."
{app="api"} | json | logger="routers.reminders"
{app="api"} | json | status_code >= 500
```

Keep Loki labels low-cardinality. Query request-specific fields such as `request_id`, `path`, `route`, and `reminder_id` from the JSON log body instead of promoting them to labels.

## Deployment

Build and push through the repository helper:

```bash
make image-build-push SERVICE=api TAG=dev
```

Runtime database credentials are sourced from `apps/api/secrets.sops.yaml`. Edit them with:

```bash
sops apps/api/secrets.sops.yaml
```
