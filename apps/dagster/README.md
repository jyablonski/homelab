# Dagster Service

Dagster orchestration for homelab data pipelines. Runs as **three deployments
off one image**: the gRPC code server, the webserver (UI), and the daemon.

After deployment, the UI is reachable through Traefik at:

- `http://dagster.home`

## Architecture

```text
                ┌──────────────────┐
                │ dagster-webserver│  UI @ dagster.home (:3000)
                └────────┬─────────┘
                         │ python_module (workspace.yaml)
┌──────────────────┐     ▼      ┌──────────────────┐
│  dagster-daemon  │──────────► │dagster-code-server│  optional gRPC (:4000)
│ schedules/queue  │  same image │  (Tilt / dev only) │
└──────────────────┘            └──────────────────┘
         │
         └──────────────┬─────────────────┘
                        ▼
        Postgres  ── dagster DB (run/event/schedule metadata)
                  └─ postgres DB, source schema (assets read/write here)
```

Scheduled runs load user code from the baked-in Python module on the **daemon**
pod (`workspace.yaml`). Step subprocesses run there too, so runs no longer
depend on the optional gRPC code server staying healthy.

Two databases on the shared homelab Postgres, kept separate:

- **`dagster`** — Dagster's own metadata (runs, events, schedules). Provisioned
  by the Postgres chart (`services/postgres`) alongside the authentik DB.
- **`postgres` / `source`** — application data the assets read and summarize.

The event pipeline lands upcoming sports/esports cards into four raw tables:

- `source.events_nba`
- `source.events_cs`
- `source.events_ufc`
- `source.events_ufc_fighters`

It exposes source-specific jobs (`nba_job`, `cs_job`, `ufc_job`) for manual
reruns plus a daily `daily_events` schedule at `06:00 America/Los_Angeles`.
All event loads go through the shared `land_events()` helper, which stamps rows
and upserts via `PostgresResource.merge_polars()`.

## Directory Structure

```text
apps/dagster/
├── src/dagster_project/
│   ├── assets/
│   │   ├── ingestion/        # read raw data from source systems
│   │   ├── transformations/  # derive metrics
│   │   ├── exports/          # write results back out
│   │   └── internal/         # demo assets (opt-in, see below)
│   ├── jobs/                 # jobs + schedules; utils.create_job helper
│   ├── resources/            # ConfigurableResources + RESOURCES registry
│   ├── sensors/              # run-failure sensor
│   ├── ops/                  # reusable success/failure hooks
│   ├── sql/                  # reusable SQL by layer
│   ├── dbt_config.py         # optional dbt wiring (dormant until a project exists)
│   └── definitions.py        # discovery + Definitions assembly (entrypoint)
├── tests/
│   ├── unit/               # definitions, jobs, resources, asset materialization
│   └── integration/        # Postgres merge + end-to-end materialization (Docker)
├── dagster.yaml              # instance config (Postgres storage, queued coordinator)
├── workspace.yaml            # daemon/webserver -> python_module
├── workspace-grpc.yaml       # optional gRPC workspace for experiments
├── Dockerfile                # one image for all three roles
├── entrypoint.sh             # waits for the metadata DB, then exec
├── values-common.yaml        # shared Helm values
├── values-code-server.yaml   # role: gRPC code server
├── values-webserver.yaml     # role: UI + ingress
├── values-daemon.yaml        # role: daemon (no service)
└── secrets.sops.yaml         # DB creds + optional Slack webhook
```

## Local Development

```bash
cd apps/dagster
uv sync

# Unit tests only (default in CI):
uv run pytest -m "not integration"

# Full suite including integration tests (requires Docker and apps/django for migrations):
uv run pytest

# Run the full stack locally against your own Postgres:
DAGSTER_HOME=$PWD/.dagster_home uv run dagster dev -m dagster_project.definitions
```

Integration tests use testcontainers to start Postgres, then shell out to
`apps/django` (`manage.py migrate`) to create the `source.*` event landing
tables before exercising `merge_polars` and asset materialization.

Demo/example assets and jobs are excluded by default. Opt in with
`DAGSTER_INCLUDE_EXAMPLES=true`.

Event pipeline knobs:

- `EVENT_FORWARD_WINDOW_DAYS` — upcoming-event window shared by NBA, CS2, and UFC.
- `HLTV_PROXY_URL` — optional proxy URL for `hltv-async-api`.
- UFC schedule data is fetched from ESPN's public MMA scoreboard API.
- NBA schedule data is fetched via `nba_api` (`ScheduleLeagueV2` on stats.nba.com).
- `DB_*` — source Postgres connection fields used to build the loader DSN.

## Adding a Job

Use the helper so every job carries the standard `audience` / `domain` / `app`
tags (enforced by the test suite):

```python
from dagster_project.jobs.utils import create_job

job, schedule = create_job(
    "my_pipeline",
    selection,
    domain="reminders",
    cron_schedule="0 6 * * *",
)
```

## Adding dbt

`dbt_config.py` activates automatically when a dbt project with a
`dbt_project.yml` exists at `apps/dagster/dbt` (or `DAGSTER_DBT_PROJECT_DIR`).
Drop the project there, add `COPY dbt/ ./dbt/` to the Dockerfile, and add
`@dbt_assets` modules under `assets/transformations/`.

## Deployment

```bash
make image-build-push SERVICE=dagster
```

All three releases (`dagster-code-server`, `dagster-webserver`,
`dagster-daemon`) share the resulting `homelab/dagster` image; only their
`args`, service, and probes differ.

Edit runtime secrets (source + metadata DB passwords, Slack webhook) with:

```bash
sops apps/dagster/secrets.sops.yaml
```

> **Note:** The `dagster` database is created by the Postgres init scripts,
> which only run on a fresh data volume. On an already-initialized cluster,
> create it once manually:
>
> ```sql
> CREATE DATABASE dagster;
> CREATE USER dagster WITH PASSWORD '...';
> GRANT ALL PRIVILEGES ON DATABASE dagster TO dagster;
> ALTER DATABASE dagster OWNER TO dagster;
> ```
