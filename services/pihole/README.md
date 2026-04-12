# Pi-hole

Pi-hole is staged here as a workstation-only DNS server for the current homelab phase. It is not meant to become the whole-LAN resolver yet.

## Current design

- Pi-hole DNS is exposed through MetalLB at `192.168.76.246`
- Pi-hole returns `*.home` to Traefik at `192.168.76.245`
- Pi-hole returns `registry.home` directly to `192.168.76.250`
- Pi-hole's web UI is exposed through Traefik at `http://pihole.home/admin/`

That gives this repo a clean path to the following urls without changing the router yet.

- `apps.home`
- `grafana.home`
- `headlamp.home`
- `homeassistant.home`
- `longhorn.home`
- `prometheus.home`
- `pihole.home/admin/`

## Enable on This Workstation

This repo includes a NetworkManager helper for this machine only. `make up` enables it automatically after Pi-hole is ready, and `make down` disables it before cluster teardown.

```bash
make pihole-dns-enable
make pihole-dns-disable
make pihole-dns-status
```

That switches the active NetworkManager connection to use Pi-hole as its IPv4 DNS server.

- This means all internet access works as normal, but `.home` requests resolve to the cluster instead of the public internet.

## Disable Before Cluster Teardown

Because the cluster is not expected to run 24/7 yet, disable the workstation override before `make down` if you still need working DNS while the cluster is offline:

```bash
make pihole-dns-disable
```

Later, once the homelab is stable, the same `.home` records can move to Pi-hole for the full LAN by pointing the router DHCP DNS setting at the Pi-hole IP instead of changing this workstation alone.
