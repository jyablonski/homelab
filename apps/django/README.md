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
│   │   ├── migrations/             # Django migrations
│   │   └── static/admin/css/       # Quiet theme (`quiet.css`)
│   ├── templates/admin/            # Admin template overrides (`base_site.html`)
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

## Commands

```bash
make migrate
make migrate core 0003_reminders_table
make migrations
make showmigrations
```

## Runtime Behavior

`entrypoint.sh` handles startup by:

1. waiting for Postgres connectivity
2. failing fast if model changes are missing migrations
3. running **`migrate`** only when the database has not been initialized yet; otherwise skipping (use **`make migrate`** to apply schema changes)
4. starting Django

## Static files and admin UI

[WhiteNoise](https://whitenoise.readthedocs.io/) serves admin CSS/JS from `STATIC_ROOT` at `/django/static/` (aligned with the `/django` ingress prefix). The **Docker build** runs `collectstatic`; nothing serves static files at container startup beyond that.

Admin appearance uses the **Quiet** theme: `src/core/static/admin/css/quiet.css` (Django variable overrides) plus `src/templates/admin/base_site.html` (brand bar, font links). Edit those files to adjust colors or the header title.

## Migration Workflow

If you modify models in `src/core/models.py`, generate migrations before committing (from repo root **`make migrations`**, or **`cd apps/django`** and **`uv run python src/manage.py makemigrations`**). Apply with **`make migrate`**. The startup script will reject boot if migrations are missing. Tests: **`cd apps/django`** and **`uv run pytest`**.

## Notes

- On first boot against an empty database, the entrypoint applies all migrations once. After that, schema changes are applied manually with **`make migrate`** (cluster or local).
- Upgrading **Django** may change bundled admin assets; rebuild the image so `collectstatic` picks them up. No separate CSS/HTML maintenance unless you add **custom** static files or templates—in that case keep them under app `static/` / `templates/` as usual; the same build-time `collectstatic` includes them.
- Superuser bootstrap is handled by migration `core/migrations/0001_create_superuser.py` when `DJANGO_SUPERUSER_USERNAME` and `DJANGO_SUPERUSER_PASSWORD` are set.
- DB credentials and Django superuser credentials are currently sourced from `apps/django/secrets.sops.yaml`.
