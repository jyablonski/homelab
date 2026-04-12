# Registry

Dedicated OCI image registry for homelab-owned application images. This is shared infrastructure and is intentionally separate from the reusable `charts/workload` application chart.

## Why a dedicated chart

- The registry is cluster infrastructure, not an application workload.
- It needs persistent storage for image layers.
- It is the stable image source that lets multi-node K3s clusters pull the same app images from any node.

## Helmfile wiring

This repo wires the registry in `helmfile.yaml` as a dedicated release:

```yaml
- name: registry
  namespace: registry
  createNamespace: true
  chart: twuni/docker-registry
  version: 3.0.0
  values:
    - services/registry/values.yaml
```

## K3s node configuration

Each K3s node that may schedule workloads must be able to pull from the registry. Copy [registries.yaml.example](./registries.yaml.example) to `/etc/rancher/k3s/registries.yaml` on every node, then restart K3s.

The repo pins the registry `LoadBalancer` service to `192.168.76.250`, which is inside the MetalLB pool defined in [services/metallb/ip-pool.yaml](../metallb/ip-pool.yaml).

For the example file to work, `registry.home` needs to resolve to `192.168.76.250` from every node and from the machine doing `docker push`. In this homelab, Pi-hole or another LAN DNS entry is the cleanest option. Until then, a single `/etc/hosts` entry is enough:

```text
192.168.76.250 registry.home
```

Because this registry is HTTP-only in v1, both the local Docker daemon and K3s/containerd need to trust `registry.home:5000` as an insecure registry.

## Image naming convention

Use the app directory name as the image name:

- `apps/lotus-api` -> `registry.home:5000/homelab/lotus-api:<tag>`
- `apps/lotus-frontend` -> `registry.home:5000/homelab/lotus-frontend:<tag>`

Example build and push flow:

```bash
make image-build-push SERVICE=lotus-api TAG=dev
```

To see the image name without building:

```bash
make image-ref SERVICE=lotus-api TAG=dev
```

## First-pass scope

- Longhorn-backed filesystem storage
- `LoadBalancer` service on port `5000`
- Prometheus scraping via `ServiceMonitor`
- No auth yet
- No TLS yet

## Suggested next hardening steps

- Add LAN DNS for `registry.home`
- Add basic auth once the workflow is stable
- Move from `:dev` tags to git SHA or timestamp tags
- Add TLS once you want stricter node/client trust

## Future image retention

This registry setup does not yet enforce image retention. Docker Distribution does not provide a simple built-in policy like "keep only the newest 2 tags per repository".

The intended future approach is:

- use immutable, sortable tags for each deployment, such as git SHA or timestamp-based tags
- keep the most recent deployed image plus one previous image per repository
- delete older manifests by digest through the registry API
- run garbage collection afterward to reclaim unreferenced blobs

Two important notes:

- deleting a tag or manifest does not immediately reclaim disk space; garbage collection is what actually frees unreferenced layers
- reclaimed space may be smaller than expected because image layers are shared across versions

This is intentionally not implemented yet. When it is added, it should live in deployment or maintenance tooling, not in the application workload chart.
