# Homelab

Personal homelab infrastructure running on K3s with automated deployment via Helmfile.

## Overview

This project provisions a single-node Kubernetes cluster with a complete observability stack, persistent storage, and home automation. Everything is declaratively managed through Helm charts with pinned versions for reproducible deployments.

### What's Included

| Component       | Purpose                                                 |
| --------------- | ------------------------------------------------------- |
| MetalLB         | Bare-metal load balancer - assigns LAN IPs to services  |
| Traefik         | Ingress controller - routes HTTP traffic                |
| Longhorn        | Distributed block storage - provides persistent volumes |
| Prometheus      | Metrics collection and alerting                         |
| Grafana         | Visualization for metrics and logs                      |
| Loki + Promtail | Log aggregation and querying                            |
| Headlamp        | Kubernetes dashboard UI                                 |
| PostgreSQL      | Relational database                                     |
| Home Assistant  | Home automation platform                                |
| Authentik       | Identity provider / SSO (WIP)                           |

## Quick Start

### Prerequisites

- Ubuntu/Debian-based Linux system
- `curl`, `kubectl`, `helm`, `helmfile` installed
- Sufficient disk space (the cluster needs ~15% free to avoid disk pressure)

### Quick Start

```bash
make up
```

This will:

1. Install K3s (with built-in Traefik disabled)
2. Create required namespaces
3. Deploy all services via Helmfile

For teardown:

```bash
make down
```

This will uninstall all services, remove persistent volumes, and uninstall K3s.

### Access Services

After deployment, services are accessible via MetalLB-assigned IPs. Check assigned IPs:

```bash
kubectl get svc -A | grep LoadBalancer
```

Default services:

| Service        | Default Port | Credentials                        |
| -------------- | ------------ | ---------------------------------- |
| Grafana        | 3000         | admin / admin                      |
| Prometheus     | 9090         | -                                  |
| Headlamp       | 8085         | [Generate token](#headlamp-access) |
| Home Assistant | 8123         | Setup on first visit               |
| Longhorn UI    | 30085        | -                                  |
| PostgreSQL     | 5432         | jacob / password                   |

#### Headlamp Access

Headlamp requires a service account token that has to be generated dynamically (insecure auth is not supported yet).

```bash
kubectl create token headlamp -n kube-system --duration=8760h
```

Paste the token into the Headlamp login screen. Your browser will remember it.

## Project Structure

```
homelab/
├── helmfile.yaml              # Main deployment manifest - all releases with pinned versions
├── Makefile                   # Cluster lifecycle commands (up/down)
├── scripts/
│   └── setup.sh               # Post-install setup script
└── services/
    ├── authentik/
    │   └── values.yaml
    ├── loki/
    │   └── values.yaml
    ├── longhorn/
    │   └── values.yaml
    ├── prometheus/
    │   └── values.yaml        # Includes Grafana config
    ├── etc...                 # Other service charts and values
```

## How It Works

### Networking

```
Internet/LAN Request
        ↓
    MetalLB (assigns external IP from pool, e.g., 192.168.76.240-250)
        ↓
    Service (LoadBalancer type)
        ↓
    Pod
```

MetalLB assigns IPs from a configured pool to `LoadBalancer` services. Each service gets a dedicated IP accessible from your LAN.

### Storage

Longhorn provides persistent volumes backed by local disk. Volumes are stored at `/var/lib/longhorn/` and managed through Kubernetes PVCs.

For single-node clusters, replica count is set to 1 (no redundancy). Data persists across pod restarts but not node failures.

### Observability

```
Pods write to stdout/stderr
        ↓
Container runtime writes to /var/log/pods/
        ↓
Promtail (DaemonSet) tails logs, adds labels
        ↓
Loki stores and indexes logs
        ↓
Grafana queries both Prometheus (metrics) and Loki (logs)
```

- Prometheus scrapes metrics from pods, nodes, and Kubernetes components
- Promtail collects logs from all pods on each node
- Loki stores logs with 7-day retention
- Grafana provides dashboards for node metrics as well as logs exploration

### Chart Version Pinning

All Helm charts are pinned to specific versions in `helmfile.yaml` for reproducible deployments. To upgrade a chart:

1. Check available versions: `helm search repo <chart> --versions`
2. Update the `version:` field in `helmfile.yaml`
3. Run `helmfile sync`

## Future State

### Pi-hole

Local DNS resolution to enable services to be accessed via hostnames instead of IPs or port numbers. Example:

- `http://grafana.home`
- `http://homeassistant.home`

### Multi-Node Cluster

Expand to 3+ nodes for high availability:

- Longhorn replication across nodes (bump `defaultReplicaCount` to 3)
- Pod scheduling across nodes for redundancy
- Proper ingress with DNS-based routing via Traefik

### Authentik SSO

Centralized authentication for all services:

- OIDC integration with Grafana, Headlamp, etc.
- Single sign-on across the homelab
- User management and access control

### Ingress + DNS

Replace direct LoadBalancer IPs with hostname-based routing:

- Local DNS (Pi-hole or router) pointing `*.home.local` to Traefik IP
- Traefik ingress rules routing by hostname
- Optional: TLS with self-signed certs or Let's Encrypt
