# Registry Notes

This homelab uses a local OCI registry for application images that are built from `apps/<app>/Dockerfile` and deployed through `charts/workload`. The registry is managed as shared infrastructure through `services/registry/values.yaml`, not through the workload chart.

## Current Setup

The registry runs as a single `twuni/docker-registry` release in the `registry` namespace, stores image layers on a Longhorn-backed volume, listens on port `5000`, and is exposed through MetalLB at `192.168.76.250`. The canonical name for that endpoint is `registry.home`, so image names look like `registry.home:5000/homelab/<service>:<tag>`.

The address is pinned because the hostname is part of the image reference, and changing IPs would force repeated local DNS or host-file changes. The pinned IP lives inside the MetalLB pool defined in `services/metallb/ip-pool.yaml`.

A registry is needed because the cluster cannot pull images directly from your local machine, and pushing to Docker Hub or another public registry is too slow and adds friction. The local registry provides a stable, fast image source that can be used for development and testing without needing to set up a more complex multi-node registry or add extra steps to the build and deploy flow.

## Host-level Configuration

Two host-level files are required to make push and pull work reliably.

### Docker

Docker needs `/etc/docker/daemon.json` so pushes do not default to HTTPS:

```json
{
  "insecure-registries": ["registry.home:5000"]
}
```

Restart Docker after updating:

```bash
sudo systemctl restart docker
```

### K3s

K3s needs `/etc/rancher/k3s/registries.yaml` so containerd will pull from the same HTTP registry instead of trying HTTPS and failing with `server gave HTTP response to HTTPS client`:

```yaml
mirrors:
  "registry.home:5000":
    endpoint:
      - "http://registry.home:5000"
```

Restart K3s after updating:

```bash
sudo systemctl restart k3s
```

### DNS / Hostname Resolution

Before Pi-hole or another local DNS source is in place, `registry.home` still needs to resolve on the machine doing `docker push` and on any node pulling the image. The temporary workaround is a single `/etc/hosts` entry:

```
192.168.76.250 registry.home
```

This is a stopgap. The intended long-term state is for Pi-hole to resolve `registry.home` to the pinned MetalLB IP so local host files are no longer needed.

> Pi-hole can't be configured long term until the full 3-node cluster is setup and running. It requires you to go into router settings and reserve fixed IPs for the nodes, then add those IPs to Pi-hole's DHCP configuration. Figure this out later once the full cluster is ready for configuration.

## Bring-up Flow

Deploy the registry and confirm MetalLB assigned the pinned address:

```bash
helmfile sync --selector name=registry
kubectl -n registry get svc registry-docker-registry -o wide
```

The `EXTERNAL-IP` should be `192.168.76.250`. Smoke test:

```bash
curl http://registry.home:5000/v2/
```

Expected response is `{}`.

## Application Image Workflow

In-house applications in `apps/` follow a simple pattern. An app directory owns its source code, its `Dockerfile`, and its `values.yaml`. The image name matches the app directory name, so `apps/workload-chart-example` maps to `registry.home:5000/homelab/workload-chart-example:dev`.

- See example in `apps/workload-chart-example/` for a sample app directory.
- For services that use a third-party Helm chart in `helmfile.yaml`, the workload chart and local Dockerfile are not needed because the chart pulls an image from a public registry. The workload chart is only for in-house applications that are built and pushed to the local registry.

Build and push:

```bash
make image-build-push SERVICE=workload-chart-example TAG=dev
make image-ref SERVICE=workload-chart-example TAG=dev
```

Full deployment flow:

```bash
make image-build-push SERVICE=workload-chart-example TAG=dev
helmfile sync --selector name=workload-chart-example
kubectl -n apps rollout status deploy/workload-chart-example
```

## Troubleshooting

`lookup registry.home: no such host` on `docker push` or from Kubernetes means the hostname is not resolving. Fix with `/etc/hosts` or Pi-hole.

`server gave HTTP response to HTTPS client` means Docker or K3s is still missing its insecure-registry configuration.

`ImagePullBackOff` on a pod warrants these checks:

```bash
kubectl -n apps describe pod <pod-name> | sed -n '/Events:/,$p'
curl http://registry.home:5000/v2/homelab/workload-chart-example/tags/list
getent hosts registry.home
```

## Limitations

The current registry is not truly HA. It is a single replica, uses a filesystem volume rather than object storage, has no auth or TLS, and retention is not automated. This is acceptable for the current homelab phase because it gives a stable, working image source without adding too much complexity.

## Future State

Near-term, Pi-hole should resolve `registry.home` to `192.168.76.250`, and `/etc/rancher/k3s/registries.yaml` should exist on every node that may schedule workloads. At that point, developer machines can push to the same hostname that cluster nodes use for pulls, and service values no longer need to change as nodes are added.

The likely multi-node path is to keep the registry as a hardened singleton rather than forcing full HA too early. Longhorn can preserve the data and let the pod reschedule if a node goes away, which is often good enough for a homelab. If the registry becomes important enough to harden further, next steps would be TLS, authentication, immutable tags, automated retention for current-plus-previous images, and potentially a backend more appropriate for multi-replica operation. A multi-replica registry backed only by a simple shared filesystem is not automatically safe, so application workloads should become more HA before the registry itself is made more complex.

## Desired Operator Experience

`registry.home` should resolve everywhere, every node should trust and pull from the registry, every in-house app directory under `apps/` should own its code and image build, and `make image-build-push SERVICE=<name> TAG=<tag>` should work without one-off machine fixes. That keeps Helm focused on deployment, keeps build logic out of charts, and leaves a clean path from the current single-node setup to a more stable multi-node cluster later.
