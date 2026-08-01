# Talos Cluster Preparation

## Status

This repository contains the non-destructive preparation for a future three-node Talos Linux cluster. The active homelab still runs K3s, and none of the Talos Make targets install, configure, reset, or otherwise contact a node.

Talos replaces K3s with Talos-managed upstream Kubernetes. All three Beelinks are intended to run as schedulable control-plane nodes, giving etcd and the Kubernetes control plane one-node failure tolerance.

The implementation plan and cutover checklist live in `notes/ideas/talos-migration.md`.

## Repository Layout

```text
talos/
├── cluster.yaml
├── schematic.yaml
├── patches/
│   ├── common.yaml
│   └── longhorn.yaml
└── _out/                  # generated and ignored

scripts/
├── generate-talos-secrets.sh
├── generate-talos-config.sh
└── validate-talos-config.sh
```

`talos/cluster.yaml` is the tracked cluster inventory. Hardware-derived fields remain empty until the nodes can be inspected.

`talos/schematic.yaml` declares Image Factory system extensions. Longhorn requires `siderolabs/iscsi-tools` and `siderolabs/util-linux-tools`.

`talos/patches/common.yaml` allows workloads on control-plane nodes. After bootstrap, verify whether Kubernetes added `node.kubernetes.io/exclude-from-external-load-balancers` and remove it from all three nodes if it would exclude them from LoadBalancer traffic; forcing its deletion in the generated Talos 1.13 config fails when the label is absent.

`talos/patches/longhorn.yaml` exposes `/var/mnt/longhorn` to the kubelet. It is included only when `storage.longhorn.enabled` is `true`.

## Pinned Versions

The initial preparation pins:

- Talos Linux `v1.13.3`
- Kubernetes `v1.36.1`

These versions are compatible, but they must be reviewed against the current Talos support matrix before the nodes are provisioned. The generation script passes both versions explicitly so a future `talosctl` default cannot silently change the output.

Use a `talosctl` version matching the pinned Talos minor version.

## Prerequisites

Local generation requires:

- `talosctl`
- `sops`
- `yq`
- `jq`
- Access to an age private key matching a recipient in `.sops.yaml`

No Kubernetes cluster or Talos node is required to generate or statically validate machine configurations.

## Image Factory Schematic

Submit the tracked schematic to Image Factory:

```bash
curl --fail --silent --show-error \
  --data-binary @talos/schematic.yaml \
  https://factory.talos.dev/schematics
```

The response contains a content-addressed 64-character schematic ID. The current schematic resolves to `613e1592b2da41ae5e265e8789429f22e121aab91cb4deb6bc3c0b6262961245`, which is recorded as `cluster.schematicId` in `talos/cluster.yaml`.

The boot ISO and the installer image referenced by the machine configuration must use the same schematic ID and Talos version. The generation script constructs the installer reference as:

```text
factory.talos.dev/metal-installer/<schematic-id>:<talos-version>
```

Additional CPU microcode or hardware firmware extensions should be added only after the Beelink models and devices have been inspected. Changing `talos/schematic.yaml` changes its schematic ID.

## Required Hardware Inventory

Before machine configurations can be generated, fill each node entry in `talos/cluster.yaml` with:

- `address`: the DHCP-reserved node address
- `interface`: the physical interface name reported by Talos maintenance mode
- `installDiskSelector.serial` or `installDiskSelector.wwid`: a stable identifier reported for the intended system disk

Also set `cluster.apiVip` to an unused, reserved address on the same layer 2 network as all three control-plane nodes.

The generator rejects node addresses and the API VIP if they overlap the tracked MetalLB pool. DHCP reservations must also be configured on the router before applying machine configurations.

Do not infer disk identity from another Linux installation or assume every node contains identical devices. Inspect each node from Talos maintenance mode before filling these values. The generated config retains Talos's base `/dev/sda` field because `talosctl gen config` requires an install-disk value, but the per-node serial or WWID selector takes priority during installation.

## Longhorn Storage Decision

Longhorn configuration is disabled in `talos/cluster.yaml` until the physical disk layout is known. This prevents generation of a machine config that might partition the wrong device.

When a dedicated storage disk is available, configure each node with a selector based on an observed stable property such as its serial or WWID:

```yaml
storage:
  longhorn:
    enabled: true

nodes:
  - hostname: talos-1
    longhorn:
      diskSelector: disk.serial == "observed-serial"
      maxSize: -10%
      ephemeralMaxSize:
```

When Longhorn must share the Talos system disk, use `system_disk` and set an explicit `ephemeralMaxSize` so the EPHEMERAL volume does not consume the disk before the Longhorn user volume is provisioned:

```yaml
storage:
  longhorn:
    enabled: true

nodes:
  - hostname: talos-1
    longhorn:
      diskSelector: system_disk
      maxSize: -10%
      ephemeralMaxSize: 80GiB
```

These values are examples, not sizing recommendations. Choose them from the actual disk capacity and workload requirements.

When enabled, generation adds the following to every machine config:

- A kubelet bind mount for `/var/mnt/longhorn`
- An optional `VolumeConfig` limiting EPHEMERAL
- A `UserVolumeConfig` named `longhorn`

Talos applies volume provisioning only when a volume has not already been provisioned. Finalize this layout before the first installation.

The Kubernetes-side Longhorn data path and privileged namespace labels remain unchanged until the migration cutover is ready. Enabling Talos storage alone does not modify the active K3s cluster.

## Cluster Identity

The Talos secrets bundle has been created and committed as encrypted source at `talos/secrets.sops.yaml`. Its one-time creation command was:

```bash
make talos-secrets
```

The file is encrypted using the repository's SOPS creation rule. The script now refuses to overwrite it because replacing it would create a different cluster identity. Do not remove and rerun this target during config regeneration or recovery.

Back up all of the following outside the repository and outside the future cluster before provisioning:

- `talos/secrets.sops.yaml`
- The corresponding SOPS age private keys
- The generated `talosconfig`
- The generated Kubernetes administrator kubeconfig, once available

Never regenerate secrets as part of ordinary config regeneration or disaster recovery for an existing cluster.

## Generate Machine Configurations

After the schematic ID and required inventory are set:

```bash
make talos-config
```

Generation:

1. Decrypts the Talos secrets bundle into a mode-`0700` temporary directory.
2. Generates one base control-plane configuration using the pinned versions and schematic-specific installer.
3. Adds the HTTP mirror for `registry.home:5000`.
4. Creates one configuration per node with its hostname, NIC, install disk, DHCP networking, and shared API VIP.
5. Adds Longhorn volume documents only when explicitly enabled.
6. Configures `talosconfig` with all three physical node endpoints.
7. Writes credential-bearing results to the ignored, mode-`0700` `talos/_out/` directory.
8. Deletes the temporary plaintext secrets on exit.

The script refuses to write into a non-empty output directory. Remove `talos/_out/` explicitly after reviewing whether its generated credentials are still needed, then regenerate.

Generated files are:

```text
talos/_out/
├── talos-1.yaml
├── talos-2.yaml
├── talos-3.yaml
└── talosconfig
```

The machine YAML files and `talosconfig` contain credentials and must not be committed.

## Validate Machine Configurations

Validate all three generated machine configurations locally:

```bash
make talos-validate
```

This runs strict metal-platform validation through `talosctl`. Local validation may report hardware-dependent issues that require an actual node, especially around install disks and volume selectors; do not dismiss other validation errors as hardware limitations.

## Intentionally Deferred Operations

The repository does not yet automate:

- Writing an ISO to removable media
- Applying a machine configuration
- Installing or resetting Talos
- Bootstrapping etcd
- Retrieving or merging kubeconfig
- Upgrading Talos or Kubernetes
- Replacing a failed node

These operations either modify physical machines or depend on verified live addresses and disks. Add them only after the nodes are available, with explicit target selection and destructive-operation safeguards. A normal `make down` must never reset Talos nodes.

## Bootstrap Dependencies

The node addresses, Kubernetes API VIP, and `registry.home` must resolve without depending on in-cluster Pi-hole. Use router DHCP reservations and router or LAN DNS records for these bootstrap dependencies.

The Kubernetes VIP is the endpoint for `kubectl`, Helmfile, Tilt, and Terraform. Configure `talosctl` with the three physical node addresses instead of the VIP so Talos remains manageable when etcd or the Kubernetes API is unavailable.

The current registry uses HTTP. The generated machine configs explicitly use `http://registry.home:5000`. Registry TLS and authentication should be implemented later, after the initial migration is stable.

## References

- [Talos Image Factory](https://docs.siderolabs.com/talos/v1.13/learn-more/image-factory)
- [Talos production cluster guidance](https://docs.siderolabs.com/talos/v1.13/getting-started/prodnotes)
- [Talos virtual IP](https://docs.siderolabs.com/talos/v1.13/networking/vip)
- [Talos configuration validation](https://docs.siderolabs.com/talos/v1.13/reference/cli)
- [Talos disk management](https://docs.siderolabs.com/talos/v1.13/configure-your-talos-cluster/storage-and-disk-management/disk-management/common)
- [Longhorn support on Talos Linux](https://longhorn.io/docs/1.12.0/advanced-resources/os-distro-specific/talos-linux-support/)
