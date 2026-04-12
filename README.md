# Homelab

![Validate](https://github.com/jyablonski/homelab/actions/workflows/validate.yaml/badge.svg?branch=main)

Personal Kubernetes homelab running on [K3s](https://k3s.io/), fully declared in Git and deployed with [Helmfile](https://github.com/helmfile/helmfile).

## Quick Start

**Prerequisites:** Linux system with `curl`, `kubectl`, `helm`, and `helmfile` installed.

```bash
# Bring up the cluster (installs K3s, deploys infra, builds local app images, deploys local apps)
make up

# Re-sync after config changes
make sync

# Run the fast local checks used by the pre-commit hook
make validate-fast

# Run the full local validation pass that mirrors CI
make validate

# Tear down everything (services, PVs, and K3s)
make down
```

Install the local git hooks with:

```bash
pre-commit install
pre-commit install --hook-type pre-push
```

### Default Access

| Service        | Access                                        | Credentials                                                     |
| -------------- | --------------------------------------------- | --------------------------------------------------------------- |
| Grafana        | [localhost:3000](http://localhost:3000)       | admin / admin                                                   |
| Prometheus     | [localhost:9090](http://localhost:9090)       | —                                                               |
| Home Assistant | [localhost:8123](http://localhost:8123)       | Setup on first visit                                            |
| Headlamp       | [localhost:8085](http://localhost:8085)       | `kubectl create token headlamp -n kube-system --duration=8760h` |
| Longhorn UI    | [localhost:30085](http://localhost:30085)     | —                                                               |
| Frigate        | [localhost:5000](http://localhost:5000)       | —                                                               |
| PostgreSQL     | [localhost:5432](postgresql://localhost:5432) | postgres / postgres                                             |

## Services

| Service                                                | Description                                                     |
| ------------------------------------------------------ | --------------------------------------------------------------- |
| [MetalLB](services/metallb/)                           | Bare-metal load balancer — assigns LAN IPs via L2/ARP           |
| [Traefik](services/traefik/)                           | Ingress controller — routes traffic by hostname                 |
| [Longhorn](services/longhorn/)                         | Distributed block storage — default StorageClass for all PVCs   |
| [Prometheus](services/prometheus/)                     | Metrics collection from pods, nodes, and Kubernetes internals   |
| [Grafana](services/prometheus/)                        | Dashboards for metrics and logs — bundled with Prometheus chart |
| [Loki](services/loki/)                                 | Log aggregation with 7-day retention                            |
| [Promtail](services/promtail/)                         | DaemonSet that ships pod logs to Loki                           |
| [PostgreSQL](services/postgres/)                       | Postgres 17 with bootstrap SQL for initial database setup       |
| [Registry](services/registry/)                         | Local OCI registry for homelab-owned application images         |
| [Workload Chart Example](apps/workload-chart-example/) | Minimal example Go app using the workload chart                 |
| [Home Assistant](services/home-assistant/)             | Home automation platform with Prometheus metrics                |
| [Frigate](services/frigate/)                           | NVR with ML object detection — monitors 4 cameras via RTSP      |
| [Mosquitto](services/mosquito/)                        | MQTT broker connecting Frigate events to Home Assistant         |
| [Pi-hole](services/pihole/)                            | DNS-level ad blocker with custom local DNS entries              |
| [Headlamp](services/headlamp/)                         | Kubernetes web dashboard                                        |
| [Authentik](services/authentik/)                       | SSO / OIDC identity provider (WIP)                              |

## Project Layout

```
homelab/
├── helmfile.yaml                 # All releases, versions, and repos in one file
├── Makefile                      # Cluster lifecycle (up / down / sync)
├── charts/                       # Reusable local Helm charts shared across apps
│   └── workload/                 # Base single-workload application chart
├── scripts/
│   ├── setup.sh                  # Namespace creation and post-install bootstrap
│   └── update-charts.sh          # Detects available Helm chart updates
├── terraform/                    # Authentik OAuth2 provider config (WIP)
├── services/                     # Infra and third-party service values/config
│   ├── prometheus/               # Each deployed service gets its own directory
│   └── ...                       #
├── apps/                         # App-owned code, Dockerfiles, and workload values
│   ├── workload-chart-example/
│   └── ...
└── notes/                        # Hardware planning, Talos setup, scratch notes
```

## App-Owned Services

For applications you build and run yourself, the intended golden path is:

```text
apps/
└── lotus-api/
    ├── Dockerfile
    ├── <source files>
    └── values.yaml
```

The directory name becomes the image name and Helm release name. Build and push with:

```bash
make image-build SERVICE=lotus-api TAG=dev
make image-push SERVICE=lotus-api TAG=dev
# or in one step
make image-build-push SERVICE=lotus-api TAG=dev
```

By default this targets `registry.home:5000/homelab/<service>:<tag>`. You can print the resolved image name with:

```bash
make image-ref SERVICE=lotus-api TAG=dev
```

## Roadmap

- **Local DNS** — Pi-hole resolving `*.home` hostnames so services are reachable by name instead of IP
- **Multi-node HA** — Expand to 3 nodes with Longhorn replication and pod anti-affinity
- **Authentik SSO** — OIDC integration across Grafana, Headlamp, and other services
- **Backups** — Velero for cluster resource and PV snapshots
