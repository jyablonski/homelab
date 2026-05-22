# Smart Home Setup on K3s Homelab

## Smart Home Device Protocols

Smart home devices need a shared communication protocol to be controllable by a hub like Home Assistant. The main options:

- Zigbee: mature, broad device support, mesh-based, local-only
- Z-Wave: similar to Zigbee but proprietary, smaller ecosystem, longer range
- Matter: newer standard backed by Apple/Google/Amazon, runs over Thread, WiFi, or Ethernet
- Thread: network-layer mesh protocol (not a smart home standard itself, but Matter runs on it)
- WiFi: high overhead, often cloud-dependent, avoid when possible

Devices need a protocol because they speak over radio, not IP. Something has to translate radio messages into something HA can understand. The protocol defines pairing, messaging, security, and how devices form a network.

## The Two Chosen: Zigbee + Matter-over-Thread

For a GitOps K3s homelab:

- Zigbee via Zigbee2MQTT (Z2M): workhorse protocol, broadest device support, best diagnostics, most homelab-friendly
- Matter-over-Thread via OpenThread Border Router (OTBR): forward-looking, growing device ecosystem, multi-admin support

Both protocols use the same 802.15.4 physical radio layer, but with completely different stacks on top. They can't share a single radio reliably, so two separate USB sticks are required.

## The Mesh Concept

Both Zigbee and Thread form self-organizing mesh networks. Devices on the same frequency with the same network credentials discover each other and route packets cooperatively.

Not every device routes:

- Mains-powered devices (smart plugs, bulbs, switches) act as routers, always on, forwarding traffic for others
- Battery-powered devices (sensors, buttons) are end devices, sleep most of the time, attach to one parent router, don't extend the mesh

This means the mesh gets stronger with more mains-powered devices. A good rule: at least one router per room. The coordinator/border router sits at the root, routers form the backbone, end devices hang off as leaves.

Mesh formation is gradual. Devices initially connect directly to the coordinator, then discover better routes through nearby routers over hours/days. Don't relocate routers frequently after the mesh stabilizes.

Common anti-pattern: smart bulbs behind dumb wall switches. Flipping the switch off kills a router and orphans its end-device children.

## Coordinators and Border Routers

Every protocol needs a root node that bridges the mesh to your IP network.

### Zigbee Coordinator

Always a dedicated USB stick. Examples:

- Sonoff ZBDongle-E (~$20)
- Home Assistant SkyConnect / Connect ZBT-1 (~$40)

No consumer device gives HA a usable Zigbee coordinator. Hue Bridges, Echos, and SmartThings hubs have Zigbee radios but are locked to their own ecosystems.

### Thread Border Router

Built into many consumer devices because Matter requires Thread border routers to be multi-admin and interoperable:

- Apple TV 4K (2nd gen+), HomePod mini
- Google Nest Hub (2nd gen), Nest Hub Max
- Amazon Echo (4th gen+)

Or a dedicated USB stick:

- HA SkyConnect (Thread mode)
- Dedicated OTBR-compatible sticks

For a homelab prioritizing GitOps and standardization, a USB stick + OTBR is the better fit. Config in code, full diagnostic visibility, no Apple/Google account dependencies.

## What the Devices Actually Connect To

Devices have no concept of nodes, containers, or clusters. They see only:

- A radio mesh on a specific frequency
- A network key
- Other devices in the mesh

The connection terminates at the radio. The radio lives in the USB stick. The USB stick is owned by a container running the protocol stack.
[Device] -> [Radio in USB stick] -> [Container running protocol software] -> [HA via IP]

## The Containers

Sticks do nothing without software actively driving them. The radio is just hardware; the protocol intelligence lives in the container.

### Zigbee2MQTT

- Reads/writes the Zigbee stick over its serial interface
- Translates Zigbee messages to MQTT topics
- Publishes device state to a Mosquitto broker
- HA subscribes via its MQTT integration, auto-discovers entities
- Memory: ~80-150 MB

### OpenThread Border Router

- Reads/writes the Thread stick
- Exposes the Thread network as a routable IPv6 subnet
- HA's Matter integration talks Matter over IPv6 through the border router
- Memory: ~30-80 MB

### Mosquitto (MQTT broker)

- Required by Z2M as the transport to HA
- Can run anywhere in the cluster, but reasonable to colocate with Z2M
- Memory: ~10-30 MB

### Home Assistant

- Runs anywhere in the cluster
- Talks to Mosquitto over the cluster network (for Zigbee devices)
- Talks to OTBR over IPv6 (for Thread/Matter devices)
- Memory: 500 MB - 2 GB

## Node Affinity: Why Containers Must Run on the Stick's Node

The USB stick is a physical device on one specific machine. The host OS exposes it as `/dev/serial/by-id/...`. Containers mount that path via `hostPath`.

If the container schedules onto a different node, the path either doesn't exist or points to different hardware. The container fails or talks to the wrong device.

Fix: label one node and pin the protocol containers to it.

```bash
kubectl label node node-a smart-home=true
```

```yaml
spec:
  nodeSelector:
    smart-home: "true"
```

Use `/dev/serial/by-id/...` paths, not `/dev/ttyUSB0`. The latter changes after reboots.

## Single Pod, Not Multiple

Z2M and OTBR are exclusive consumers of their hardware device. Only one process at a time can hold the serial port open. Implications:

- `replicas: 1`, always
- `strategy: Recreate`, not RollingUpdate (default would deadlock on the device)
- No HA in the high-availability sense for the smart-home stack
- Resilience comes from PVC backups, not multiple replicas

```yaml
spec:
  replicas: 1
  strategy:
    type: Recreate
```

## Deployment Layout

On the smart-home node (pinned):

1. Z2M, 1 replica, hostPath mount of Zigbee stick, PVC for data
2. OTBR, 1 replica, hostPath mount of Thread stick, PVC for data
3. Mosquitto, 1 replica, can be colocated for simplicity

Elsewhere in the cluster:

4. Home Assistant, runs anywhere, PVC for config and database

Total smart-home-node footprint: ~200-300 MB. Plenty of headroom for other workloads on that node.

## Resilience

Single point of failure at the node level is unavoidable for mesh coordinators. Mitigations:

- Back up Z2M's data dir (Zigbee network key, device database)
- Back up OTBR's data (Thread credentials)
- Document recovery: new node, label `smart-home: true`, plug in sticks, restore PVCs, pods reschedule
- Thread supports multiple border routers on the same network for redundancy if needed; Zigbee does not

## Debugging by Layer

The clean layering makes failure isolation easy:

- Device won't pair -> radio/stick/container issue (check Z2M or OTBR logs)
- Paired but not in HA -> MQTT broker or HA integration issue
- In HA but commands fail -> command path issue (HA -> broker -> container -> device)
- Smart-home node down -> all Zigbee/Thread dead, rest of cluster fine
- HA pod down -> mesh keeps working, just no consumer until HA returns

Use the Z2M map view and OTBR topology view for mesh diagnostics. First place to look when a device gets flaky.
