# Workload Chart Example

Minimal example application that follows the repo's app-owned service golden path:

- Go source in `apps/workload-chart-example/src/`
- Docker image built from `apps/workload-chart-example/Dockerfile`
- Deployment managed by `charts/workload`

## Endpoints

- `GET /random` returns a random 32-character hex string
- `GET /metrics` exposes Prometheus-format metrics
- `GET /health/live` returns `ok`
- `GET /health/ready` returns `ok`

## Why this service exists

This is a bare-bones example to test:

- building and pushing an image to the local registry
- scraping application metrics with Prometheus
- collecting container stdout logs with Promtail/Loki
- exposing an app-owned workload through Traefik on a shared `apps.home` host

## Build and push

```bash
make image-build-push SERVICE=workload-chart-example TAG=dev
```

## Deploy

```bash
helmfile sync
```

## Ingress curl test

This example is exposed at `http://apps.home/workload-chart/api`.
Traefik strips the `/workload-chart/api` prefix before forwarding to the pod, so the Go app can keep serving its internal root-level routes:

- `GET /random`
- `GET /metrics`
- `GET /health/live`
- `GET /health/ready`

`make up` runs `scripts/setup-ingress-home.sh`, which adds a persistent `/etc/hosts` entry for `apps.home` pointing at the pinned Traefik MetalLB IP. If you are syncing manually on a machine that has not run `make up`, run that script once or add the host entry yourself.

Then you can hit it directly:

```bash
curl http://apps.home/workload-chart/api/random
```

You can also inspect health and metrics through the ingress path:

```bash
curl http://apps.home/workload-chart/api/health/ready
curl http://apps.home/workload-chart/api/metrics
```

## Metrics and logs

- `/metrics` is served by the official Prometheus Go client library
- Prometheus scraping is still enabled through the chart `ServiceMonitor` and the internal `ClusterIP` service
- the liveness and readiness probes still hit the app's root-level health endpoints inside the cluster
- Grafana can visualize the metrics through the existing Prometheus datasource
- Request logs are written to stdout, so Promtail/Loki should ingest them automatically
- the example now uses the chart HPA with a floor of 2 replicas and can scale up to 5 replicas at 80% average CPU utilization

## Important note

Because access now goes through a normal `ClusterIP` service plus Traefik ingress, this example no longer depends on `hostPort` or `deploymentStrategy.type: Recreate`. That removes the node-local port collision issue and gives the release a clean path to horizontal scaling.
