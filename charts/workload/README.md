# Workload chart

Reusable Helm chart for a single deployable application workload. It is designed for this repo's pattern of one Helm release per service, with shared infrastructure such as Postgres, Redis, Traefik, Prometheus, and Longhorn managed separately at the cluster level.

## V1 scope

- Single `Deployment`
- Single application container
- Optional `Service`
- Optional `Ingress`, including a small Traefik strip-prefix helper for shared-host path routing
- Optional HPA
- Optional `ServiceMonitor`
- Optional app-owned `CronJob` entries for scheduled or manual-only runs
- Plain env vars, secret-backed env vars, and `envFrom`
- Existing Secret / ConfigMap mounts through `extraVolumes` and `extraVolumeMounts`
- Service account, pod metadata, probes, resources, and scheduling controls
- Optional deployment strategy override for cases like single-node `hostPort` workloads
- Optional `hostPort` binding for node-local access when explicitly desired

## Intentionally out of scope

- StatefulSets and PVC management
- Sidecars and init containers
- Multiple service ports
- Multi-container jobs or workflow orchestration
- Bundled app-specific infra such as Postgres or Redis

## Recommended repo structure

Put the shared chart here, then keep real app values in their own service directories:

```text
charts/
└── workload/
    ├── Chart.yaml
    ├── templates/
    └── examples/
services/
├── registry/
│   └── values.yaml
├── prometheus/
│   └── values.yaml
└── ...
apps/
├── lotus-frontend/
│   ├── Dockerfile
│   ├── src/...
│   └── values.yaml
├── lotus-api/
│   ├── Dockerfile
│   ├── jobs/...
│   ├── app/...
│   └── values.yaml
└── lotus-worker/
    ├── Dockerfile
    ├── worker/...
    └── values.yaml
```

This chart assumes the image is already built and available in a registry. In this repo, the intended golden path is:

- source code lives in `apps/<service>/`
- `apps/<service>/Dockerfile` builds the app image
- `apps/<service>/values.yaml` configures the Helm release
- the Helm release `name` matches `apps/<service>/` (used for image name and default labels)
- the image is built as `registry.home:5000/homelab/<service>:<tag>` via `make image-build-push SERVICE=<service>`
- optional scripts live in `apps/<service>/jobs/` and are copied into the same image

## Homelab values shape (v0.2)

This repo runs one personal K3s cluster, not multiple environments. Chart defaults are tuned for that workflow: build with `make image-build-push SERVICE=<app>`, sync with Helmfile, and rely on a single `dev` image tag unless you explicitly override it.

App-owned `values.yaml` files only need app-specific settings. The chart fills in the rest:

```yaml
service:
  port: 8080

serviceMonitor:
  enabled: true

readinessProbe:
  httpGet:
    path: /healthz
    port: http
  periodSeconds: 10
  failureThreshold: 3

livenessProbe:
  httpGet:
    path: /healthz
    port: http
  periodSeconds: 20
  failureThreshold: 3
```

### Defaults and why

| Value                           | Default                                     | Why                                                                                       |
| ------------------------------- | ------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `image.repository`              | `registry.home:5000/homelab/<Release.Name>` | Matches `apps/<app>/`, helmfile release `name`, and `make image-build-push SERVICE=<app>` |
| `image.tag`                     | `dev`                                       | Single homelab image line; no per-environment tags in app values                          |
| `image.pullPolicy`              | `Always`                                    | Ensures nodes pull fresh layers after local registry pushes                               |
| `scale.replicas`                | `1`                                         | Sufficient for most homelab apps; use `scale.autoscaling` when you need more              |
| `service.port`                  | — (required in app values)                  | Sets both Service port and container listen port                                          |
| `service.targetPort`            | falls back to `service.port`                | Escape hatch when ingress Service port ≠ app port (see `examples/frontend.yaml`)          |
| `podLabels`                     | `component: <Release.Name>`                 | Avoids repeating the same label in every app file                                         |
| `serviceMonitor` (when enabled) | `/metrics`, `30s`, `release: prometheus`    | Aligns with kube-prometheus-stack in this cluster                                         |

Probes are **not** defaulted: paths differ per app (`/healthz`, `/django/healthz`, `/health/ready`, etc.), so each app keeps its own `readinessProbe` / `livenessProbe` blocks.

Use `scale.autoscaling` for HPA. When autoscaling is enabled, the Deployment omits `replicas` and the HPA controls scale. Legacy top-level `replicaCount`, `containerPort`, and `autoscaling` still work but are deprecated.

## Helmfile wiring

Use a separate Helm release per deployable workload:

```yaml
releases:
  - name: lotus-frontend
    namespace: apps
    createNamespace: true
    chart: ./charts/workload
    values:
      - apps/lotus-frontend/values.yaml

  - name: lotus-api
    namespace: apps
    chart: ./charts/workload
    values:
      - apps/lotus-api/values.yaml

  - name: lotus-worker
    namespace: apps
    chart: ./charts/workload
    values:
      - apps/lotus-worker/values.yaml
```

## Design notes

- Resource names default to the Helm release name, so a release named `lotus-frontend` renders to `lotus-frontend` rather than `lotus-frontend-workload`.
- The chart gives first-class values to the common cases and keeps only a small escape hatch for mounted config through `extraVolumes` and `extraVolumeMounts`.
- Replicated or autoscaled workloads get a default preferred pod anti-affinity unless you provide an explicit `affinity:` block, which keeps the chart aligned with this repo's linting and HA direction.
- Jobs reuse the workload image and inherited pod settings. They are intended for app-owned maintenance scripts, not as a general workflow engine.
- For app-owned services in this repo, the clean default is a normal `ClusterIP` service plus Traefik ingress. If you want a shared `apps.home` host with per-app path prefixes, the chart can attach a Traefik `StripPrefix` middleware so the application still serves `/`-rooted routes internally.
- If a workload eventually needs a different controller type, multiple ports, sidecars, complex jobs, or persistence, that is a good signal for a separate chart rather than stretching this one too far.

## Ingress patterns

Host-based ingress works well for standalone UIs:

```yaml
ingress:
  enabled: true
  className: traefik
  hosts:
    - host: lotus.home
      paths:
        - path: /
          pathType: Prefix
```

For app-owned APIs on the shared `apps.home` host, use a path prefix and let Traefik strip it before the request reaches the pod:

```yaml
ingress:
  enabled: true
  className: traefik
  hosts:
    - host: apps.home
      paths:
        - path: /lotus-api/api
          pathType: Prefix
  traefik:
    stripPrefix:
      enabled: true
      prefixes:
        - /lotus-api/api
```

That keeps the application code, probes, and `ServiceMonitor` paths simple because they can continue to use `/health/*`, `/metrics`, and other root-level routes internally.

## Jobs

Use `jobs:` for app-owned scripts that should run from the same image as the main workload. A job entry renders as a Kubernetes `CronJob`.

Manual-only jobs should set `suspend: true`. Kubernetes still requires a valid cron schedule, so the chart defaults suspended jobs to `0 0 * * *`; the suspend flag prevents scheduled execution.

```yaml
jobs:
  print-reminders-rows:
    enabled: true
    runnable: true
    suspend: true
    description: Print reminder table row count
    command: ["python"]
    args: ["/app/jobs/print-reminders-rows/main.py"]
```

Scheduled jobs set `suspend: false` and provide `schedule`:

```yaml
jobs:
  refresh-reminders:
    enabled: true
    runnable: true
    suspend: false
    schedule: "0 * * * *"
    description: Refresh reminder metadata
    command: ["python"]
    args: ["/app/jobs/refresh-reminders/main.py"]
```

Every job uses `concurrencyPolicy: Forbid` by default. This prevents overlapping scheduled runs. Manual runners should still check for active Jobs with the same labels before creating another run.

Run a suspended job on demand from its CronJob template:

```bash
kubectl create job \
  --namespace apps \
  --from=cronjob/api-print-reminders-rows \
  api-print-reminders-rows-manual-$(date +%s)
```

Jobs inherit these workload settings by default:

- image repository, tag, and pull policy
- image pull secrets
- service account and automount setting
- env, secret env, config map env, extra env, and envFrom
- resources
- extra volumes and volume mounts
- pod labels, pod annotations, affinity, node selector, and tolerations

Each job may override `command`, `args`, `env`, `extraEnv`, `envFrom`, `resources`, `restartPolicy`, `backoffLimit`, `ttlSecondsAfterFinished`, `successfulJobsHistoryLimit`, `failedJobsHistoryLimit`, `startingDeadlineSeconds`, and `activeDeadlineSeconds`.

Runnable jobs are labeled for discovery:

```yaml
homelab.jacob/runnable: "true"
homelab.jacob/app: api
homelab.jacob/job: print-reminders-rows
```

## Examples

- `examples/frontend.yaml` shows a public web service with ingress, HPA, and metrics scraping.
- `examples/internal-api.yaml` shows an internal API with existing Secret / ConfigMap wiring and no ingress.
