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
- accessing the service on `localhost:10032` without `kubectl port-forward`

## Build and push

```bash
make image-build-push SERVICE=workload-chart-example TAG=dev
```

## Deploy

```bash
helmfile sync
```

## Local curl test

This example binds the pod to `127.0.0.1:10032` on the node via `hostPort`.
Because that port can only be used by one pod at a time on a single node, the example also uses `deploymentStrategy.type: Recreate` to avoid rollout collisions during updates.

If your K3s node is the same machine where you are running `curl`, you can hit it directly:

```bash
curl http://localhost:10032/random
```

You can also inspect metrics directly:

```bash
curl http://localhost:10032/metrics
```

## Metrics and logs

- `/metrics` is served by the official Prometheus Go client library
- Prometheus scraping is enabled through the chart `ServiceMonitor` and the internal `ClusterIP` service
- Grafana can visualize the metrics through the existing Prometheus datasource
- Request logs are written to stdout, so Promtail/Loki should ingest them automatically

## Important note

`localhost:10032` only works on the machine that is actually running the pod. This example is meant for single-node or local-machine use, which is why it uses `replicaCount: 1` and an explicit `hostPort`.
