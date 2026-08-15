## 1. Rack overview

**Goal:** consolidate compute, networking, and home-automation radios into a single rack in one location, with structured cabling terminating at a patch panel.

**Gear going in:**

| Item                          | Qty | Rack space                      |
| ----------------------------- | --- | ------------------------------- |
| Mini PCs (Beelink or similar) | 3   | 1U on a shared tray             |
| PoE switch                    | 1   | 1U                              |
| Router                        | 1   | 1U shelf                        |
| Patch panel, 24-port          | 1   | 1U                              |
| PDU                           | 1   | 1U                              |
| Cable management              | 1   | 1U                              |
| Thread/Zigbee dongles         | 2–3 | 0U — mounted _outside_ the rack |

**Total: ~6U in an 18U rack.** Room to double without replanning.

---

## 2. Components and their purpose

**Rack (18U, 19", 4-post, open frame, casters)**
The frame everything bolts to. 19" is EIA-310, unchanged for a century — anything you buy later will fit. Casters mean you can roll it out and work behind it instead of contorting.

**Mini PC tray**
Mini PCs have no rack ears. A 1U tray holds all three side by side. Options: a purpose-built metal tray, or a 3D-printed model-specific mount. Printed mounts are cheaper and fit the exact chassis; metal trays are more generic.

**PoE switch**
Powers and connects the Thread/Zigbee dongles' host devices, APs, cameras, anything PoE. This is the one component with a real lifespan — plan to replace it in 5–10 years as PoE standards (af → at → bt) and port speeds (1G → 2.5G) move.

**Router**
Almost certainly a desktop box, so it goes on a 1U shelf regardless of rack width.

**Patch panel**
Terminates permanent in-wall runs so you never touch them again. Only worth the U if you're actually running cable through walls — if everything starts and ends inside the rack, skip it.

**PDU**
Rack-mount power strip. Front-mounted is fine on an open frame. The mess isn't the outlets — it's five power bricks. Budget a shelf or rear-rail velcro for those, and buy short cords.

**Cable management (1U finger duct or D-ring panel)**
Keeps patch cables from becoming a nest. On an open frame, a brush panel is less useful than it'd be in an enclosure — a D-ring panel plus velcro does more.

**USB 2.0 extension cables**
Non-negotiable for the Thread/Zigbee dongles. Get the coordinators out of the rack and away from USB 3.0 ports and SSDs, which emit right in the 2.4GHz band. Must be USB **2.0**, not 3.0.

**Label maker**
Label both ends of every run, and every patch panel port.

---

## 3. Structured cabling — patch panel to switch

### The two cable types

This is the part that trips people up. They are not interchangeable.

**Solid-core Cat6** — for permanent in-wall runs. Bought by the spool (500ft or 1000ft box). Punches down cleanly and holds. Cracks if flexed repeatedly, so it never gets used as a patch cable.

**Stranded Cat6** — for patch cables. Flexible, survives repeated plugging. Never punch this down; the IDC contacts are designed to bite a solid conductor.

### The flow

```
Wall jack (room)  →  in-wall solid Cat6  →  patch panel port (rack)
                                                    ↓
                                          short stranded patch cable
                                                    ↓
                                              switch port
```

Each run needs **two terminations**: a keystone jack + wall plate at the room end, and a keystone jack punched into the panel at the rack end. So budget 2 keystones per run.

### How to punch down

1. Strip about 1.5–2" of the outer jacket. Use a jacket stripper or score gently — nicking the conductor insulation causes intermittent faults that are miserable to trace.
2. Untwist each pair only as far as you need. Keep untwisted length under ~0.5" — this is what preserves the crosstalk rejection you paid for.
3. Seat the wires into the color-coded channels on the keystone. **Pick 568B and use it on every single jack in the house.** Both ends of a run must match. 568A vs 568B doesn't matter technically; mixing them does.
4. Punch each wire with the 110 tool, blade facing _outward_ toward the cut side. The tool seats the wire and trims the excess in one motion.
5. Snap the cap on, clip the keystone into the panel from the back.
6. Test with a continuity tester before you close the wall up.

### Buying quantities

- One spool of solid Cat6 sized to your total run length (measure generously — vertical drops eat more than you'd think).
- Keystone jacks: 2 × number of runs, plus spares. You will destroy a few learning.
- Patch cables: a 24-pack of slim stranded Cat6 in 0.5ft/1ft, ideally color-coded by purpose.
- Punchdown tool (110) and a cheap continuity tester.

---

## 4. Rack decision and rationale

**Chosen: 18U, 19", 4-post open frame, floor-standing on casters.**

| Decision                     | Why                                                                                                                                                                                           |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **19" over 10"**             | Standard hasn't changed in a century. Huge used market — PDUs, shelves, panels, cable management all cheap secondhand. Denser mini PC trays (3 in 1U). Replacement switches bolt straight in. |
| **18U over 12U**             | Floor-standing, so height is nearly free — same footprint, ~$30 more. Removes capacity as a future question entirely.                                                                         |
| **Open frame over enclosed** | Cheaper, self-cooling, full access to everything. No fan panel needed. Enclosure only earns its cost in living space or with pets/kids.                                                       |
| **4-post over 2-post**       | 2-post would work for this gear, but 4-post supports rear-mounted equipment and rail kits if anything heavier arrives later.                                                                  |
| **Casters over fixed**       | Roll it out to work behind it. Real quality-of-life difference.                                                                                                                               |
| **Adjustable depth**         | Set it shallow. All your gear is ~10" deep; a 40" rack would be furniture. Most 4-post racks adjust 22–40", so collapse it in.                                                                |

**Tradeoff accepted:** 19" gear invites cheap enterprise hardware off eBay, which is loud and power-hungry. Staying mini-PC-first is a discipline thing, not a hardware constraint.

---

## 5. Purchase links

**Racks** — all 18U, 4-post, adjustable depth, casters included:

StarTech 4POSTRACK18U — 1200lb static capacity, ships with casters, leveling feet, _and_ a floor base-plate, plus cage nuts, screws, and cable management hooks. NavePoint 18U — adjustable 22–40" depth, with button-hole toolless mounting for vertical PDUs and cable managers.

- StarTech: https://www.startech.com/en-us/server-management/4postrack18u
- NavePoint: https://navepoint.com/navepoint-18u4-post-open-frame-server-rack-adjustable-depth-with-casters-12-24-threaded/
- Sysracks 18U: https://www.amazon.com/Frame-Server-Network-Casters-Sysracks/dp/B079M19BXD

⚠️ **Check the hole type before ordering.** Square-hole racks take cage nuts; threaded racks are 12-24 or M6. The L-com listing, for example, is explicitly 12-24 threaded. Everything you mount must match, so pick one and buy screws accordingly. Square-hole + cage nuts is the more flexible choice.

**Patch panels** — blank keystone, so you choose the jacks:

ICC IC107BP241 — 24-port blank keystone, 16-gauge steel, EIA-310-E compliant, includes #12-24 screws. Ubiquiti's version ships with a rear cable management bar.

- ICC: https://icc.com/product/blank-patch-panel-24-ports-hd-style-1-rms/
- Ubiquiti: https://store.ui.com/us/en/products/uacc-rack-panel-patch-blank-24
- TRENDnet TC-KP24: https://www.trendnet.com/products/patch-panel/24-Port-Blank-Keystone-1U-Patch-Panel-TC-KP24
- Tripp Lite/Eaton (12/16/24/48-port variants): https://tripplite.eaton.com/24-port-1u-rack-mount-shielded-blank-keystone-multimedia-patch-panel-rj45-ethernet-usb-hdmi-cat5e-cat6~N062024KJSH

Pre-loaded alternative if you'd rather not buy jacks separately: NSI/LYNN ProFIT 24-port, pre-loaded with Cat6 110-punchdown keystones — https://nsiindustries.com/product/1u-profit-keystone-patch-panel-24-port-pre-loaded-with-cat6-110-punchdown-keystones/

**Mini PC trays:**

UCTRONICS 1U rackmount, holds 3 low-profile NUCs — https://www.amazon.com/UCTRONICS-Mount-Rackmount-Supports-Units/dp/B09BJ5WBHB

MyElectronics 1U frame for 1–3 NUCs, with three blanked front-panel holes you can populate with LAN, USB, HDMI, or USB-C pass-through connectors — https://www.myelectronics.nl/us/nuc-minipc-19-rackmount-kit-1-3-nucs.html

3D-printed, model-specific: https://3drackmounts.com/products/intel-nuc-slim-pcs-19-rack-mount-1u-modular and https://racknex.com/shop/intel/

⚠️ **These are all sized for NUCs.** Beelinks are a different footprint — measure yours (W × D × H in mm) and match against the listing before ordering. If nothing fits, a generic vented 1U shelf plus velcro works fine, or search Etsy/Printables for your exact model.

**Still to source** (didn't look these up — commodity items, buy on price):

- Cat6 solid-core spool, 500ft or 1000ft — Monoprice, Cable Matters, trueCABLE
- Cat6 keystone jacks, 568A/B, quantity = 2× runs + spares
- Wall plates + low-voltage mounting brackets
- 110 punchdown tool + continuity tester
- Slim Cat6 patch cables, 24-pack, 0.5–1ft, assorted colors
- 1U PDU (consider a metered or switched model — remote power-cycling a hung mini PC is worth the upgrade, and retrofitting means buying twice)
- 1U vented shelf for the router
- 1U cable management panel
- Cage nuts + screws to match your rack's hole type
- USB 2.0 extension cables, 1–2m
- Label maker
