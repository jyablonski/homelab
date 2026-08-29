# OCI ARM K3s Cluster Trial

This note describes a temporary trial of the homelab on an Oracle Cloud Infrastructure Ampere A1 ARM instance.

## Expected capacity

Oracle's current Always Free A1 allocation is 2 OCPUs and 12 GB of memory total. The current homelab snapshot used approximately 5.4 GiB across pod working sets, approximately 17 GiB at the node working-set level, and showed about 12 GiB available on a 32 GiB node. The full stack may therefore boot on a 12 GB instance, but it is expected to be CPU- and memory-constrained, especially while building images or during Prometheus, Longhorn, Authentik, and Dagster activity.

K3s supports ARM64. The repository still needs an ARM image-build audit before the complete stack can run there: `apps/workload-chart-example/Dockerfile` and `apps/tools/Dockerfile` currently force `GOARCH=amd64`. The workload-chart example is deployed; the tools image is built by bootstrap discovery but is not currently a Helmfile release.

## OCI instance

Create a VM.Standard.A1.Flex instance with 2 OCPUs and 12 GB RAM. Use the standard Ubuntu 24.04 LTS ARM-compatible image, enable a public IPv4 address, and start with a 100 GB boot volume. Create a VCN with internet connectivity.

Initially allow only TCP port 22 from the administrator's home IP. Keep ports 5000, 5432, 6443, and 53 private. Use SSH tunnels for Grafana and Prometheus during the trial instead of exposing management and data services publicly.

## SSH access

For an Ubuntu image, connect as `ubuntu` using the private key selected during instance creation:

```bash
chmod 600 ~/.ssh/oci-homelab
ssh -i ~/.ssh/oci-homelab ubuntu@PUBLIC_IP
```

Verify the architecture on the instance:

```bash
uname -m
```

The expected output is `aarch64`.

## Host prerequisites

Install Docker, Git, curl, CA certificates, jq, and make with the operating system package manager. Install the repository's other prerequisites using their official installers:

```text
kubectl, helm, helmfile, sops, age, terraform
```

Enable Docker and ensure the login user can use it without sudo:

```bash
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

Log in again or run `newgrp docker`, then verify all required commands before starting the cluster.

## Repository and secrets

Clone the repository into the Ubuntu user's home directory and use a temporary cloud-test branch. Copy the SOPS age key securely to the instance, outside the repository, and set `SOPS_AGE_KEY_FILE` to its path. Do not commit the key or decrypted secrets. Protect the local Terraform state created by the Authentik bootstrap.

## Cloud-specific repository considerations

The current `make up` path assumes the home LAN. Before running it on OCI, the cloud test configuration needs to address these items:

- The MetalLB pool and fixed service addresses use `192.168.76.x`, which is not an OCI VCN range.
- The registry, Traefik, Pi-hole, and Postgres services have fixed home-LAN `loadBalancerIP` values.
- The K3s config disables ServiceLB while the Helmfile installs MetalLB. A simple single-node OCI trial should use one cloud-compatible LoadBalancer approach rather than the current home-LAN MetalLB setup.
- The Makefile changes workstation DNS through NetworkManager. That should not be run on the cloud host; use `/etc/hosts`, SSH tunnels, or real DNS instead.
- The registry and ingress bootstrap helpers support environment overrides. Once the service model is adapted, the node's private address can be derived with:

```bash
export OCI_PRIVATE_IP="$(ip -4 route get 1.1.1.1 | awk '{print $7; exit}')"
export INGRESS_IP="$OCI_PRIVATE_IP"
export REGISTRY_IP="$OCI_PRIVATE_IP"
```

Do not run the existing `make up` unchanged until these networking and ARM image issues are addressed; it is expected to fail or create unusable addresses on OCI.

## Startup and verification

After the cloud-specific adjustments:

```bash
export SOPS_AGE_KEY_FILE="$HOME/.config/sops/age/keys.txt"
make up
```

Once bootstrap completes and the cluster has settled for 30–60 minutes, collect:

```bash
free -h
kubectl top nodes
kubectl top pods -A --sort-by=memory
vmstat 1 5
kubectl get events -A --sort-by=.lastTimestamp | tail -n 50
```

Use `free -h`'s `available` column as the main host-pressure signal. In `vmstat`, nonzero sustained `si` or `so` indicates active swap traffic. Check for OOM kills if memory becomes tight.

## Private access through SSH

Grafana can be exposed locally without opening public ingress:

```bash
ssh -i ~/.ssh/oci-homelab -L 3000:127.0.0.1:3000 ubuntu@PUBLIC_IP \
  'kubectl -n monitoring port-forward --address 127.0.0.1 svc/prometheus-operator-grafana 3000:80'
```

Open `http://localhost:3000`. Use the same pattern with the Prometheus service on local port 9090 when needed.

## References

- [Oracle Always Free resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm?Highlight=free)
- [OCI platform images](https://docs.oracle.com/en-us/iaas/Content/Compute/References/images.htm)
- [OCI SSH access](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/connect-to-linux-instance.htm)
- [OCI network security](https://docs.oracle.com/en-us/iaas/Content/Network/Concepts/waystosecure.htm)
- [K3s requirements](https://docs.k3s.io/installation/requirements)
