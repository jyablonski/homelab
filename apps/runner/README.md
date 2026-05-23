# Runner

Internal FastAPI app for listing and running approved Kubernetes runnables.

Runner discovers `CronJob` objects labeled by the workload chart:

```text
homelab.jacob/runnable=true
```

It can create one-off `Job` runs from those CronJob templates. The job definitions still live in each app's `values.yaml`; Runner is only a control surface.

## UI

The runner UI is a dashboard at `/runner` (via Traefik). It loads jobs from `GET /api/jobs`, supports search and status filters, shows a per-job history sparkline, and opens a confirmation modal with a Grafana link after `POST /api/jobs/{app}/{name}/run`.

Click a job row to open its full run history. The list view still shows a short sparkline summary per job.

## API

- `GET /api/jobs` — app, name, schedule, status, last run, history
- `GET /api/jobs/{app}/{name}/runs` — full run history for a job
- `POST /api/jobs/{app}/{name}/run` — `{ runId, namespace, grafanaUrl }`

## Grafana log links

Each run links to Loki with:

- `container` set to the runnable job name (matches the CronJob container name)
- `pod` matched to every pod with `job-name=<Kubernetes Job name>` for that run
- a time range from the Job start/finish times (with a small buffer)

`RUNNER_LOKI_DATASOURCE_UID` must match the Loki datasource UID in Grafana (**Connections → Data sources → Loki**). Links use Explore `left=` (v0 array form: time range, datasource UID, LogQL with `namespace`, `container`, and `pod` labels). After changing link logic, rebuild and restart the **runner** deployment.
