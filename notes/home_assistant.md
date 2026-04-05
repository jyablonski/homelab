# Home Assistant Notes

## Overview

Home Assistant (HA) is a self-hosted smart home platform that unifies devices across multiple protocols into a single interface. Automations, dashboards, and device state are all manageable from one place.

---

## Protocols

Smart home devices communicate over different radio protocols. Each protocol needs its own USB coordinator plugged into a server and its own software translator. HA sits on top of all of them.

### Zigbee

Best for: sensors, bulbs, outlets. Cheap, low power, local control.

- Runs on 2.4GHz
- Devices form a mesh — plugged-in devices repeat signals and extend range
- Needs a USB coordinator (Sonoff Zigbee 3.0 Dongle Plus ~$20)
- Software: Zigbee2MQTT + Mosquitto MQTT broker
- Data flow: `device -> USB dongle -> Zigbee2MQTT -> MQTT broker -> HA`

### Z-Wave

Best for: locks. More reliable and better security than Zigbee for critical devices.

- Runs on 908MHz (US) — less congested than 2.4GHz
- Stronger encryption (S2 security framework)
- Needs a USB stick (Zooz 800 series ~$40)
- Software: Z-Wave JS + optionally Z-Wave JS UI for device management
- Data flow: `lock -> USB stick -> Z-Wave JS -> HA`

### Wi-Fi

Best for: thermostats, cameras. No extra coordinator needed — devices join your normal network and HA talks to them via their own integrations.

### Matter / Thread

Newer standard backed by Apple, Google, Amazon. HA has solid support. Thread devices need a border router (Apple TV 4K or HomePod mini).

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

### USB Coordinator Placement

Each USB dongle must be physically plugged into a specific node. The coordinator pod must run on that same node.

Label the node:

```bash
kubectl label node <node-name> protocol=zwave
kubectl label node <node-name> protocol=zigbee
```

Pin the deployment to that node:

```yaml
spec:
  template:
    spec:
      nodeSelector:
        protocol: zwave
```

### USB Device Passthrough

Mount the USB device into the container:

```yaml
volumeMounts:
  - name: zwave-usb
    mountPath: /dev/ttyUSB0
volumes:
  - name: zwave-usb
    hostPath:
      path: /dev/serial/by-id/usb-<device-id>
      type: CharDevice
securityContext:
  privileged: true
```

Use `/dev/serial/by-id/` paths instead of `/dev/ttyUSB0` — they are stable across reboots.

### Cluster Layout

```
node-1: Z-Wave USB stick -> Z-Wave JS pod
node-2: Zigbee dongle -> Zigbee2MQTT pod + Mosquitto pod
any node: HA pod (talks to coordinators over cluster network)
```

HA communicates with coordinators over the network, so it can run on any node. Persistent config and database should be backed by Longhorn.

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
