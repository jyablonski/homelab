# Smart Home Device List & Rough Pricing

All prices are USD, rough street prices as of mid-2026. Local-first / no-cloud / no-subscription picks preferred throughout.

## Access & Entry

| Device                                            | Notes                                                                                                        | Qty | Unit | Subtotal |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | --- | ---- | -------- |
| Yale Assure Lock 2 with Matter-over-Thread module | Front door deadbolt. Local control via Thread, no cloud.                                                     | 2   | $250 | $500     |
| Konnected GDO blaQ (ratgdo board, productized)    | Local Home Assistant control of existing garage opener. Verify your opener is Security+ 2.0 (pre-late-2025). | 1   | $70  | $70      |
| Reolink PoE Doorbell (POE, RTSP)                  | Wired PoE, integrates with HA + Frigate. No subscription.                                                    | 1   | $100 | $100     |
| Subtotal                                          |                                                                                                              |     |      | $670     |

## Cameras & NVR

| Device                                          | Notes                                                                                                                                                                                          | Qty | Unit | Subtotal |
| ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --- | ---- | -------- |
| Reolink RLC-820A 4K PoE camera                  | Front door, garage, side gate, backyard.                                                                                                                                                       | 4   | $90  | $360     |
| Coral USB TPU                                   | Dedicated inference accelerator for Frigate. Offloads object detection from cluster nodes so camera ML doesn't compete with other workloads. Requires device plugin setup for K3s passthrough. | 1   | $60  | $60      |
| Dedicated NVMe SSD for Frigate recordings (2TB) | Separate disk for continuous camera writes.                                                                                                                                                    | 1   | $150 | $150     |
| Subtotal                                        |                                                                                                                                                                                                |     |      | $570     |

## Presence, Motion & Contact Sensors

| Device                                              | Notes                                                                                                                            | Qty | Unit | Subtotal |
| --------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- | --- | ---- | -------- |
| Aqara FP2 mmWave presence sensor                    | Living room, bedroom, office, any room needing stillness detection. FP400 is the 2026 upgrade if you want Thread-native (~$120). | 4   | $85  | $340     |
| Aqara P1 / Hue motion sensor (PIR)                  | Hallways, closets, bathrooms, laundry. PIR is fine where you just need on/off.                                                   | 6   | $20  | $120     |
| Aqara / Sonoff Zigbee door & window contact sensors | Exterior doors and windows.                                                                                                      | 12  | $12  | $144     |
| Subtotal                                            |                                                                                                                                  |     |      | $604     |

## Lighting & Switches

| Device                                   | Notes                                                         | Qty | Unit | Subtotal |
| ---------------------------------------- | ------------------------------------------------------------- | --- | ---- | -------- |
| Inovelli Blue Series 2-1 (Zigbee) switch | Main living areas, dimmable rooms. LED bar for notifications. | 12  | $55  | $660     |
| Inovelli Aux switch (for 3-ways)         | Companion switches in multi-way circuits.                     | 4   | $25  | $100     |
| Subtotal                                 |                                                               |     |      | $760     |

Smart bulbs intentionally omitted in favor of switches. Add color/temp bulbs later for specific accent fixtures if you want adaptive lighting.

## Window Coverings

| Device                                                                                | Notes                                                                                                          | Qty | Unit | Subtotal |
| ------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | --- | ---- | -------- |
| IKEA PRAKTLYSING / TREDANSEN cellular blinds (Zigbee via DIRIGERA, or direct via Z2M) | Bedroom, west-facing windows for thermal automation, anywhere glare matters. Cheapest viable motorized option. | 6   | $180 | $1,080   |
| IKEA DIRIGERA hub (optional; can pair direct to Z2M)                                  | Skip if pairing directly to your Zigbee coordinator.                                                           | 0   | $60  | $0       |
| Subtotal                                                                              |                                                                                                                |     |      | $1,080   |

Lutron Serena is the premium upgrade (~$350/window) if bedroom motor noise becomes an issue. SwitchBot Blind Tilt (~$70) is the retrofit option for existing horizontal blinds.

## Climate & Environment

| Device                                                 | Notes                                                                                                                                                                                                                                                                                                                    | Qty | Unit | Subtotal |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --- | ---- | -------- |
| Thermostat (deferred)                                  | Zigbee/Thread thermostat options for US forced-air HVAC are weak as of 2026. Realistic paths: (1) keep dumb thermostat and let room temp sensors drive automations, (2) Ecobee with HACS local integration (~$230, WiFi but talks locally to HA), (3) wait for Matter thermostat support to mature. Not buying this yet. | 0   | $0   | $0       |
| Aqara / Sonoff temperature & humidity sensors (Zigbee) | One per room. Drives blind automation, HVAC awareness.                                                                                                                                                                                                                                                                   | 8   | $15  | $120     |
| Aqara TVOC air quality monitor (Zigbee)                | PM2.5, CO2, VOC. Useful during SoCal fire season. Local via Zigbee.                                                                                                                                                                                                                                                      | 2   | $70  | $140     |
| Subtotal                                               |                                                                                                                                                                                                                                                                                                                          |     |      | $260     |

## Water Protection

| Device                                      | Notes                                              | Qty | Unit | Subtotal |
| ------------------------------------------- | -------------------------------------------------- | --- | ---- | -------- |
| Aqara Zigbee water leak sensor              | Under sinks, behind washer, water heater, fridge.  | 6   | $20  | $120     |
| Aqara Smart Water Valve Controller (Zigbee) | Auto-close on leak detection. Zigbee, fully local. | 1   | $80  | $80      |
| Subtotal                                    |                                                    |     |      | $200     |

## Energy Monitoring

| Device                                  | Notes                                                                        | Qty | Unit | Subtotal |
| --------------------------------------- | ---------------------------------------------------------------------------- | --- | ---- | -------- |
| IotaWatt (whole-home, local-first)      | Local-first, no cloud needed. Better fit than Emporia Vue given your stance. | 1   | $200 | $200     |
| CT clamps for IotaWatt (14-channel kit) | Sized to your panel circuits.                                                | 1   | $150 | $150     |
| Subtotal                                |                                                                              |     |      | $350     |

## Cleaning Robots

| Device                | Notes                                                                                                                     | Qty | Unit | Subtotal |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------- | --- | ---- | -------- |
| Roborock S8 Pro Ultra | Vacuum + mop, self-empty dock. HA integration via `roborock` integration (local where supported). Refurb available ~$450. | 1   | $800 | $800     |
| Subtotal              |                                                                                                                           |     |      | $800     |

## Radio Coordinators

| Device                                              | Notes                                                                                                  | Qty | Unit | Subtotal |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | --- | ---- | -------- |
| Home Assistant Connect ZBT-1 (or Sonoff ZBDongle-E) | Concurrent Zigbee + Thread on a single stick. Pin to a specific K3s node via nodeSelector.             | 1   | $40  | $40      |
| USB 2.0 extension cable (1m)                        | Moves coordinator away from host chassis to reduce 2.4 GHz RF interference. USB 2.0 only, not USB 3.0. | 1   | $8   | $8       |
| Subtotal                                            |                                                                                                        |     |      | $48      |

## Wall Display

| Device                           | Notes                                                                                   | Qty | Unit | Subtotal |
| -------------------------------- | --------------------------------------------------------------------------------------- | --- | ---- | -------- |
| Lenovo Tab M11 (or similar)      | Wall-mounted HA dashboard with daily briefing view. Fully Kiosk Browser for kiosk mode. | 1   | $180 | $180     |
| Wall mount + USB power cable run | Magnetic or recessed mount.                                                             | 1   | $40  | $40      |
| Subtotal                         |                                                                                         |     |      | $220     |

## Totals

| Category                           | Subtotal |
| ---------------------------------- | -------- |
| Access & Entry                     | $670     |
| Cameras & NVR                      | $570     |
| Presence, Motion & Contact Sensors | $604     |
| Lighting & Switches                | $760     |
| Window Coverings                   | $1,080   |
| Climate & Environment              | $260     |
| Water Protection                   | $200     |
| Energy Monitoring                  | $350     |
| Cleaning Robots                    | $800     |
| Radio Coordinators                 | $48      |
| Wall Display                       | $220     |
| Grand Total                        | $5,562   |

## Notes on Sequencing

If you want to phase this:

1. Foundation first: Switches + contact sensors + leak sensors + locks. These are the highest daily-use, lowest-regret items.
2. Presence and lighting automation: FP2s + motion sensors. Unlocks the bulk of the "magic" automations.
3. Cameras and Frigate: Standalone project, can happen any time after networking is ready.
4. Climate, blinds, energy: These layer on once room-level sensing is in place.
5. Robots and wall display: Quality-of-life additions, not foundational.

Quantities for sensors, switches, and contacts are placeholders. Walk the house, count actual switches, exterior doors, and rooms before ordering. Switch count is usually the biggest swing factor.
