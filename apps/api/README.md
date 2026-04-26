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
│   ├── main.py                    # App factory and ASGI app
│   ├── metrics.py                 # Prometheus metrics endpoint + middleware
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

## Deployment

Build and push through the repository helper:

```bash
make image-build-push SERVICE=api TAG=dev
```

Runtime database credentials are sourced from `apps/api/secrets.sops.yaml`. Edit them with:

```bash
sops apps/api/secrets.sops.yaml
```
