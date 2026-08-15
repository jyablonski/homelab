# Smart Home Setup on K3s Homelab

## Smart Home Device Protocols

Smart home devices need a shared communication protocol to be controllable by a hub like Home Assistant. The main options:

- Zigbee: mature, broad device support, mesh-based, local-only. Operates on 2.4 GHz using the IEEE 802.15.4 radio standard.
- Z-Wave: similar to Zigbee but proprietary, smaller ecosystem, longer range. Operates around 908 MHz in the US, avoiding the crowded 2.4 GHz band shared with WiFi and Bluetooth.
- Thread: a mesh networking protocol that uses the same 802.15.4 radio as Zigbee but with an IPv6-based upper stack. Not a smart home standard itself, just the transport.
- Matter: the application-layer standard backed by Apple, Google, and Amazon. Runs over Thread, WiFi, or Ethernet. The long-term direction for cross-vendor compatibility.
- WiFi: high overhead, often cloud-dependent, avoid when possible.

### How these protocols actually work

At the bottom of any of these protocols is a radio chip transmitting and receiving packets over the air at a specific frequency. Zigbee, Thread, and Z-Wave are all low-power, low-bandwidth protocols designed for sensors and switches that send tiny messages occasionally — a temperature reading, a button press, a motion event. None of them are anything like WiFi in terms of throughput or power draw.

Above the radio layer, each protocol defines how devices pair with each other, how they form a network, how messages are routed, and how they're secured. Devices need a protocol because they speak over radio, not IP. They aren't on your WiFi network, they don't have IP addresses (Thread devices do, but indirectly), and your computer has no way to hear them natively. Something has to bridge between the radio world and the IP world.

### Why we need coordinator radios

Cluster nodes do not have 802.15.4 or Z-Wave radios built in. They have WiFi and Bluetooth, but those are different protocols on different hardware. Zigbee, Thread, and Z-Wave therefore need a compatible external radio.

The radio commonly uses a Silicon Labs EFR32 or Texas Instruments CC2652-family chip. A USB adapter exposes its serial interface directly to one host as a device such as `/dev/ttyUSB0`. A network adapter puts a serial-to-Ethernet bridge in front of the same type of radio and exposes the serial protocol over a TCP socket. PoE models need only one structured Ethernet run for both data and power.

The coordinator has a specific role in the network: it forms the network, holds its identity and security material, and handles pairing. In Zigbee terms there is exactly one coordinator per network, although mains-powered routers carry most mesh traffic after the network has formed.

A PoE radio is preferred for this homelab. It can be mounted at a radio-friendly location rather than beside a server, rack, SSD, or USB 3.0 controller, all of which can be poor surroundings for a 2.4 GHz radio. If a USB adapter is used instead, put it on a USB 2.0 extension cable to move it away from the host chassis.

### Reading packets from the coordinator

The coordinator handles the radio, but it doesn't know anything about your devices, what they mean, or how to expose them to Home Assistant. That's a separate software layer running on the host. For Zigbee, the standard choice is Zigbee2MQTT (Z2M):

1. Z2M opens the serial connection to the coordinator
2. Decodes incoming Zigbee packets and figures out which device they're from and what they mean (e.g., "this is a temperature reading of 21.5°C from the living room sensor")
3. Publishes the decoded message to an MQTT topic like `zigbee2mqtt/living_room_sensor`

MQTT is a generic pub/sub messaging protocol — Z2M doesn't know or care who's listening. A separate MQTT broker (Mosquitto) holds the messages and delivers them to anything subscribed. Home Assistant's MQTT integration subscribes to the relevant topics and updates its entities when new messages arrive.

With a USB adapter, the full data flow is:

```
sensor → radio packet → coordinator stick → serial/USB → Z2M container → MQTT broker → HA
```

With a network adapter, only the transport between the coordinator and Z2M changes:

```
sensor → radio packet → PoE coordinator → serial/TCP → Z2M pod → MQTT broker → HA
```

Zigbee2MQTT supports this directly. The adapter type and port depend on the selected hardware, but a typical configuration is:

```yaml
serial:
  port: tcp://192.168.76.247:6638
  adapter: zstack
```

Reserve the address in DHCP or assign it statically, and use wired Ethernet rather than WiFi. The serial protocol is latency-sensitive and does not tolerate packet loss as well as a normal application protocol.

Thread is structurally different. Thread devices are IPv6 endpoints — they have addresses and route packets through a Thread border router (OTBR), which bridges Thread and the regular IP network. HA's Matter integration talks to Thread devices over standard IP, no MQTT or serial passthrough required at the HA layer.

## The Two Chosen: Zigbee + Matter-over-Thread

For a GitOps K3s homelab:

- Zigbee via Zigbee2MQTT (Z2M): workhorse protocol, broadest device support, best diagnostics, most homelab-friendly
- Matter-over-Thread via OpenThread Border Router (OTBR): forward-looking, growing device ecosystem, multi-admin support

Both protocols use the same 802.15.4 physical radio layer, but with completely different stacks on top. They should have separate radios. A dual-radio PoE appliance can serve both simultaneously; a single-radio device must be dedicated to either Zigbee or Thread.

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

Use a supported Ethernet/PoE coordinator with Zigbee2MQTT. It remains a Zigbee coordinator, not a proprietary hub: Zigbee2MQTT owns the device model and MQTT integration while it communicates with the radio over TCP.

Choose a model using a Zigbee2MQTT-supported `zstack` or `ember` radio, with coordinator backup support and an external antenna. Confirm the exact adapter type, firmware, TCP port, and migration path before purchase. Avoid depending on a vendor's cloud service.

Consumer hubs such as Hue Bridges and Echos do not expose a general-purpose coordinator socket for Zigbee2MQTT and remain tied to their own integration model.

### Thread Border Router

Built into many consumer devices because Matter requires Thread border routers to be multi-admin and interoperable:

- Apple TV 4K (2nd gen+), HomePod mini
- Google Nest Hub (2nd gen), Nest Hub Max
- Amazon Echo (4th gen+)

Or a dedicated OpenThread implementation:

- A standalone Ethernet/PoE Thread border router that runs the Thread routing stack on the appliance
- An Ethernet/PoE Thread RCP that exposes its radio protocol to an OTBR instance running elsewhere
- A USB RCP attached directly to the OTBR host

These are materially different. A standalone border router is already the IPv6 router between Thread and the LAN, so the cluster should discover and use it as a network peer; it does not need another OTBR pod. A network-attached RCP is only a remote radio, so the OTBR pod still owns the Thread stack and routing. Confirm that the selected OTBR image supports the vendor's network RCP transport before buying it.

For this homelab, prefer a standalone wired PoE border router if it provides local management, standards-compatible discovery, credential backup or sharing, and usable diagnostics. Otherwise, use a supported network RCP with the existing OTBR deployment. Both options remove the radio's attachment to a particular K3s node, but only the standalone border-router option removes OTBR's privileged host-network routing responsibilities from Kubernetes.

## What the Devices Actually Connect To

Devices have no concept of nodes, containers, or clusters. They see only:

- A radio mesh on a specific frequency
- A network key
- Other devices in the mesh

For Zigbee, the connection terminates at the coordinator radio and Zigbee2MQTT owns the coordinator session. With a PoE coordinator, the physical radio is on the LAN rather than attached to a cluster node.

```
[Zigbee device] -> [PoE coordinator] -> [Z2M over TCP] -> [MQTT] -> [HA]
[Thread device] -> [Thread border router] -> [IPv6 LAN] -> [Matter controller / HA]
```

## The Containers

Coordinator radios do nothing useful for Home Assistant without software driving or integrating them. With Zigbee and an RCP-based Thread design, the protocol software lives in the container. A standalone Thread border router runs its routing stack on the appliance instead.

### Zigbee2MQTT

- Reads/writes the Zigbee coordinator over a local serial device or TCP socket
- Translates Zigbee messages to MQTT topics
- Publishes device state to a Mosquitto broker
- HA subscribes via its MQTT integration, auto-discovers entities
- Memory: ~80-150 MB

### OpenThread Border Router

- Drives a local or network-attached Thread RCP, unless OTBR runs on the appliance itself
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

## Kubernetes Placement

A USB radio creates a hard dependency on one node. Its pod needs a `hostPath` device mount, elevated device access, and a `nodeSelector` or affinity rule. If that node fails, Kubernetes cannot restore service on another node without physically moving the adapter.

A PoE Zigbee coordinator removes that dependency. Zigbee2MQTT becomes a normal single-replica workload that can connect to the coordinator from any cluster node. The deployment no longer needs the radio `hostPath`, USB-related privileges, or smart-home node selector. Its persistent data still needs to be available after rescheduling.

The same benefit applies to an OTBR pod using a network RCP, although OTBR still needs host networking, `/dev/net/tun`, and network-administration privileges to route Thread traffic. A standalone PoE border router moves that entire function out of Kubernetes.

Keep coordinators on the local wired management or IoT network with stable IP reservations. Allow only the required coordinator port from the consuming workload or cluster nodes, keep management interfaces restricted, and ensure IPv6 plus required multicast discovery can pass between a standalone Thread border router and Matter controllers.

## Single Active Client, Not Multiple Replicas

Whether the serial link is USB or TCP, a coordinator or RCP normally accepts one active controller. Implications:

- `replicas: 1`, always
- `strategy: Recreate`, not RollingUpdate, so a replacement does not contend with the old pod for the socket
- Do not let ZHA, a second Z2M instance, or diagnostic software connect to the same coordinator concurrently
- Resilience comes from rescheduling and backups, not multiple active Zigbee2MQTT or OTBR replicas

```yaml
spec:
  replicas: 1
  strategy:
    type: Recreate
```

## Preferred Deployment Layout

On the wired LAN:

1. A PoE Zigbee coordinator at a central, radio-friendly location
2. A separate PoE Thread border router, or a separate PoE Thread RCP if OTBR remains in K3s

In the cluster:

3. Z2M, 1 replica with `Recreate`, connects to the Zigbee coordinator over TCP, PVC for data
4. OTBR, 1 replica with `Recreate`, only if using a network RCP
5. Mosquitto, runs anywhere, PVC for data
6. Home Assistant, runs anywhere, PVC for config and database

There is no dedicated smart-home K3s node and no need to run Mosquitto beside the Zigbee coordinator.

## Resilience

The PoE design removes the K3s node as a radio failure domain, but each coordinator remains a single point of failure. It also depends on the Ethernet path and PoE switch. Mitigations:

- Back up Z2M's data dir (Zigbee network key, device database)
- Back up the Zigbee coordinator and OTBR operational data using hardware-supported procedures
- Put the PoE switch on UPS power and keep a tested spare coordinator with compatible firmware
- Document the coordinator IP addresses, firmware, radio type, TCP ports, and restore procedure
- Thread can use multiple border routers on the same Thread network for redundancy; Zigbee has one coordinator per network
- Test adapter migration before depending on it; changing radio families can require devices to be re-paired

## Debugging by Layer

The clean layering makes failure isolation easy:

- Device won't pair -> radio/coordinator/controller issue (check Z2M or OTBR logs)
- Paired but not in HA -> MQTT broker or HA integration issue
- In HA but commands fail -> command path issue (HA -> broker -> container -> device)
- Z2M pod or node down -> Zigbee radio and mesh remain powered, but HA integration and coordinator-driven control pause until the pod reschedules
- Coordinator, switch, or cable down -> affected radio network loses its IP bridge
- HA pod down -> mesh keeps working, just no consumer until HA returns

Use the Z2M map view and OTBR topology view for mesh diagnostics. First place to look when a device gets flaky.

## References

- [Zigbee2MQTT adapter settings](https://www.zigbee2mqtt.io/guide/configuration/adapter-settings.html)
- [Zigbee2MQTT supported adapters](https://www.zigbee2mqtt.io/guide/adapters/)
- [OpenThread co-processor designs](https://openthread.io/platforms/co-processor)
- [OpenThread Border Router](https://openthread.io/guides/border-router)
