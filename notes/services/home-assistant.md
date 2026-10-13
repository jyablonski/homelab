# Home Assistant Notes

## Overview

Home Assistant (HA) is a self-hosted smart home platform that unifies devices across multiple protocols into a single interface. Automations, dashboards, and device state are all manageable from one place.

---

## Protocols

HA sits on top of several device protocols; this homelab uses Zigbee (via Zigbee2MQTT and Mosquitto) and Matter-over-Thread, each through a PoE coordinator on the LAN rather than a USB stick in a cluster node. Protocol details, hardware selection, and data flows are in [device_protocols.md](../hardware/device_protocols.md).

---

## Devices Worth Starting With

| Device                      | Protocol             | Notes                                       |
| --------------------------- | -------------------- | ------------------------------------------- |
| Aqara door/window sensors   | Zigbee               | ~$10 each, reliable                         |
| Aqara motion sensors        | Zigbee               | ~$15 each                                   |
| Schlage BE469 / Yale YRD256 | Z-Wave               | Front and back door locks                   |
| Lutron Caseta switches      | Lutron (proprietary) | Requires small Lutron hub, very reliable    |
| Shelly Plug S               | Wi-Fi                | Per-outlet energy monitoring, local API     |
| Ecobee thermostat           | Wi-Fi                | Exposes more sensors than Nest, HA-friendly |

---

## K3s Cluster Setup

### Radio Placement

Use PoE coordinators on the wired LAN and keep the radios out of the cluster nodes. Zigbee2MQTT connects to the Zigbee coordinator over TCP, so it is a normal single-replica workload that can run on any node: no node label, `nodeSelector`, `hostPath` device mount, or privileged USB access.

A USB stick is the fallback, not the default. It pins the pod to whichever node holds the stick and takes the radio network down with that node. The trade-offs and the Thread options are covered in [device_protocols.md](../hardware/device_protocols.md#kubernetes-placement).

### Cluster Layout

```
wired LAN: PoE Zigbee coordinator, PoE Thread border router
any node:  Zigbee2MQTT pod, Mosquitto pod, HA pod
```

HA, Mosquitto, and Zigbee2MQTT communicate over the network, so they can run on any node. Persistent config and database should be backed by Longhorn.

---

## Config as Code

Almost all HA configuration can be stored in YAML and managed in git.

### What Can Be Git-Managed

- Automations
- Scripts
- Scenes
- Dashboards (Lovelace in YAML mode)
- Template sensors, input helpers, groups
- `configuration.yaml` root config

### What Requires the UI

- Initial device pairing (Zigbee, Z-Wave)
- OAuth / cloud integration auth flows (Nest, Spotify, etc.)
- Area and device room assignment (cosmetic)

### Repo Structure

```
ha-config/
  configuration.yaml
  automations/
    lighting.yaml
    presence.yaml
    locks.yaml
  scripts/
  scenes/
  dashboards/
    main.yaml
  secrets.yaml        # gitignored
  .gitignore
```

Split config across files in `configuration.yaml`:

```yaml
automation: !include_dir_merge_list automations/
script: !include scripts.yaml
scene: !include scenes.yaml
```

### Secrets

Use HA's built-in secrets mechanism. Reference in config:

```yaml
password: !secret mqtt_password
```

Keep `secrets.yaml` gitignored. Manage via a k8s Secret mounted into the HA pod.

---

## Recommended Workflow

Source of truth is git. UI editor is for prototyping only.

1. Build an automation in the UI to learn the YAML structure
2. Copy the generated YAML from `automations.yaml` into your repo
3. Delete it from the UI-managed file
4. All future edits happen in code only

### Applying Changes

Edit on a branch, sync files to the HA config volume, reload without restarting the pod:

```bash
# reload automations
curl -X POST http://homeassistant:8123/api/services/automation/reload \
  -H "Authorization: Bearer <token>"

# reload scripts
curl -X POST http://homeassistant:8123/api/services/script/reload \
  -H "Authorization: Bearer <token>"
```

Test on branch, validate behavior in HA, then open PR and merge to main.
