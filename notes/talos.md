Here's the updated document with the Longhorn/Image Factory section and related updates throughout:

---

## Talos

## Phase 1: Preparation (on your laptop)

### Install talosctl

```bash
# On your current Ubuntu/Arch system
curl -sL https://talos.dev/install | sh

# Verify
talosctl version --client
```

### Create the bootable USB with Longhorn extensions

Longhorn requires iSCSI tools that aren't in the stock Talos image. Use [Talos Image Factory](https://factory.talos.dev/) to create a custom image:

1. Go to https://factory.talos.dev/
2. Select your Talos version (e.g., v1.9.0)
3. Under "System Extensions," add:
   - `siderolabs/iscsi-tools`
   - `siderolabs/util-linux-tools`
4. Generate the image
5. Download the ISO
6. **Save the installer image URL** — you'll need it for future upgrades

The factory gives you an installer URL like:

```
factory.talos.dev/installer/376567988ad370138ad8b2698212367b8edcb69b5fd68c80be1f2ec7d603b4ba:v1.9.0
```

The long hash is your "schema ID" — it encodes which extensions you selected. Save this in your README.

Write the ISO to USB:

```bash
# Find your USB device
lsblk

# Write the ISO (replace /dev/sdX with your USB - be careful here)
sudo dd if=talos-metal-amd64.iso of=/dev/sdX bs=4M status=progress conv=fsync
```

### Generate cluster configuration

Before touching any Beelinks, generate your configs:

```bash
mkdir -p ~/talos && cd ~/talos

# Generate base configs
# The endpoint IP will be your control plane node (node1)
# Pick an IP you'll assign via DHCP reservation later
talosctl gen config homelab https://192.168.1.101:6443 \
  --output-dir .
```

This creates:

- `controlplane.yaml` — config for control plane node(s)
- `worker.yaml` — config for worker nodes
- `talosconfig` — client config for talosctl to authenticate

### Create your patches

Create patches for Longhorn and any other customizations:

```yaml
# patches/common.yaml
machine:
  kubelet:
    extraMounts:
      - destination: /var/lib/longhorn
        type: bind
        source: /var/lib/longhorn
        options:
          - bind
          - rshared
          - rw
  sysctls:
    vm.panic_on_oom: "0"
    vm.overcommit_memory: "1"
    kernel.panic: "10"
  nodeLabels:
    node.longhorn.io/create-default-disk: "true"
cluster:
  allowSchedulingOnControlPlanes: true
```

The `allowSchedulingOnControlPlanes: true` ensures your control plane node can also run workloads—important for a 3-node cluster where you don't want to waste 33% of capacity.

---

## Phase 2: First boot (node1 - control plane)

### Physical setup

1. Plug USB into Beelink 1
2. Plug ethernet from Beelink 1 into your managed switch
3. Connect a monitor and keyboard temporarily (just for first boot)
4. Power on

### Boot into Talos

1. Enter BIOS (usually F2 or DEL on boot)
2. Set boot order to USB first, or use boot menu (F7 or F12)
3. Save and exit

Talos will boot into a maintenance mode. You'll see a console screen showing:

```
Talos Linux v1.9.0
Platform: metal

This machine is not configured.

Network:
  eth0: 192.168.1.47 (DHCP assigned)

To configure this machine, run:
  talosctl apply-config --insecure --nodes 192.168.1.47 --file <config>
```

**Important:** Note the IP address shown. This is the temporary DHCP IP.

### Apply configuration from your laptop

Back on your laptop (connected to the same network):

```bash
cd ~/talos

# Apply the control plane config to node1 with patches
# Use the IP shown on the Beelink's console
talosctl apply-config --insecure \
  --nodes 192.168.1.47 \
  --file controlplane.yaml \
  --config-patch @patches/common.yaml
```

The `--insecure` flag is needed because the node doesn't have certificates yet.

### What happens next

The Beelink will:

1. Write the config to disk
2. Partition and format the disk (this wipes everything)
3. Install Talos to the internal drive
4. Reboot automatically
5. Come back up running Talos from the internal drive

**You can remove the USB now** — it's no longer needed for this node.

---

## Phase 3: Bootstrap the cluster

After node1 reboots, it's running Talos but Kubernetes isn't started yet. You need to bootstrap it:

```bash
# Set up your talosctl to talk to this cluster
export TALOSCONFIG=~/talos/talosconfig

# Bootstrap etcd and Kubernetes on node1
# Use the SAME IP (it might have changed after reboot if you haven't set DHCP reservation)
talosctl bootstrap --nodes 192.168.1.47
```

This takes 2-3 minutes. Watch progress with:

```bash
# Stream logs from the node
talosctl dmesg --nodes 192.168.1.47 --follow

# Or check service status
talosctl services --nodes 192.168.1.47
```

You want to see `etcd`, `kubelet`, `apid` all showing as "Running".

### Get your kubeconfig

```bash
# Pull the admin kubeconfig
talosctl kubeconfig --nodes 192.168.1.47 -f ~/.kube/config

# Verify
kubectl get nodes
```

You should see:

```
NAME    STATUS   ROLES           AGE   VERSION
node1   Ready    control-plane   1m    v1.32.0
```

---

## Phase 4: Add worker nodes

### Boot node2

1. Move USB to Beelink 2
2. Boot from USB (same BIOS process)
3. Note the IP shown on console (e.g., `192.168.1.48`)

### Apply worker config

```bash
talosctl apply-config --insecure \
  --nodes 192.168.1.48 \
  --file worker.yaml \
  --config-patch @patches/common.yaml
```

Node2 will install and reboot. After a minute or two:

```bash
kubectl get nodes
```

```
NAME    STATUS   ROLES           AGE   VERSION
node1   Ready    control-plane   5m    v1.32.0
node2   Ready    <none>          1m    v1.32.0
```

### Repeat for node3

Same process — boot from USB, note IP, apply worker.yaml with patches.

---

## Phase 5: Lock in your network config

Right now your nodes have DHCP addresses that could change. Fix this:

### Option A: DHCP reservations (simpler)

The purpose here is to give the 3 Beelinks static IPs via your router's DHCP server.

1. Log into your router's admin panel
2. Find DHCP settings / address reservation
3. Add reservations mapping each Beelink's MAC address to a static IP:
   - `node1 MAC` → `192.168.1.101`
   - `node2 MAC` → `192.168.1.102`
   - `node3 MAC` → `192.168.1.103`
4. Reboot each node to pick up new IPs

---

## Phase 6: Verify everything

```bash
# Check all nodes
kubectl get nodes -o wide

# Check Talos services on each node
talosctl services --nodes 192.168.1.101,192.168.1.102,192.168.1.103

# Check cluster health
talosctl health --nodes 192.168.1.101

# Verify iSCSI extensions are loaded (required for Longhorn)
talosctl get extensions --nodes 192.168.1.101
```

Expected output from health check:

```
discovered nodes: ["192.168.1.101" "192.168.1.102" "192.168.1.103"]
service "etcd" to be "Running": OK
service "kubelet" to be "Running": OK
service "apid" to be "Running": OK
...
all checks passed!
```

---

## Phase 7: Install Longhorn via Helmfile

Now that Talos is configured with the iSCSI extensions and kubelet mounts, install Longhorn.

In your `services/longhorn/values.yaml`:

```yaml
defaultSettings:
  defaultDataPath: /var/lib/longhorn
  defaultReplicaCount: 3
  createDefaultDiskLabeledNodes: true

persistence:
  defaultClass: true
  defaultClassReplicaCount: 3
```

Then:

```bash
helmfile sync
```

Verify:

```bash
kubectl get pods -n longhorn-system
kubectl get storageclass
```

You should see a `longhorn` storage class set as default.

---

## Summary of the physical process

| Step | What you're doing                                        |
| ---- | -------------------------------------------------------- |
| 1    | Create custom ISO with extensions via Image Factory      |
| 2    | Write ISO to USB                                         |
| 3    | Generate configs + patches on laptop                     |
| 4    | Plug USB + monitor + keyboard into Beelink 1             |
| 5    | Boot, note IP, apply controlplane.yaml + patches         |
| 6    | Remove USB after reboot, disconnect monitor/keyboard     |
| 7    | Bootstrap cluster from laptop                            |
| 8    | Move USB to Beelink 2, boot, apply worker.yaml + patches |
| 9    | Move USB to Beelink 3, boot, apply worker.yaml + patches |
| 10   | Set DHCP reservations                                    |
| 11   | Run helmfile sync to install Longhorn + services         |
| 12   | Done — manage everything via talosctl and kubectl        |

---

## Directory structure

```
~/talos/
├── controlplane.yaml       # generated, gitignored
├── worker.yaml             # generated, gitignored
├── talosconfig             # generated, gitignored
├── secrets.yaml            # generated, gitignored
├── patches/
│   └── common.yaml         # your customizations, committed
├── .gitignore
├── Makefile
└── README.md               # include your Image Factory schema ID here
```

Your `.gitignore`:

```
controlplane.yaml
worker.yaml
talosconfig
secrets.yaml
_out/
```

---

## Patches in Git

### Why patches go in Git

Patches represent your decisions—the customizations you made on top of Talos defaults:

```yaml
# patches/common.yaml
machine:
  kubelet:
    extraMounts:
      - destination: /var/lib/longhorn
        type: bind
        source: /var/lib/longhorn
        options: [bind, rshared, rw]
cluster:
  allowSchedulingOnControlPlanes: true
```

Six months later, you can look at this and immediately understand what you customized.

### Why base configs stay out of Git

When you run `talosctl gen config`, it generates `controlplane.yaml` and `worker.yaml` containing:

- Talos defaults (boilerplate you didn't choose)
- Secrets (CA certs, private keys, bootstrap tokens)

These files are output, not input. There's nothing in them that documents your intent—they're just generated artifacts, and they contain credentials that would let anyone control your cluster.

### The mental model

| File                | What it is                   | In Git? |
| ------------------- | ---------------------------- | ------- |
| `patches/*.yaml`    | Your decisions               | ✓ Yes   |
| `controlplane.yaml` | Generated defaults + secrets | ✗ No    |
| `worker.yaml`       | Generated defaults + secrets | ✗ No    |
| `talosconfig`       | Client credentials           | ✗ No    |

It's the same pattern as Helm: you commit your `values.yaml` overrides but not the rendered manifests. The values are your intent; the output is derived.

### Storing secrets

Store `talosconfig` and `secrets.yaml` in a password manager (1Password, Bitwarden) or encrypted backup. You'll need these to authenticate to the cluster from a new machine or regenerate configs.

### Regenerating from scratch

If you ever need to rebuild, you generate fresh base configs and apply your patches:

```bash
# Generate new secrets + base configs
talosctl gen secrets -o secrets.yaml
talosctl gen config homelab https://192.168.1.101:6443 \
  --with-secrets secrets.yaml \
  --output-dir _out

# Apply with your patches
talosctl apply-config --nodes 192.168.1.101 \
  --file _out/controlplane.yaml \
  --config-patch @patches/common.yaml
```

Your patches survive because they're versioned. The generated files are disposable.

### Applying patches to running nodes

To apply a new patch to an already-running cluster:

```bash
talosctl patch machineconfig \
  --nodes 192.168.1.101 \
  --patch @patches/common.yaml
```

---

## Updating Talos

### How updates work

Talos uses an A/B partition scheme. The OS is immutable—there's no package manager modifying files. Instead:

1. Current Talos runs from partition A
2. New Talos image is written to partition B
3. Node reboots into partition B
4. If it fails, rollback to partition A

The "image" is a squashfs filesystem containing the entire OS. You're swapping one immutable artifact for another.

### What happens to workloads

When a node upgrades:

1. Node is cordoned (no new pods scheduled)
2. Node is drained (pods evicted, rescheduled to other nodes)
3. New Talos image written to disk
4. Node reboots (~2-3 minutes)
5. Node rejoins cluster and is uncordoned

**Longhorn volumes** stay safe because data lives on disk, not in memory. With replication factor 3, the volume remains accessible (degraded to 2 replicas) while one node reboots. When the node returns, Longhorn rebuilds automatically.

**Key rule:** Always wait for Longhorn to report healthy before upgrading the next node.

### Using your custom Image Factory image

Because you have extensions (iscsi-tools, util-linux-tools), use your custom image URL for upgrades—not the stock image:

```bash
# Stock image (won't have your extensions):
# ghcr.io/siderolabs/installer:v1.9.1

# Your custom image (includes extensions):
factory.talos.dev/installer/YOUR_SCHEMA_ID:v1.9.1
```

The schema ID stays the same across versions—just change the version tag at the end.

### Manual upgrade commands

```bash
# Check current version
talosctl version --nodes 192.168.1.101

# Upgrade single node with your custom image
SCHEMA_ID="376567988ad370138ad8b2698212367b8edcb69b5fd68c80be1f2ec7d603b4ba"
talosctl upgrade --nodes 192.168.1.101 \
  --image factory.talos.dev/installer/${SCHEMA_ID}:v1.9.1

# Wait for health
talosctl health --nodes 192.168.1.101

# Rollback if needed
talosctl rollback --nodes 192.168.1.101
```

### Upgrading Kubernetes (separate from Talos)

Talos OS and Kubernetes versions are independent:

```bash
talosctl upgrade-k8s --nodes 192.168.1.101 --to 1.32.0
```

### Rolling upgrade script

```bash
#!/bin/bash
set -e

NODES=("192.168.1.101" "192.168.1.102" "192.168.1.103")
VERSION="v1.9.1"
SCHEMA_ID="376567988ad370138ad8b2698212367b8edcb69b5fd68c80be1f2ec7d603b4ba"
IMAGE="factory.talos.dev/installer/${SCHEMA_ID}:${VERSION}"

for node in "${NODES[@]}"; do
  echo "=== Upgrading ${node} ==="

  talosctl upgrade --nodes "$node" --image "$IMAGE" --wait

  echo "Waiting for node to be Ready..."
  kubectl wait --for=condition=Ready node/${node} --timeout=5m

  echo "Waiting for Longhorn volumes to be healthy..."
  until kubectl get volumes.longhorn.io -n longhorn-system -o json | \
    jq -e '.items | all(.status.robustness == "healthy")' > /dev/null 2>&1; do
    sleep 10
  done

  echo "${node} complete"
done

echo "All nodes upgraded"
```

### Version check script

Rather than fully automated upgrades, check for updates and upgrade manually when ready:

```bash
#!/bin/bash
CURRENT=$(talosctl version --nodes 192.168.1.101 -o json | jq -r '.version.tag')
LATEST=$(curl -s https://api.github.com/repos/siderolabs/talos/releases/latest | jq -r '.tag_name')

if [[ "$CURRENT" != "$LATEST" ]]; then
  echo "Talos update available: ${CURRENT} -> ${LATEST}"
  # Send notification (ntfy, discord, email, etc.)
fi
```

This lets you read release notes before upgrading—Talos updates occasionally require config changes.

### Adding new extensions later

If you need to add more extensions:

1. Go back to Image Factory
2. Select new Talos version + all extensions (existing + new)
3. Get a new schema ID
4. Update your README with the new schema ID
5. Use the new image URL for upgrades

---

## Longhorn on Talos summary

| Requirement                  | How to satisfy                           |
| ---------------------------- | ---------------------------------------- |
| iSCSI tools                  | System extension via Image Factory       |
| nsenter/blkid tools          | `util-linux-tools` extension             |
| `/var/lib/longhorn` mount    | `machine.kubelet.extraMounts` in patch   |
| Default disk creation        | Node label in patch                      |
| Control plane runs workloads | `cluster.allowSchedulingOnControlPlanes` |
