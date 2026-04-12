# Workload chart

Reusable Helm chart for a single deployable application workload. It is designed for this repo's pattern of one Helm release per service, with shared infrastructure such as Postgres, Redis, Traefik, Prometheus, and Longhorn managed separately at the cluster level.

## V1 scope

- Single `Deployment`
- Single application container
- Optional `Service`
- Optional `Ingress`, including a small Traefik strip-prefix helper for shared-host path routing
- Optional HPA
- Optional `ServiceMonitor`
- Plain env vars, secret-backed env vars, and `envFrom`
- Existing Secret / ConfigMap mounts through `extraVolumes` and `extraVolumeMounts`
- Service account, pod metadata, probes, resources, and scheduling controls
- Optional deployment strategy override for cases like single-node `hostPort` workloads
- Optional `hostPort` binding for node-local access when explicitly desired

## Intentionally out of scope

- CronJobs
- StatefulSets and PVC management
- Sidecars and init containers
- Multiple service ports
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
- the image is tagged as `registry.home:5000/homelab/<service>:<tag>`

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
- For app-owned services in this repo, the clean default is a normal `ClusterIP` service plus Traefik ingress. If you want a shared `apps.home` host with per-app path prefixes, the chart can attach a Traefik `StripPrefix` middleware so the application still serves `/`-rooted routes internally.
- If a workload eventually needs a different controller type, multiple ports, sidecars, or persistence, that is a good signal for a separate chart rather than stretching this one too far.

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

## Examples

- `examples/frontend.yaml` shows a public web service with ingress, HPA, and metrics scraping.
- `examples/internal-api.yaml` shows an internal API with existing Secret / ConfigMap wiring and no ingress.
