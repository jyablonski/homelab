## Networking Devices

### All-in-One Routers (e.g., ASUS RT-AX3000, UniFi Express, Dream Router)

Single box combining routing, switching, and Wi-Fi. Easier setup, lower cost, sufficient for most homes.

Strengths:

- Plug-and-play, mobile app setup
- Adequate Wi-Fi for ~1,500-2,000 sqft single-AP coverage
- Built-in switch ports (4 on the ASUS), USB for storage/printer
- AiMesh allows daisy-chaining additional ASUS routers later as nodes

Limits:

- Wi-Fi coverage capped by single-AP physics (multi-floor, thick walls = dead zones)
- Limited VLAN support, weak inter-VLAN firewalling
- All-or-nothing upgrades: Wi-Fi 7 means replacing the whole box
- Less visibility into per-client/per-port behavior

Right when: Single-AP coverage works, no segmentation needs beyond guest Wi-Fi, want consumer-grade ergonomics.

### Modular UniFi (Gateway + Switch + Access Points)

Separate components: gateway routes, switch handles wired + PoE, APs do Wi-Fi only. Unified controller UI.

Reference build (~$400): Cloud Gateway Ultra + USW-Lite-8-PoE + U6-Pro

Strengths:

- Independent upgrade paths (replace AP every ~5 years, keep gateway)
- Better roaming via 802.11k/v/r across multiple wired APs
- PoE: single Cat6 powers APs, cameras, doorbells
- True VLANs with firewall rules between them
- Per-port telemetry; controller surfaces topology, throughput, errors
- No subscription; Protect/Access/Talk available if needed later

Limits:

- 3-4x cost of a consumer all-in-one
- Setup requires more thought (controller, VLANs, firewall posture)
- Software has rough edges; updates occasionally regress
- Cable runs are the real commitment — APs work best ceiling-mounted with wired backhaul

Right when: Multi-AP coverage needed, want segmentation for IoT/homelab/guest, planning to add PoE devices, or enjoy network visibility as a feature.

### Wi-Fi AP Placement

- Ceiling mount in central hallways/open areas (looks like a smoke detector)
- One AP covers ~1,500-2,500 sqft open-plan; less with interior walls
- Multi-story: one AP per floor, roughly stacked
- Avoid: closets, behind furniture, near microwaves/fridges, low to floor
- Wired backhaul >> wireless mesh (mesh halves throughput, adds latency)

### Advanced Features (Managed Switch Territory)

VLAN tagging — One physical network behaves as multiple isolated networks. Frames tagged with VLAN ID; switch enforces isolation.

- _Use case:_ Isolate IoT (compromised bulb can't reach laptop), separate homelab from family traffic so breaking Traefik at 11pm doesn't kill Netflix.

Per-port visibility — Real-time stats per port: throughput, errors, link speed, PoE draw, connected MAC.

- _Use case:_ Diagnose slow connections (cable negotiated at 100Mbps not 1Gbps), audit forgotten devices still drawing PoE.

Port profiles — Reusable port config templates (VLAN assignment, trunk/access, PoE, etc.).

- _Use case:_ Standardize AP trunk uplinks across multiple switches; treat network config like Terraform modules — define once, apply everywhere, no drift.

### VLAN Architecture for K3s + Home Assistant + IoT

Three VLANs: Trusted (personal devices), Homelab (K3s nodes, HA), IoT (smart devices).

Default-deny inter-VLAN firewall, with allows:

- Trusted -> anywhere
- Homelab -> IoT (HA polls devices)
- IoT -> specific Homelab IPs/ports only (Pi-hole DNS, HA webhooks)
- Established/related traffic always allowed (stateful firewall handles return packets)
- IoT -> Homelab/Trusted: deny

Gotchas:

- mDNS/SSDP don't cross VLANs by default — enable multicast DNS reflector or use static IPs in HA
- Prefer Zigbee/Z-Wave/Matter-over-Thread devices: they sidestep IP networking entirely
- MetalLB IP pool should live on Homelab subnet
- WiFi IoT devices must be re-paired when migrating SSIDs — plan for friction

### IoT Threat Model (Realistic)

Common compromises: default credentials (Mirai-style), unpatched firmware, vendor cloud breaches (Eufy/Ring/Wyze), botnet conscription.

Practical risk for typical homes: mostly botnet participation and camera-feed exposure, rarely targeted lateral movement.

Why segmentation matters more for homelabbers: the high-value asset (K3s cluster, work code) sits on the same network as the riskiest devices. IoT foothold -> cluster recon is the asymmetry segmentation closes.

Higher-impact than segmentation: buy reputable brands, prefer non-WiFi protocols (Zigbee/Z-Wave), keep firmware patched, don't port-forward (Cloudflare Tunnel ✓), monitor DNS egress via Pi-hole.

### Migration Path

1. Plug everything in flat on default VLAN; verify it works
2. Use controller for visibility; tag clients with friendly names
3. Define VLANs in controller without assigning ports (zero impact)
4. Migrate K3s nodes to Homelab VLAN first (you control these)
5. Stand up IoT SSID; re-pair devices one at a time
6. Flip to default-deny firewall last, add specific allows as needed

VLAN/port reassignment is pure software via the controller — no recabling required. Only physical work is pulling new Cat6 to AP locations, ideally during move-in.
