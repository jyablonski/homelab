# Homelab

![Validate](https://github.com/jyablonski/homelab/actions/workflows/validate.yaml/badge.svg?branch=main)

Personal Kubernetes homelab running on [K3s](https://k3s.io/), fully declared in Git and deployed with [Helmfile](https://github.com/helmfile/helmfile).

## Quick Start

**Prerequisites:** Linux system with `curl`, `kubectl`, `helm`, and `helmfile` installed.

```bash
# Bring up the cluster (installs K3s, creates namespaces, deploys all services)
make up

# Re-sync after config changes
make sync

# Tear down everything (services, PVs, and K3s)
make down
```

After deployment, find service IPs with:

```bash
kubectl get svc -A | grep LoadBalancer
```

### Default Access

| Service        | Port  | Credentials                                                     |
| -------------- | ----- | --------------------------------------------------------------- |
| Grafana        | 3000  | admin / admin                                                   |
| Prometheus     | 9090  | —                                                               |
| Home Assistant | 8123  | Setup on first visit                                            |
| Headlamp       | 8085  | `kubectl create token headlamp -n kube-system --duration=8760h` |
| Longhorn UI    | 30085 | —                                                               |
| Frigate        | 5000  | —                                                               |
| PostgreSQL     | 5432  | postgres / postgres                                             |

## Services

| Service                                    | Description                                                     |
| ------------------------------------------ | --------------------------------------------------------------- |
| [MetalLB](services/metallb/)               | Bare-metal load balancer — assigns LAN IPs via L2/ARP           |
| [Traefik](services/traefik/)               | Ingress controller — routes traffic by hostname                 |
| [Longhorn](services/longhorn/)             | Distributed block storage — default StorageClass for all PVCs   |
| [Prometheus](services/prometheus/)         | Metrics collection from pods, nodes, and Kubernetes internals   |
| [Grafana](services/prometheus/)            | Dashboards for metrics and logs — bundled with Prometheus chart |
| [Loki](services/loki/)                     | Log aggregation with 7-day retention                            |
| [Promtail](services/promtail/)             | DaemonSet that ships pod logs to Loki                           |
| [PostgreSQL](services/postgres/)           | Postgres 17 with bootstrap SQL for initial database setup       |
| [Home Assistant](services/home-assistant/) | Home automation platform with Prometheus metrics                |
| [Frigate](services/frigate/)               | NVR with ML object detection — monitors 4 cameras via RTSP      |
| [Mosquitto](services/mosquito/)            | MQTT broker connecting Frigate events to Home Assistant         |
| [Pi-hole](services/pihole/)                | DNS-level ad blocker with custom local DNS entries              |
| [Headlamp](services/headlamp/)             | Kubernetes web dashboard                                        |
| [Authentik](services/authentik/)           | SSO / OIDC identity provider (WIP)                              |

## Project Layout

```
homelab/
├── helmfile.yaml                 # All releases, versions, and repos in one file
├── Makefile                      # Cluster lifecycle (up / down / sync)
├── scripts/
│   ├── setup.sh                  # Namespace creation and post-install bootstrap
│   └── update-charts.sh          # Detects available Helm chart updates
├── terraform/                    # Authentik OAuth2 provider config (WIP)
├── services/                     # Per-service Helm values and config options
│   ├── prometheus/               # Each service gets its own directory
│   └── ...                       # 
└── notes/                        # Hardware planning, Talos setup, scratch notes
```

## Roadmap

- **Local DNS** — Pi-hole resolving `*.home` hostnames so services are reachable by name instead of IP
- **Multi-node HA** — Expand to 3 nodes with Longhorn replication and pod anti-affinity
- **Authentik SSO** — OIDC integration across Grafana, Headlamp, and other services
- **Backups** — Velero for cluster resource and PV snapshots
