# Smart Home Management

## Power categories

Smart home devices split into two main groups based on how they're powered, and the design tradeoffs are very different.

### Mains-powered

Tap directly into household wiring with effectively unlimited power budget. Supports always-on radios, more powerful processors, richer features.

Examples: smart bulbs, hardwired thermostats (using HVAC C-wire), PoE cameras, plug-in hubs.

Smart bulbs include a small AC-to-DC switching regulator to step 120V/240V down to the 3.3V or 5V the LED driver and radio need. This is why they have a persistent standby draw (typically 0.3-0.5W) even when "off" - the radio stays alive to receive commands.

### Battery-powered

Devices where running a wire is impractical: door/window sensors, motion sensors, temperature/humidity sensors, leak detectors, smart locks, motorized blinds, remote buttons.

The engineering challenge is brutal: years of battery life from a coin cell or a couple of AAs. This forces several design constraints.

## How battery devices stretch power

### Low-power radios

Wi-Fi is a nonstarter for battery devices. The radio is hungry and the association/handshake process burns energy. Battery sensors use Zigbee, Z-Wave, Thread, or Bluetooth LE. These protocols are designed around short bursts of transmission with the radio sleeping over 99% of the time.

A Zigbee temperature sensor might wake every few minutes, take a reading, transmit ~50 bytes, and go back to deep sleep. Average current draw in the microamps.

### Sleep-by-default MCUs

The microcontroller spends almost all its time in deep sleep (1-10 µA) and wakes on either a timer interrupt or an external event (reed switch closing on a door sensor, PIR motion detector triggering). Active time is measured in milliseconds.

### Event-driven vs polled

A door sensor only transmits when the door state changes, plus an occasional heartbeat. A temperature sensor might report on a fixed interval or only when the reading changes by a threshold. Less radio time means more battery life.

With this design, a CR2032 coin cell (~220 mAh) can last 2-5 years in a door sensor, and AA batteries can last 5-10 years in some Z-Wave sensors.

## Naming devices

When devices join via Zigbee/Thread coordinator stick, they show up with cryptic identifiers (IEEE addresses, manufacturer-assigned names). Rename them once during onboarding and the friendly name propagates everywhere.

In Home Assistant the hierarchy is:

- Device name: `living_room_temperature_sensor` (the physical thing)
- Entity IDs: auto-generated, like `sensor.living_room_temperature_sensor_battery`
- Area: `living_room` (grouping concept for automations)

Naming convention: pick `{area}_{type}_{instance}` and stick to it - `family_room_blind_1`, `office_motion_sensor`, `garage_door_sensor`. Future automations will benefit from consistency.

## Tracking battery levels programmatically

Battery-powered devices report level as a standard attribute on whatever cadence the firmware decides.

Protocol specifics:

- Zigbee: `genPowerCfg` cluster (0x0001) with `batteryPercentageRemaining` and `batteryVoltage` attributes
- Z-Wave: Battery Command Class (0x80) with `BATTERY_GET` / `BATTERY_REPORT`
- Matter/Thread: Power Source cluster (0x002F) with `BatPercentRemaining` and `BatChargeLevel`
- BLE: Battery Service (0x180F) with Battery Level characteristic (0x2A19)

Typical reporting cadence:

- Aqara/Xiaomi sensors: every 50-60 minutes
- Sonoff sensors: every hour or two
- Z-Wave locks: once per day or on wake-up
- Most Thread/Matter devices: configurable, often hourly

In Home Assistant these become sensor entities automatically. With Zigbee2MQTT they also publish to predictable MQTT topics like `zigbee2mqtt/front_door/battery`, which makes piping data into Prometheus, Postgres, or Lightdash straightforward.

### Retention strategy

Keep 30-90 days of battery telemetry. Enough to spot trend changes (sudden faster discharge often signals a firmware bug or radio interference forcing retries) without bloating the database. Set HA recorder retention accordingly or ship to longer-term storage.

## Low battery automations

Standard pattern - takes 30 seconds to set up.

```yaml
automation:
  - alias: "Low battery notification"
    trigger:
      - platform: time
        at: "09:00:00"
    action:
      - variables:
          low_battery_devices: >
            {{ states.sensor
               | selectattr('attributes.device_class', 'eq', 'battery')
               | selectattr('state', 'is_number')
               | selectattr('state', 'lt', '30')
               | map(attribute='name')
               | list }}
      - condition: template
        value_template: "{{ low_battery_devices | length > 0 }}"
      - service: notify.mobile_app_your_phone
        data:
          title: "Low batteries"
          message: "{{ low_battery_devices | join(', ') }}"
```

### Variations worth considering

- Per-device thresholds: locks at 30% (motor brownouts when low), sensors at 15% (more headroom)
- Escalating alerts: daily reminder at 30%, hourly at 10%
- Grafana alerting if data is already piped there - richer routing than HA's built-in
- Slack or ntfy notifications instead of mobile push

## Gotchas

The reported percentage is often a lie. Many devices report based on voltage thresholds rather than coulomb counting, and discharge curves are nonlinear. Devices commonly sit at 100% for months, drop to 50%, then to 10% within a week or two. Battery voltage (when exposed separately) is sometimes more informative than the percentage.

Dead-battery devices go "unavailable" in HA, not "0%". Automations should also alert on devices that haven't reported in N hours - a dead sensor stops reporting battery before it ever reports 0%.

Track battery type per device (CR2032, AA, USB-C rechargeable) as a device attribute or in a separate reference table. When an alert fires, knowing what battery to grab (or whether to pull down a blind for charging) saves a trip.
