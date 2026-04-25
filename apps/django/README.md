# Django Admin Service

Django app used as:

- a schema migration tool for Postgres-backed tables
- a simple admin web interface for manual data management

After deployment in this homelab setup, access via your configured ingress path:

- `http://apps.home/django/admin`

For local-only runs, Django admin is typically at:

- `http://localhost:8000/django/admin/`

## Directory Structure

```text
apps/django/
├── src/
│   ├── core/                       # Django project + app code
│   │   ├── admin.py                # Admin registrations
│   │   ├── apps.py                 # Django app config
│   │   ├── asgi.py                 # ASGI app
│   │   ├── models.py               # Database models
│   │   ├── settings.py             # Django settings
│   │   ├── urls.py                 # URL routing
│   │   ├── wsgi.py                 # WSGI app
│   │   └── migrations/             # Django migrations
│   └── manage.py                   # Django CLI
├── tests/
│   ├── conftest.py                 # Pytest fixtures
│   ├── test_migrations.py          # Migration integration test
│   └── test_smoke.py               # Basic settings/boot test
├── Dockerfile                      # Container build
├── entrypoint.sh                   # Startup checks + migrate + run
├── pyproject.toml                  # Dependencies and pytest config
├── uv.lock                         # Locked dependencies
└── values.yaml                     # Helm values for workload chart
```

## Quick Start

From repository root:

```bash
make up
```

Teardown:

```bash
make down
```

## Runtime Behavior

`entrypoint.sh` handles startup by:

1. waiting for Postgres connectivity
2. failing fast if model changes are missing migrations
3. applying migrations
4. starting Django

## Migration Workflow

If you modify models in `src/core/models.py`, generate migrations before committing:

```bash
cd apps/django
uv run python src/manage.py makemigrations
```

Then run:

```bash
uv run python src/manage.py migrate
```

The startup script will reject boot if migrations are missing.

## Command Cheat Sheet

```bash
uv run python src/manage.py makemigrations
uv run python src/manage.py migrate
uv run python src/manage.py showmigrations
uv run pytest
```

## Notes

- Superuser bootstrap is handled by migration `core/migrations/0001_create_superuser.py` when `DJANGO_SUPERUSER_USERNAME` and `DJANGO_SUPERUSER_PASSWORD` are set.
- DB credentials and Django superuser credentials are currently sourced from `apps/django/secrets.sops.yaml`.
- This service deploys through the shared `charts/workload` chart via the `django` release in `helmfile.yaml`.
