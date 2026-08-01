# Talos Migration Implementation Plan

## Goal

Migrate the homelab from its current single-node K3s lifecycle to a three-node, highly available Talos Linux Kubernetes cluster while preserving the existing Helmfile deployment model, MetalLB addresses, Traefik ingress, Longhorn storage, Pi-hole DNS, local registry, applications, and encrypted secrets.

Talos replaces K3s; K3s does not run inside Talos.

## Assumptions

- All three Beelink nodes run both control-plane and workload roles.
- A Kubernetes API virtual IP provides a stable control-plane endpoint.
- Talos uses its default Flannel CNI and kube-proxy initially. A Cilium migration is separate work.
- Helmfile remains the source of truth for workloads and services.
- Existing service IPs remain:
  - Postgres: `192.168.76.243`
  - Traefik: `192.168.76.245`
  - Pi-hole: `192.168.76.246`
  - Registry: `192.168.76.250`
  - MetalLB pool: `192.168.76.240-192.168.76.250`
- Talos node addresses and the Kubernetes API VIP are reserved outside the MetalLB pool and normal DHCP allocation.
- The first migration can retain the registry's current HTTP endpoint. TLS and authentication are follow-up hardening.
- Brief workload interruption during node failure or migration is acceptable; most stateful services remain single replicas even if storage is replicated.

## Current Behavior

The `Makefile` currently treats cluster creation and application deployment as one lifecycle:

1. Configure workstation DNS, `/etc/hosts`, Docker, and the K3s registry.
2. Install K3s using the upstream shell installer.
3. Copy the K3s kubeconfig.
4. Run `scripts/setup.sh`.
5. Deploy infrastructure with Helmfile.
6. Build and push local images.
7. Deploy applications.
8. Point the workstation at cluster Pi-hole.
9. `make down` uninstalls the cluster.

K3s-specific configuration lives in:

- `services/k3s/config.yaml`
- `services/k3s/README.md`
- `scripts/setup-registry-home.sh`

The existing Helm releases are mostly standard Kubernetes resources and should be portable. The main migration-sensitive areas are storage, privileged workloads, registry access, kubeconfig and context handling, bootstrap sequencing, DNS, and backup and restore.

## Desired Behavior

The lifecycle should be split into three layers:

1. Talos machine lifecycle:
   - Generate and validate machine configurations.
   - Install or upgrade Talos explicitly.
   - Bootstrap etcd exactly once.
   - Obtain and maintain an independent Talos kubeconfig and `talosconfig`.
2. Cluster workload lifecycle:
   - Bootstrap namespaces and infrastructure.
   - Deploy services through Helmfile.
   - Build and push application images.
   - Deploy application releases.
3. Workstation integration:
   - Configure Docker to use the registry.
   - Configure local DNS only after Pi-hole is healthy.
   - Avoid modifying Talos node configuration through workstation scripts.

Routine commands such as `make sync` should continue to operate against the Talos Kubernetes cluster. Destructive Talos resets must not be exposed through a normal `make down`.

## Likely Files and Areas Touched

Existing files:

- `Makefile`
- `README.md`
- `Tiltfile`
- `helmfile.yaml`
- `scripts/setup.sh`
- `scripts/setup-registry-home.sh`
- `scripts/setup-local-pihole-dns.sh`
- `scripts/validate-manifests.sh`
- `services/longhorn/values.yaml`
- `services/registry/values.yaml`
- `services/k3s/config.yaml`
- `services/k3s/README.md`
- `terraform/main.tf`
- `.github/workflows/validate.yaml`
- `notes/reference/talos.md`
- Service documentation containing K3s-specific instructions.

Proposed new files:

```text
talos/
├── schematic.yaml
├── patches/
│   ├── common.yaml
│   ├── controlplane.yaml
│   └── nodes/
│       ├── node-1.yaml
│       ├── node-2.yaml
│       └── node-3.yaml
└── secrets.sops.yaml

scripts/
├── generate-talos-config.sh
└── validate-talos-config.sh

services/longhorn/
└── namespace.yaml
```

Generated Talos machine configs, kubeconfig, `talosconfig`, and decrypted secrets should be ignored rather than committed.

## Implementation Plan

### 1. Complete the Hardware and Network Inventory

Before generating configuration:

1. Record each node's:
   - MAC address
   - NIC name
   - System disk model, serial, and device path
   - Optional Longhorn disk model, serial, and device path
   - Required firmware or Talos system extensions
2. Reserve three static DHCP addresses for the nodes.
3. Reserve a fourth address for the Kubernetes API VIP.
4. Verify none overlap:
   - The MetalLB pool
   - Existing static services
   - DHCP's dynamic range
   - Other LAN devices
5. Create a LAN DNS record such as `kubernetes.home` for the API VIP.
6. Decide whether Longhorn uses:
   - A dedicated SSD per node, preferred; or
   - Free space on the Talos system disk.

For a shared system disk, Talos's ephemeral partition must be capped during the initial installation so a `UserVolumeConfig` can claim the remaining space. This is difficult to retrofit safely after the disk has been allocated.

### 2. Pin the Platform Versions and Image Factory Schematic

Select exact compatible versions of:

- Talos Linux
- Kubernetes
- `talosctl`
- Image Factory schematic

Create `talos/schematic.yaml` containing the extensions required for Longhorn, at minimum:

- `siderolabs/iscsi-tools`
- `siderolabs/util-linux-tools`

Add hardware firmware extensions discovered during inventory.

Generate both the boot or installation media and the installer image from the same schematic. The machine configurations must reference that schematic-specific installer image; booting a custom ISO alone does not ensure the installed system retains the extensions.

Record the schematic ID and pinned versions in the Talos documentation.

### 3. Add Encrypted Talos Configuration Sources

Use the existing SOPS age recipients to encrypt `talos/secrets.sops.yaml`.

Store the generated Talos secrets bundle there, including the cluster PKI and bootstrap tokens needed to regenerate the same machine configurations.

Do not commit:

- Rendered control-plane YAML
- Decrypted secrets
- `talosconfig`
- Kubernetes admin kubeconfig
- Temporary generation directories

Update `.gitignore` for the generated output locations.

Back up the encrypted Talos secret bundle and administrative configs somewhere outside this repository and outside the cluster. Regenerating new secrets during recovery would create a different cluster identity.

### 4. Define the Three-Node Talos Topology

Generate all three nodes as control-plane machines and leave workload scheduling enabled.

Common configuration should include:

- Cluster name
- Kubernetes API VIP endpoint
- Cluster DNS and pod and service networks
- Selected Kubernetes version
- Schematic-specific installer image
- Stable install disk selectors
- Time servers
- Registry configuration
- Longhorn system extensions
- Longhorn volume and mount configuration

Per-node patches should include:

- Hostname
- Physical node IP and prefix
- Gateway
- Install disk selector
- Storage disk selector, if separate
- Network interface selector
- Hardware-specific configuration

Configure `talosctl` endpoints with all three physical Talos node IPs. The Kubernetes VIP is the Kubernetes API endpoint, not the Talos API endpoint.

### 5. Configure Longhorn-Compatible Talos Storage

Create a Talos `UserVolumeConfig` for Longhorn on every node and mount it consistently at:

```text
/var/mnt/longhorn
```

Expose that path through the kubelet's extra mounts.

Update `services/longhorn/values.yaml`:

- Change the Longhorn data path to `/var/mnt/longhorn`.
- Change the default replica count from `1` to `3`.
- Preserve sufficient free space and scheduling thresholds for recovery.
- Confirm disk and node scheduling settings are not tied to old K3s node names.

Add `services/longhorn/namespace.yaml` with the Pod Security labels required for Longhorn's privileged components. Apply this namespace before Helmfile installs Longhorn rather than relying on `createNamespace`.

Add the namespace manifest to repository validation.

### 6. Move Node Registry Trust into Talos Configuration

The cluster nodes must be able to pull:

```text
registry.home:5000/homelab/<app>:<tag>
```

Add a Talos registry mirror configuration that explicitly uses the HTTP registry endpoint.

Ensure `registry.home` resolves before Pi-hole is running. The preferred bootstrap dependency is a router or LAN DNS record, not an in-cluster Pi-hole record.

Refactor `scripts/setup-registry-home.sh` so it only configures the development workstation:

- Docker insecure-registry trust while HTTP is retained
- Optional workstation host resolution
- Docker restart if needed

Remove its writes to `/etc/rancher/k3s/registries.yaml` and its K3s restart logic.

A later hardening phase should add registry TLS and authentication, eliminating the insecure-registry configuration.

### 7. Separate Talos Provisioning from Workload Bootstrap

Refactor `Makefile` around explicit lifecycle operations. Suggested targets:

```text
talos-config       Generate machine configurations into an ignored directory
talos-validate     Validate generated Talos machine configurations
talos-apply        Apply configuration to explicitly selected node addresses
talos-bootstrap    Bootstrap etcd exactly once
talos-kubeconfig   Merge or export the Talos cluster kubeconfig
talos-health       Run Talos and Kubernetes health checks
bootstrap          Deploy infrastructure, images, and applications
sync               Run Helmfile against the existing cluster
```

Remove the K3s installer and K3s kubeconfig-copy behavior from `make up`.

Either redefine `make up` as a safe wrapper around `bootstrap`, or remove it in favor of the explicit commands above.

Remove the current destructive `make down` behavior. A Talos reset should require a separate, explicit per-node operation with the target node named and a confirmation step. Routine teardown should only disable workstation DNS or remove workloads, not wipe node disks.

### 8. Make Kubeconfig and Context Handling Explicit

Talos will likely create a context such as `admin@homelab`, not K3s's generic `default` context.

Update `Tiltfile` to permit the selected Talos context.

Update Terraform configuration to accept an explicit kubeconfig path and context rather than depending implicitly on whichever context is current in `~/.kube/config`.

Make shell scripts respect `KUBECONFIG` and avoid overwriting the user's primary kubeconfig unexpectedly.

Document separate handling for:

- `talosconfig`, used by `talosctl`
- Kubernetes kubeconfig, used by `kubectl`, Helmfile, Tilt, and Terraform

### 9. Adapt Workload Bootstrap Sequencing

Keep the broad structure of `scripts/setup.sh`, but make the prerequisites explicit:

1. Confirm all three Talos nodes are healthy.
2. Confirm the Kubernetes API VIP is reachable.
3. Apply required namespaces, including the privileged Longhorn namespace.
4. Deploy MetalLB and Longhorn.
5. Wait for Longhorn nodes, disks, and the default StorageClass to become ready.
6. Deploy remaining infrastructure.
7. Verify the registry LoadBalancer address and endpoint.
8. Configure workstation registry access.
9. Build and push application images.
10. Deploy applications.
11. Apply Authentik Terraform.
12. Enable workstation Pi-hole DNS only after Pi-hole and Traefik are healthy.

Do not make in-cluster Pi-hole or the in-cluster registry prerequisites for the nodes themselves to start Kubernetes.

### 10. Prepare Application Data for Migration

Before wiping or repurposing any node, inventory every PVC and decide whether its data is:

- Restored from an application-level backup
- Restored from a filesystem archive
- Regenerated
- Intentionally discarded

At minimum, create and verify off-cluster backups for:

- Postgres databases
- Home Assistant configuration
- Pi-hole configuration, if it must be preserved
- Mosquitto state, if used
- Registry data, if images cannot simply be rebuilt
- Any application-owned persistent files

Prometheus and Loki history may be treated as disposable only if explicitly accepted.

Do not copy old Longhorn replica directories into the new cluster. Restore application-level data into new Talos-backed Longhorn volumes.

Test at least the Postgres and Home Assistant restore procedures before starting the destructive cutover.

### 11. Provision the Talos Cluster

On cutover day:

1. Disable use of cluster Pi-hole on the workstation and retain a router or public DNS fallback.
2. Confirm external backups and restore tests.
3. Boot every node from the pinned Image Factory media.
4. Inspect discovered disks and network interfaces before applying configuration.
5. Apply each node's control-plane configuration.
6. Configure `talosctl` with all three physical endpoints.
7. Bootstrap etcd exactly once against one control-plane node.
8. Retrieve the Kubernetes kubeconfig.
9. Verify:
   - Three etcd members
   - Three Ready control-plane nodes
   - Kubernetes API VIP reachability
   - Extensions loaded on every node
   - Longhorn mount present on every node
   - Correct time synchronization and DNS

### 12. Deploy and Restore the Homelab

Deploy infrastructure first:

1. Required namespaces and Pod Security labels
2. MetalLB
3. Longhorn
4. Traefik
5. Pi-hole
6. Postgres
7. Registry
8. Monitoring and logging
9. Remaining services

Verify that MetalLB reclaims the existing fixed service addresses without conflicts.

Restore stateful application data before deploying applications that depend on it.

Build and push local application images only after the registry is reachable from both the workstation and every Talos node.

Then deploy application releases and apply the Authentik Terraform resources.

### 13. Perform Failure Testing Before DNS Cutover

Test one node at a time:

1. Cordon and drain or reboot the node.
2. Confirm the Kubernetes API remains reachable through the VIP.
3. Confirm etcd maintains quorum.
4. Confirm workloads reschedule.
5. Confirm Longhorn volumes remain available or enter an expected degraded state and recover.
6. Confirm registry image pulls work on the remaining nodes.
7. Return the node and wait for Longhorn replica rebuilding to finish before testing another.

Also verify:

- Every fixed LoadBalancer IP
- All `.home` routes through Traefik
- Pi-hole resolution
- Registry push and pull
- Database connectivity
- Home Assistant access
- Prometheus targets
- Grafana dashboards
- Loki log ingestion
- Application probes
- Terraform access using the intended context

Only then point the workstation or router DNS at cluster Pi-hole.

### 14. Add Backup and Disaster-Recovery Operations

Configure and document:

- Regular etcd snapshots
- Off-node and off-cluster etcd snapshot copies
- Longhorn recurring snapshots
- Longhorn backups to storage outside the Kubernetes cluster
- Scheduled Postgres logical backups
- Home Assistant backups
- Encrypted copies of Talos secrets and administrative configs

The recovery runbook must distinguish:

- Replacing one failed Talos node
- Restoring etcd after loss of quorum
- Rebuilding the entire cluster
- Restoring application data after cluster recreation

### 15. Update Validation and Documentation

Update the Kubernetes version used by:

- `Makefile`
- `.github/workflows/validate.yaml`
- `scripts/validate-manifests.sh`

Add Talos configuration generation and validation to local validation. CI should validate encrypted sources and deterministic rendering without publishing decrypted output.

Update CI path filters and sparse checkout inputs for `talos/**` and any new scripts.

Rewrite `notes/reference/talos.md` as the operational runbook, including:

- Exact supported architecture
- Network and IP table
- Hardware and disk mapping
- Configuration generation
- First bootstrap
- Joining and replacing nodes
- Upgrades
- Etcd recovery
- Longhorn recovery
- Registry trust
- DNS bootstrap
- Rollback procedure

Remove or update K3s references throughout the root README and service documentation. Delete `services/k3s/` after no active automation or documentation depends on it.

## Tests

### Static Validation

- `shellcheck` on new and modified scripts
- Prettier on Markdown and YAML
- `talosctl validate` against every generated machine configuration
- SOPS decryption smoke test without writing plaintext to the repository
- `make validate-fast`
- `make validate`
- `agentslint check`

### Kubernetes Manifest Validation

- `helmfile repos`
- `helmfile lint`
- `helmfile template`
- Kubeconform against the selected Kubernetes version
- kube-linter
- Standalone namespace and manifest validation
- Helm unit tests

### Cluster Validation

- `talosctl health`
- Three Talos nodes visible and healthy
- Three etcd members
- Three Kubernetes nodes Ready
- All three nodes schedulable
- API VIP reachable during one-node failure
- Required Talos extensions loaded
- Longhorn volume mounted on each node
- Longhorn default replica count is three
- MetalLB service addresses assigned as expected
- Registry image pull succeeds from each node
- Traefik ingress and Pi-hole DNS work
- Terraform connects using the intended kubeconfig and context

### Recovery Validation

- Reboot one node and verify control-plane continuity.
- Restore a Postgres backup into a test database.
- Restore a Home Assistant backup.
- Confirm Longhorn replica rebuilding after a node outage.
- Document and dry-run etcd recovery commands without performing a destructive restore on the live cluster.

## Risks and Edge Cases

- Talos installation wipes the selected disk. Disk selection must use stable identifiers and be reviewed on each node.
- A single-disk layout can leave no room for Longhorn unless Talos partitioning is planned before installation.
- Three control-plane nodes tolerate one control-plane failure, not two.
- Stateful services with one application replica can still experience downtime while Kubernetes reattaches storage.
- A three-replica Longhorn volume requires all three nodes to have usable storage; maintenance can temporarily leave volumes degraded.
- The registry and Pi-hole can create circular bootstrap dependencies if Talos nodes rely on them before Kubernetes is functional.
- Reusing the existing MetalLB addresses prevents old and new clusters from advertising the same IPs simultaneously.
- For parallel validation, the Talos cluster needs a temporary MetalLB pool and temporary DNS names.
- Talos's Pod Security defaults may block Longhorn and future hardware-oriented services such as Zigbee2MQTT or the OpenThread border router.
- The API VIP protects the Kubernetes endpoint, but Talos management still requires physical node endpoints.
- A Talos upgrade must use the same required system extensions and should be performed one node at a time.
- Rollback after disks have been wiped means rebuilding K3s and restoring external backups; it is not an in-place switch back.

## Non-Goals

- Migrating from Flannel to Cilium.
- Replacing Helmfile.
- Rewriting application charts that already work on standard Kubernetes.
- Adding registry TLS or authentication during the initial cutover.
- Making every stateful application zero-downtime.
- Enabling currently disabled Frigate, Zigbee2MQTT, Mosquitto, or OpenThread workloads.
- Introducing Talos Omni, Cluster API, or Talhelper unless separately selected.
- Building a complete backup platform beyond what is required for a safe migration and recovery.

## Definition of Done

- All three Beelinks run the pinned Talos and Kubernetes versions as schedulable control-plane nodes.
- Kubernetes is reachable through a stable API VIP and remains available during a one-node outage.
- Talos machine configurations are reproducible from encrypted repository sources.
- No generated machine secrets, kubeconfigs, or `talosconfig` files are committed.
- Longhorn uses Talos-supported extensions and `/var/mnt/longhorn` on every node.
- Longhorn creates three replicas for new volumes.
- Existing MetalLB, Traefik, Pi-hole, Postgres, registry, monitoring, and application workloads are deployed successfully.
- Local application images can be pushed from the workstation and pulled by every Talos node.
- Required persistent data has been restored and tested.
- Workstation DNS is switched only after the new cluster passes health and failure testing.
- K3s-specific installation, uninstall, registry, and documentation paths have been removed.
- CI and local validation cover the pinned Kubernetes version and Talos configuration.
- Etcd, Longhorn, and application backups exist outside the cluster, with documented and tested restore procedures.
- The migration and rollback runbooks contain the actual IPs, disks, versions, commands, and recovery locations selected during implementation.
