# Pi-hole

## Goal

Use Pi-hole to provide network-wide DNS filtering for the LAN, blocking ads, trackers, telemetry, malicious domains, and other unwanted traffic caught by OISD and HaGeZi while preserving the homelab's local `.home` DNS records.

## Status

Pi-hole is currently a workstation-only DNS server. The LAN-wide cutover should wait until the cluster is reliable enough to provide DNS continuously. The planned emergency fallback is the router's own DNS forwarder rather than a permanently running second Pi-hole.

## Current architecture

The current Helmfile release deploys one Pi-hole replica in Kubernetes with a persistent Longhorn volume. DNS is exposed through MetalLB at `192.168.76.246` with `externalTrafficPolicy: Local`. The DNS service accepts both TCP and UDP through the mixed service configuration.

Pi-hole remains separate from Kubernetes service discovery. K3s CoreDNS handles names such as `*.svc.cluster.local`; Pi-hole handles LAN clients, external DNS lookups, and the homelab's `.home` records.

Current local DNS behavior:

- `*.home` resolves to Traefik at `192.168.76.245`.
- `registry.home` resolves directly to the registry at `192.168.76.250`.
- Pi-hole's web UI is reached through Traefik at `http://pihole.home/admin/`.
- Only the workstation is currently configured to use `192.168.76.246`.
- The router remains responsible for DHCP.

Relevant implementation files are [pihole values](../../services/pihole/values.yaml), [Helmfile](../../helmfile.yaml), [workstation DNS helper](../../scripts/setup-local-pihole-dns.sh), and [MetalLB address pool](../../services/metallb/ip-pool.yaml).

## Workstation operation

`make up` enables Pi-hole DNS on the workstation after Pi-hole is ready. `make down` disables the workstation override before cluster teardown.

```bash
make pihole-dns-enable
make pihole-dns-disable
make pihole-dns-status
```

This changes the active NetworkManager connection to use Pi-hole as its IPv4 DNS server. Internet access continues to work normally, while `.home` requests resolve to cluster services.

Disable the workstation override before taking down the cluster if the cluster is not expected to remain available:

```bash
make pihole-dns-disable
```

## DNS flow after LAN cutover

```text
LAN clients
    |
    | DHCP advertises Pi-hole as DNS
    v
Pi-hole LoadBalancer 192.168.76.246
    |-- blocked domain ------------------> Pi-hole blocking response
    |-- *.home --------------------------> Traefik 192.168.76.245
    |-- registry.home -------------------> Registry 192.168.76.250
    `-- all other names -----------------> Explicit upstream DNS

K3s pods
    |
    v
K3s CoreDNS
    |-- *.svc.cluster.local -------------> Kubernetes services
    `-- external names ------------------> Upstream resolver path
```

Pi-hole is therefore the DNS boundary between the LAN and the internet, not the DNS implementation for Kubernetes internals. This preserves normal K3s behavior while allowing every LAN client that uses Pi-hole to receive filtering and `.home` resolution.

## Blocklists

The names OISD and HaGeZi refer to families of lists with multiple variants. This configuration uses OISD Big and HaGeZi Multi Pro.

| List             | Purpose                                                                                                                                                         |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| OISD Big         | Functionality-first blocking of ads, mobile ads, trackers, telemetry, phishing, malvertising, malware, ransomware, cryptojacking, and similar unwanted domains. |
| HaGeZi Multi Pro | Balanced, broader blocking of ads, affiliate tracking, telemetry, phishing, malware, scams, fake stores, cryptojacking, and other harmful domains.              |

Both are broad all-in-one lists and overlap substantially. Using both can provide some additional coverage, but the main cost is a larger gravity database and more complicated false-positive troubleshooting. Do not begin by stacking HaGeZi Pro++ or Ultimate on top of both.

The configured list sources are:

```yaml
adlists:
  - https://big.oisd.nl
  - https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/pro.txt
```

OISD Big is designed for network-wide DNS blockers and prioritizes functionality over maximum blocking. HaGeZi identifies Multi Pro as its balanced, recommended tier for mostly problem-free protection.

An alternative, more complementary pairing is OISD Big plus HaGeZi's Threat Intelligence Feed. That combination uses OISD for general ad/tracker blocking and HaGeZi specifically for malware, phishing, scams, spam, cryptojacking, and command-and-control domains.

The MoJo2600 chart documents `adlists` as lists imported during initial container startup. Since Pi-hole uses a persistent database, add the URLs in the Pi-hole UI on an existing installation and run Tools → Update Gravity after changing the Helm values. The values remain the bootstrap and reproducibility source for fresh or recreated instances.

## LAN rollout

### Phase 1: Cluster-only validation

Keep the workstation-only configuration and confirm that Gravity updates complete, `.home` records still resolve, `registry.home` still resolves directly, and normal browsing works.

Use the Pi-hole query log to identify false positives before changing router DHCP. Keep a short allowlist process for domains that are needed by legitimate applications or devices.

### Phase 2: LAN pilot

Reserve the Pi-hole service IP and confirm that `192.168.76.246` is reachable from wired, wireless, and IoT clients. Change the router's IPv4 DHCP DNS option to advertise Pi-hole instead of the router or a public resolver.

Do not advertise a public resolver as a second DNS server if the goal is consistent filtering. Clients may choose the second resolver and bypass Pi-hole.

Configure IPv6 router advertisements and DHCPv6 to provide Pi-hole as DNS too, or disable IPv6 DNS advertisements until Pi-hole has a reachable IPv6 service. Otherwise, IPv6-capable clients may bypass the IPv4 Pi-hole configuration.

Keep the router as the DHCP server. `serviceDhcp.enabled: false` is appropriate because moving DHCP into a Kubernetes service would add unnecessary broadcast and cluster-availability complexity.

### Phase 3: DNS enforcement

Some clients ignore DHCP DNS settings or use hard-coded resolvers. If the router or firewall supports it, block or redirect LAN traffic to external DNS on UDP/TCP port 53 so that it can only reach Pi-hole. Allow Pi-hole itself to reach its configured upstream resolvers.

DNS-over-TLS, DNS-over-HTTPS, VPNs, Apple Private Relay, and similar mechanisms can bypass ordinary DNS filtering. Pi-hole cannot inspect queries that never reach it. Blocking those paths requires router/firewall policy and may have compatibility costs.

### Phase 4: Availability and emergency fallback

The current single Pi-hole replica is a LAN-wide single point of failure. If the K3s cluster is down, the LAN loses DNS. The existing Longhorn-backed persistent volume also means that simply changing `replicaCount` to two is not a complete high-availability design.

The initial fallback should be the router's own DNS forwarder rather than a permanently running second Pi-hole. This means LAN ad blocking is temporarily unavailable during a Pi-hole or cluster outage, but ordinary internet DNS can be restored without maintaining another device.

Normal operation:

- Run one Pi-hole in the K3s cluster at `192.168.76.246`.
- Configure the router's DHCP DNS setting to advertise `192.168.76.246`.
- Keep the router's own DNS forwarder available as an emergency fallback, but do not advertise it during normal operation.

Emergency fallback:

1. Open the router's LAN/DHCP settings.
2. Change the advertised DNS server from `192.168.76.246` to `Automatic`, `Router`, or the router's own LAN IP address.
3. Remove any Pi-hole address from the secondary DNS field.
4. Save/apply the setting.
5. Renew DHCP leases or reconnect clients so they receive the router as DNS.

The router must actually provide a DNS forwarder for this fallback to work. Test the router's LAN IP as a DNS server before the LAN cutover. The router's upstream DNS configuration is separate from the DNS address advertised to clients; changing the DHCP setting does not require changing the router's upstream resolver.

Device recovery after changing the router setting:

- Linux workstation: run `make pihole-dns-disable`, reconnect the active network connection, and optionally run `resolvectl flush-caches`.
- macOS desktop or laptop: set the active Wi-Fi or Ethernet connection's DNS configuration to `Automatic`, remove any manually entered `192.168.76.246`, renew the DHCP lease, and reconnect if necessary.
- Windows desktop or laptop: set the adapter's IPv4 DNS configuration to `Obtain DNS server address automatically`, then run `ipconfig /release`, `ipconfig /renew`, and `ipconfig /flushdns`.
- iPhone or iPad: open the Wi-Fi network details, set `Configure DNS` to `Automatic`, remove any manually configured Pi-hole address, and toggle Wi-Fi off and on.
- Android phone or tablet: open the connected Wi-Fi network, set IP settings to `DHCP`, set Private DNS to `Automatic` if it was manually configured, and reconnect. Device menus vary by manufacturer.
- Smart TVs, consoles, cameras, and IoT devices: set DNS back to automatic if a static DNS address was configured, then reconnect Wi-Fi or reboot the device.

Browsers or devices with manually enabled DNS-over-HTTPS, VPN DNS, Private Relay, or another encrypted resolver may continue using that resolver independently. The fallback procedure only changes ordinary DHCP-provided DNS.

While the router is the active DNS server, the internet should work normally but Pi-hole filtering and Pi-hole-owned `.home` records will not work unless they are also configured in the router. `pihole.home`, `apps.home`, `registry.home`, and the other homelab names should therefore be expected to fail during fallback.

Validation after fallback:

- Confirm the client received the router's address as its DNS server.
- Run `nslookup example.com` and verify that the reported server is the router.
- Confirm normal internet access.
- Expect a formerly blocked test domain to resolve, because Pi-hole is no longer filtering it.

To return to normal operation, change the router's DHCP DNS setting back to `192.168.76.246`, save it, and renew DHCP leases or reconnect clients. Any device with a manually configured DNS server must also be changed back to automatic or `192.168.76.246`.

A second Pi-hole release with its own persistent volume and another MetalLB address could improve pod-level availability later, but it is not required for the initial LAN rollout. Two Pi-hole instances inside this cluster would still fail together during a cluster outage.

## Upstream DNS

Pi-hole should forward allowed queries to explicitly configured upstream resolvers or to an independently managed recursive resolver such as Unbound. Do not configure Pi-hole to forward to the router after the router begins advertising Pi-hole, because that can create a forwarding loop.

The chart's documented defaults are Google DNS (`8.8.8.8` and `8.8.4.4`). The release currently does not set `DNS1` or `DNS2`, so the upstream policy should be made explicit before the LAN cutover.

Using HaGeZi's public DNS service as Pi-hole's upstream is unnecessary if HaGeZi lists are already installed locally. Keeping list enforcement and upstream resolution separate makes query behavior easier to understand and troubleshoot.

## Failure and operational considerations

- A cluster outage currently means a LAN-wide DNS outage until the router DHCP DNS setting is changed back to the router.
- `make down` restores DNS only for the workstation; it cannot automatically undo a router-wide DHCP change.
- Cluster maintenance, MetalLB issues, Longhorn issues, and Pi-hole pod restarts can temporarily affect LAN DNS.
- `externalTrafficPolicy: Local` is useful for preserving client source addresses in Pi-hole logs, but traffic depends on a node with a local Pi-hole endpoint.
- `FTLCONF_dns_listeningMode: all` is needed for LAN clients, but the service must be protected from unintended external access by the LAN firewall.
- DNS filtering does not remove ads embedded in the same domain as desired content and will not reliably remove YouTube ads.
- Pi-hole provides DNS filtering, not HTTP filtering, TLS interception, content rewriting, or general network intrusion prevention.

## Recommended next changes

1. Make the upstream DNS settings explicit in the Pi-hole values.
2. Test the lists on the workstation and representative IoT devices before changing router DHCP.
3. Test and document the router fallback, including DHCP renewal steps for each device class.
4. Update cluster teardown procedures so LAN DHCP is reverted before taking down the last available Pi-hole.

## References

- [OISD](https://oisd.nl/)
- [OISD FAQ](https://oisd.nl/faq)
- [HaGeZi DNS blocklists](https://github.com/hagezi/dns-blocklists)
- [Pi-hole group management](https://docs.pi-hole.net/group_management/)
- [Pi-hole domain database and gravity](https://docs.pi-hole.net/database/domain-database/)
- [MoJo2600 Pi-hole Helm chart values](https://artifacthub.io/packages/helm/mojo2600/pihole)
