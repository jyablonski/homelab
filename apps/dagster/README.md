# Dagster Service

Dagster orchestration for homelab data pipelines. The service runs from one image with separate Kubernetes components for the web UI, daemon, and optional gRPC code server.

The UI is available through Traefik at:

- `http://dagster.home`

## Architecture

```text
                +-------------------+
                | dagster-webserver |  UI @ dagster.home (:3000)
                +---------+---------+
                          | imports dagster_project.definitions
+------------------+      v       +---------------------+
| dagster-daemon   |------------> | dagster-code-server | optional gRPC
| schedules + queue|  same image  | for experiments     |
+--------+---------+              +---------------------+
         |
         v
       Kubernetes Jobs
       - one run-worker Job per Dagster run
         |
         v
       Postgres
       - dagster DB: Dagster metadata
       - postgres DB/source schema: application data
```

- `dagster-webserver`: serves the Dagster UI, reads run metadata from Postgres, and imports `dagster_project.definitions` so the UI can show assets, jobs, schedules, and sensors.
- `dagster-daemon`: runs schedules, sensors, and the queued-run coordinator. `K8sRunLauncher` creates a separate Kubernetes Job for each scheduled or queued run.
- `dagster-code-server`: optional gRPC process that exposes the same user-code definitions to Dagster tools or experiments. The default workspace imports the Python module directly, so normal runs do not depend on this component.

The webserver, daemon, code server, and run-worker Jobs all use the same Dagster image. Run workers receive the Dagster instance config, database settings, source database settings, and app environment through `K8sRunLauncher`.

## Directory Structure

```text
apps/dagster/
|-- src/dagster_project/
|   |-- assets/          # Dagster assets grouped by pipeline area
|   |-- jobs/            # jobs, schedules, and create_job helper
|   |-- resources/       # ConfigurableResources and RESOURCES registry
|   |-- sensors/         # run-failure sensor
|   |-- ops/             # reusable hooks
|   |-- sql/             # reusable SQL by layer
|   `-- definitions.py   # discovery and Definitions assembly
|-- tests/
|   |-- unit/            # definitions, jobs, resources, assets
|   `-- integration/     # Postgres-backed resource/materialization tests
|-- Dockerfile           # shared image for all Dagster components
|-- entrypoint.sh        # waits for metadata DB, then execs Dagster
`-- values-daemon.yaml   # example component-specific Helm values
```

Each component sets its own Helm values for arguments, service exposure, probes, and resource requests while sharing the same image and common environment.

Demo/example assets and jobs are excluded by default. Set `DAGSTER_INCLUDE_EXAMPLES=true` to include them.

## Adding a Job

1. Add or update the asset under `src/dagster_project/assets/<area>/`.
2. Give the asset a stable group name with Dagster metadata/decorators.
3. Add the job under `src/dagster_project/jobs/<area>.py`.
4. Use `create_job()` and select the asset or group from step 1.
5. Set `domain=` so the standard job tags stay complete.
6. Add `cron_schedule=` and `execution_timezone=` when it should be scheduled.
7. Add unit tests under `tests/unit/` for the asset, job, and schedule.
8. Add integration coverage under `tests/integration/` if Postgres is involved.
9. Run the narrowest useful Dagster tests before handoff.
