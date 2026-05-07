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

`make up` bootstraps persistent local host mappings for the pinned homelab endpoints:

- `registry.home` -> `192.168.76.250`
- `apps.home` -> `192.168.76.245`

Those `/etc/hosts` entries stay in place across repeated `make down` / `make up` cycles. The IPs stay stable because both the registry and Traefik are pinned inside the MetalLB pool.

`make up` also flips this workstation to the in-cluster Pi-hole automatically after Pi-hole is healthy, and `make down` flips it back to normal DHCP-provided DNS before teardown.

If you need to toggle that behavior manually on this machine, use:

```bash
make pihole-dns-enable
make pihole-dns-disable
make pihole-dns-status
```

That points this machine's active NetworkManager connection at the cluster Pi-hole DNS service without changing the rest of the LAN. This enables all services to be accessible by their `.home` hostnames without additional configuration on this machine.

## Secrets

Sensitive Helm values live in encrypted `secrets.sops.yaml` files next to each service's `values.yaml`.

When Helmfile syncs, it decrypts and merges any `secrets.sops.yaml` files it finds into the release values. This keeps secrets out of plaintext Git history while still allowing them to be managed alongside regular config.

To create or edit a sops secrets file, run:

```bash
sops services/<service>/secrets.sops.yaml
```

To view decrypted contents:

```bash
sops -d services/<service>/secrets.sops.yaml
```

Add new secret files to the release's `secrets:` list in `helmfile.yaml` so Helmfile decrypts and merges them during `helmfile sync`.

## Network Flow

Example request flow. Most browser-facing services resolve through Pi-hole and route through Traefik, while a few direct endpoints like the local registry still bypass Traefik.

- Pi-hole handles all DNS for the `.home` domain, resolving to cluster services or forwarding to upstream DNS as needed.
- Traefik routes incoming HTTP requests by hostname to the appropriate ClusterIP services.

```mermaid
flowchart LR
  subgraph Client["Workstation"]
    browser["Browser / curl"]
    docker["Docker build / push"]
  end

  subgraph Cluster["K3s Cluster"]
    pihole["Pi-hole DNS<br/>192.168.76.246:53"]
    traefik["Traefik ingress<br/>192.168.76.245:80/443"]
    app["workload-chart-example<br/>ClusterIP service"]
    grafana["Grafana<br/>ClusterIP service"]
    prometheus["Prometheus<br/>ClusterIP service"]
    homeassistant["Home Assistant<br/>ClusterIP service"]
    registry["Registry<br/>192.168.76.250:5000"]
  end

  browser -. "DNS lookup for *.home" .-> pihole
  pihole -. "apps.home, grafana.home,<br/>prometheus.home, homeassistant.home, ..." .-> browser

  browser -->|"HTTP Host: apps.home,<br/>grafana.home, prometheus.home, ..."| traefik
  traefik --> app
  traefik --> grafana
  traefik --> prometheus
  traefik --> homeassistant

  docker -. "DNS lookup for registry.home" .-> pihole
  pihole -. "registry.home -> 192.168.76.250" .-> docker
  docker -->|"push/pull registry.home:5000"| registry
```

### Default Access

| Service        | Access                                          | Credentials                                                     |
| -------------- | ----------------------------------------------- | --------------------------------------------------------------- |
| Grafana        | [grafana.home](http://grafana.home)             | admin / admin                                                   |
| Prometheus     | [prometheus.home](http://prometheus.home)       | —                                                               |
| Home Assistant | [homeassistant.home](http://homeassistant.home) | Setup on first visit                                            |
| Headlamp       | [headlamp.home](http://headlamp.home)           | `kubectl create token headlamp -n kube-system --duration=8760h` |
| Longhorn UI    | [longhorn.home](http://longhorn.home)           | —                                                               |
| Pi-hole        | [pihole.home/admin/](http://pihole.home/admin/) | admin / `pihole`                                                |
| Apps           | [apps.home](http://apps.home)                   | —                                                               |
| PostgreSQL     | `192.168.76.243:5432` / in-cluster service      | SOPS-managed postgres credentials                               |

## Services

### Deployed by Helmfile

| Service                                                | Description                                                    |
| ------------------------------------------------------ | -------------------------------------------------------------- |
| [MetalLB](services/metallb/)                           | Manages static LAN IPs for Kubernetes services                 |
| [Traefik](services/traefik/)                           | Ingress controller for browser-facing services                 |
| [Longhorn](services/longhorn/)                         | Persistent storage for Kubernetes workloads                    |
| [Prometheus](services/prometheus/)                     | Collects CPU, memory, and other metrics from Kubernetes        |
| [Grafana](services/prometheus/)                        | Dashboards for metrics and logs, bundled with Prometheus chart |
| [Loki](services/loki/)                                 | Aggregates and stores logs from Kubernetes workloads           |
| [Promtail](services/promtail/)                         | DaemonSet that ships pod logs to Loki                          |
| [PostgreSQL](services/postgres/)                       | Shared database for homelab-owned applications                 |
| [Registry](services/registry/)                         | Local registry for Docker images built from `apps/`            |
| [Home Assistant](services/home-assistant/)             | Home automation platform                                       |
| [Pi-hole](services/pihole/)                            | DNS and `.home` records                                        |
| [Headlamp](services/headlamp/)                         | Kubernetes dashboard; optional if `kubectl` is enough          |
| [Authentik](services/authentik/)                       | SSO / OIDC identity provider (WIP)                             |
| [API](apps/api/)                                       | REST API app for custom workloads                              |
| [Django](apps/django/)                                 | Database migration tool and admin interface                    |
| [Workload Chart Example](apps/workload-chart-example/) | Deployed reference app using the workload chart                |

### Prepared / Not Deployed

| Service                            | Status                                                   |
| ---------------------------------- | -------------------------------------------------------- |
| [Frigate](services/frigate/)       | Values and secrets are prepared; no Helmfile release yet |
| [Mosquitto](services/mosquitto/)   | Values are prepared; no Helmfile release yet             |
| [Keycloak](services/keycloak/)     | Values and secrets exist; no Helmfile release yet        |
| [go-cron-test](apps/go-cron-test/) | Standalone CronJob example used for validation only      |

## Project Layout

```
homelab/
├── helmfile.yaml                 # All releases, versions, and repos in one file
├── Makefile                      # Cluster lifecycle (up / down / sync)
├── charts/                       # Reusable local Helm charts shared across apps
│   └── workload/                 # Golden path chart for custom `apps/` workloads
├── scripts/
│   ├── setup.sh                  # Namespace creation and post-install bootstrap
│   └── ...
├── terraform/                    # Authentik OAuth2 provider config (WIP)
├── services/                     # Deployed and prepared third-party service config
│   ├── prometheus/               # Each service gets values.yaml and optional sops secrets
│   └── ...
├── apps/                         # Custom, in-house workloads deployed to the cluster
│   ├── api/
│   ├── workload-chart-example/
│   └── ...
└── notes/                        # Reference notes
```
