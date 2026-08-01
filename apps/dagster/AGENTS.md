# Dagster Service Guide

## Purpose and architecture

This directory contains the homelab's Dagster orchestration service. One image runs three Helm releases plus one Kubernetes Job per Dagster run.

- `dagster-webserver` serves the UI at `http://dagster.home` and reads Dagster metadata from the dedicated `dagster` Postgres database.
- `dagster-daemon` owns schedules, sensors, and the queued-run coordinator.
- `dagster-code-server` is an optional gRPC server for Tilt development and manual experiments; normal cluster runs do not depend on it.
- `K8sRunLauncher` creates a `batch/v1` run-worker Job in the `apps` namespace for each scheduled or manually launched run.

Webserver, daemon, code server, and run workers use `registry.home:5000/homelab/dagster:dev`. The worker is not a child process of the daemon: it is a separately scheduled Pod that must pull this image from the local registry.

`workspace.yaml` imports `dagster_project.definitions` directly from the baked image. Keep it as the production workspace. `workspace-grpc.yaml` is only for optional gRPC experiments.

## Layout

```text
apps/dagster/
├── src/dagster_project/
│   ├── definitions.py       # autoloads definitions under defs/
│   ├── defs/
│   │   ├── assets/          # source-specific assets by pipeline area
│   │   ├── jobs/            # jobs, schedules, and shared job helpers
│   │   └── sensors/         # sensors
│   ├── resources/           # ConfigurableResources and RESOURCES registry
│   ├── common/              # shared config, landing, validation helpers
│   ├── sql/                 # reusable SQL grouped by layer
│   ├── ops/                 # reusable hooks
│   └── docs/                # Markdown descriptions for specific jobs
├── tests/unit/              # no external service required
├── tests/integration/       # Postgres-backed coverage
├── Dockerfile               # shared image
├── entrypoint.sh            # waits for the metadata DB when enabled
├── dagster.yaml             # instance storage and K8sRunLauncher configuration
├── k8s-runner.yaml          # ServiceAccount and least-privilege namespace RBAC
└── kustomization.yaml       # runner resources and dagster-instance ConfigMap
```

## Definition discovery and code conventions

`definitions.py` recursively imports modules under `defs/assets`, `defs/jobs`, and `defs/sensors`. It collects top-level Dagster assets, asset checks, jobs, schedules, and sensors into one `Definitions` object.

Place registered definitions at module scope under `defs/`; do not add manual imports or registration lists to `definitions.py`. A new file is discovered automatically. Keep demo-only code in `defs/assets/internal/` or a module whose filename starts with `example`; those modules are excluded unless `DAGSTER_INCLUDE_EXAMPLES=true`.

Organize assets by pipeline area: use `src/dagster_project/defs/assets/ingestion/` for external reads, `src/dagster_project/defs/assets/transformations/` for derived data, `src/dagster_project/defs/assets/exports/` for writes out of the source layer, and `src/dagster_project/defs/assets/internal/` only for examples. Give each asset a stable `group_name`, meaningful `compute_kind`, description, and metadata. Add blocking `AssetCheckSpec` checks for invariants that must stop downstream work.

Use `dagster_project.resources.RESOURCES` for shared resources. Add a new `ConfigurableResource` to `resources/`, construct it from environment variables, then register it in `RESOURCES`; do not read secrets directly inside an asset. Keep secret values in `secrets.sops.yaml` and non-secret runtime settings in `values-common.yaml`.

Assets that load tabular source data should preserve the existing landing-table conventions: explicit Polars schemas, UTC datetimes, stable conflict keys, `stamp()`, merge through `PostgresResource`, and `log_landing_summary()`. Do not hard-delete source rows when a feed omits them; use the established stale/cancelled semantics when applicable.

## Jobs and schedules

Create registered asset jobs with `defs/jobs/utils.py:create_job()` rather than calling `define_asset_job()` directly. Every job must have the standard `audience`, `domain`, and lowercase `pii` tags.

Pass exactly one of `assets=` or `selection=`. Passing neither or both raises `ValueError`. `assets=` is useful for a small explicit set; use `AssetSelection` for groups, prefixes, or other composed selections.

```python
from dagster import AssetSelection
from dagster_project.common.docs import load_doc
from dagster_project.defs.jobs.utils import Audience, Domain, create_job

calendar_sync_job, calendar_sync_schedule = create_job(
    name="calendar_sync",
    selection=AssetSelection.groups("google_calendar"),
    audience=Audience.INTERNAL,
    domain=Domain.CALENDAR,
    pii=True,
    description=load_doc("events_google_calendar.md"),
    schedule="0 6 * * *",
    execution_timezone="America/Los_Angeles",
)
```

Without `schedule=`, `create_job()` returns the job. With a cron string, it returns `(job, schedule)`. Use an explicit `execution_timezone` for human-calendar schedules. Jobs are discovered from `defs/jobs/`, and schedules are collected from both jobs and sensors.

Keep integrations that can fail independently in separate jobs. For example, `calendar_sync` remains separate from `daily_events` so an OAuth error does not make sports-event ingestion look failed.

## Job-specific Markdown docs

Use `src/dagster_project/docs/<topic>.md` for user-facing operational context that would be too long for a code literal: external behavior, fetch windows, configuration, authorization/credential setup, failure modes, and deliberate non-goals.

Load the Markdown with `dagster_project.common.docs.load_doc()` and pass it as the job `description`, as `calendar_sync` does with `events_google_calendar.md`. Keep Markdown prose unwrapped. Do not put tokens, OAuth client secrets, database passwords, or decrypted SOPS content in a doc.

Update the relevant document whenever a job's external contract, schedule, data-retention behavior, or operator workflow changes. Keep implementation-specific details close to the asset code; docs should help an operator understand and run the job.

## Kubernetes run-worker model

`dagster.yaml` configures `QueuedRunCoordinator` and `K8sRunLauncher`. When a run is dequeued, the daemon creates a Job named `dagster-run-<run-id>` in `apps` using `dagster-runner`.

The `dagster-runner` ServiceAccount, Role, and RoleBinding live in `k8s-runner.yaml`. The Role is namespace-scoped and permits Dagster to manage Jobs, Pods, Pod logs/status, and Events required to observe its workers. `kustomization.yaml` also creates the un-hashed `dagster-instance` ConfigMap from `dagster.yaml`; the launcher passes that config to workers.

The worker receives the instance configuration and the environment variables listed under `run_launcher.config.env_vars`. When adding an environment variable that a worker needs, add it to the Helm values or SOPS secret and to this allowlist. Do not assume an environment variable on the daemon automatically reaches the worker.

Workers pull `registry.home:5000/homelab/dagster:dev` with `imagePullPolicy: Always`. Before running a job after changing any image-build input, publish the image:

```bash
make image-build-push SERVICE=dagster
```

An `ImagePullBackOff` or `not found` error means the worker never ran your asset code; inspect the Job/Pod and publish the image before debugging the integration. A completed worker Job is retained for 24 hours.

`helmfile sync` runs the Dagster presync hook that server-side applies `apps/dagster/` with Kustomize. Tilt renders Helmfile without hooks, so ensure Tilt also applies the Kustomize output (or run `kubectl apply -k apps/dagster`) before starting webserver, daemon, or jobs. Otherwise Pods cannot find the `dagster-runner` ServiceAccount and workers cannot find the `dagster-instance` ConfigMap.

## Development and validation

`entrypoint.sh` waits for the Dagster metadata database by default. The code server sets `DAGSTER_WAIT_FOR_DB=false`; webserver, daemon, and workers require a usable metadata database.

Tilt live-syncs `src/` and restarts Dagster processes, but a run-worker still needs the published registry image described above. Changes to `Dockerfile`, dependency locks, `dagster.yaml`, or deployment configuration require a rebuild/redeploy rather than relying on live sync.

Run the narrowest useful test while iterating, then the app suite when practical:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run --directory apps/dagster pytest
```

Use unit tests for definition discovery, jobs, schedules, resource parsing, and pure asset behavior. Add or update integration tests for database-backed materializations. Preserve the existing test markers and the 80% coverage gate.

For a stuck run, inspect the generated worker rather than only the Dagster UI:

```bash
kubectl -n apps get jobs,pods -l dagster/run-id
kubectl -n apps describe pods -l dagster/run-id
kubectl -n apps logs -l dagster/run-id --all-containers=true --prefix=true
```

If several runs are present, narrow the `dagster/run-id` selector to the affected run before describing Pods or reading logs.
