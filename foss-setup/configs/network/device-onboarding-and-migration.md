# Device → Subnet Assignment, IoT Onboarding & Fleet Migration Helper

The missing piece that sits on top of [`vlan-zone-firewall-plan.md`](vlan-zone-firewall-plan.md):
**where every device goes, how to get each IoT device onto its network, and a
repeatable helper for migrating the whole fleet** — while keeping HomeKit/Siri
working *and* adding everything to the new Home Assistant Green.

> Read order: [`vlan-zone-firewall-plan.md`](vlan-zone-firewall-plan.md) →
> [`mdns-multicast-checklist.md`](mdns-multicast-checklist.md) →
> [`firewall-policy-order.md`](firewall-policy-order.md) → **this file**.
> The VLANs/zones/firewall must already exist (they do) before you migrate devices.

---

## 0. TL;DR decisions

- **6 VLANs already built:** Default/mgmt `1`, Trusted `10`, IoT `20`, Cameras `30`,
  Work `40`, Guest `50`. This doc only *places devices* into them.
- **HA Green lives on Trusted (VLAN 10)** — it's a trusted controller, and keeping it
  with the Apple hubs avoids reflecting Matter across a VLAN boundary (your repo's
  Matter caveat).
- **Apple TVs + HomePods go on Trusted (VLAN 10), NOT IoT** — they are your HomeKit
  hubs and Thread border routers; they must share a subnet with HA's Matter controller.
  This is a deliberate deviation from the generic "streaming sticks → IoT" line in the
  VLAN plan, and it's the right call for HomeKit↔HA coexistence.
- **Two dual-control patterns** (detailed in §3): *native dual* (device speaks HomeKit
  itself → add to Apple Home **and** HA separately) vs *HA-bridged* (device is
  cloud/local-only → add to HA, then expose to Siri via HA's HomeKit Bridge).
- **Level Lock+ 2023 is the odd one out:** Bluetooth/HomeKit only (its Matter never
  shipped). HomeKit pairing is exclusive — keep these in Apple Home; do **not** try to
  put them in both at once.

---

## 1. Subnet assignment — the whole fleet

Legend for **Connectivity**: `Wi-Fi 2.4` = 2.4 GHz only (onboard from a 2.4 GHz phone),
`Wi-Fi` = dual-band, `PoE` = wired, `Zigbee`/`Thread`/`BLE` = no IP of its own (rides a
hub/bridge — *not* on a VLAN directly).

### Trusted — VLAN 10 (`192.168.10.0/24`)

| Device | Qty | Connectivity | Why Trusted |
|---|---|---|---|
| HA Green | 1 | Wi-Fi / wired | The controller; needs to reach IoT (allowed) + sit with the Apple hubs |
| MacBook | 3 | Wi-Fi | Personal trusted computers |
| Desktop gaming PC | 2 | Wi-Fi | Personal; Sunshine host / Moonlight clients stay same-subnet |
| iPad | 2 | Wi-Fi | Personal Apple devices (also Home app remotes) |
| Steam Deck | 2 | Wi-Fi | Personal; Moonlight clients |
| Apple TV 4K | 2 | Wi-Fi / Eth | **HomeKit hub + Thread border router** — keep with HA |
| Apple HomePod | 3 | Wi-Fi | **HomeKit hub + Thread border router + AirPlay** — keep with HA |
| Nintendo Switch 2 | 1 | Wi-Fi | Console; open NAT for online play |
| Nintendo Switch OLED | 1 | Wi-Fi | Console; open NAT for online play |
| Nintendo DS | 2 | Wi-Fi 2.4 (legacy) | ⚠️ see §1.1 — original DS is **WEP-only** and may not join WPA2 |

### IoT — VLAN 20 (`192.168.20.0/24`)

| Device | Qty | Connectivity | Notes |
|---|---|---|---|
| Hue Bridge | 1 | Wired/Wi-Fi | Hosts all 50 bulbs over Zigbee; native HomeKit + HA |
| LG CX / C4 TV | 2 | Wi-Fi | AirPlay2/HomeKit-capable *and* webOS (HA local) |
| LG smart oven/range | 1 | Wi-Fi 2.4 | LG ThinQ (cloud) → HA |
| LG smart microwave | 1 | Wi-Fi 2.4 | LG ThinQ (cloud) → HA |
| Midea AC (U-shaped) | 4 | Wi-Fi 2.4 | Local via `midea_ac_lan` or ESPHome — see midea-local-setup.md |
| Midea Dehumidifier | 1 | Wi-Fi 2.4 | Local via `midea_ac_lan` |
| Emporia Vue 3 | 2 | Wi-Fi 2.4 (ESP32) | Flash ESPHome → fully local in HA |
| Tesla Model 3 | 1 | Wi-Fi | On Wi-Fi only at home; control is cloud (Fleet API) |
| Roborock QV 35S | 1 | Wi-Fi 2.4 | Newer Q-series protocol — see §4 caveat |
| iRobot Roomba i7+ | 1 | Wi-Fi 2.4 | Local push integration in HA |
| Nintendo Alarmo | 1 | Wi-Fi 2.4 | No HA integration; treat as a cloud appliance |

### Rides a hub — no VLAN/IP of its own

| Device | Qty | Rides | Lands on |
|---|---|---|---|
| Hue light bulb | 50 | Zigbee → Hue Bridge | IoT (via the bridge) |
| Level Lock+ 2023 | 2 | BLE/HomeKit → Apple hub | Apple Home only (see §3.3) |

### Cameras — VLAN 30 (`192.168.30.0/24`)

| Device | Qty | Connectivity | Notes |
|---|---|---|---|
| UniFi G5 Flex | 1 | PoE (or Wi-Fi) | Adopted in UniFi Protect; no internet (firewall rule #14) |
| UniFi G5 Turret Ultra | 1 | PoE | Adopted in UniFi Protect; no internet |

> For PoE cameras, set the VLAN on the **switch port** (USW-PoE-8) — tag the port to
> Network "Cameras" (native VLAN 30), no SSID involved. If a G5 Flex runs on Wi-Fi,
> join it to the camera/IoT SSID instead.

### Work — VLAN 40 (`192.168.40.0/24`)

| Device | Qty | Notes |
|---|---|---|
| Work MacBook Pro | 1 | Internet-only, isolated from all LAN (zone matrix) |

### Guest — VLAN 50 (`192.168.50.0/24`)

Nothing from this fleet — reserved for visitors. (Optionally drop the Nintendo DS here
if you stand up a legacy SSID; see §1.1.)

### 1.1 ⚠️ The Nintendo DS problem (read before assigning)

The **original DS / DS Lite supports WEP only** — it physically cannot join a WPA2/WPA3
SSID. A **DSi or 3DS** does WPA2 and can join Trusted normally. If yours are original
DS units you have three choices, in order of preference:
1. **Leave them off Wi-Fi** (local multiplayer still works). Simplest and safest.
2. Stand up a **dedicated, heavily-isolated legacy SSID** (WEP) mapped to the **Guest
   VLAN 50** — WEP is broken, so isolate it hard and expect only Nintendo WFC-era
   services (mostly dead anyway).
3. Skip — most original-DS online services are retired.

Do **not** drop WEP onto the Trusted or IoT SSID; it would weaken the whole network.

---

## 2. What actually needs an SSID (and which band)

You already created the SSIDs. Mapping reality:
- **Trusted SSID → VLAN 10**, **IoT SSID → VLAN 20**, **Guest → VLAN 50**, plus the
  wired Cameras/Work tags. Each SSID is bound to exactly one network/VLAN in UniFi.
- **Most IoT gear is 2.4 GHz-only** (every device tagged `Wi-Fi 2.4` above). Make sure
  the **IoT SSID broadcasts 2.4 GHz**, and during onboarding **put your phone on a
  2.4 GHz network too** — the #1 setup failure is a phone on 5 GHz trying to hand
  credentials to a 2.4 GHz-only device. If your IoT SSID is band-steered, temporarily
  add a 2.4 GHz-only onboarding SSID, or pin the phone to 2.4 GHz.
- Give every IoT device a **static DHCP lease** (UniFi → Client → Fixed IP) right after
  it joins. Local integrations (Midea `.json`, webOS, Roborock) key off a stable IP.

---

## 3. HomeKit + Home Assistant: the two patterns

Your goal — *keep HomeKit/Siri working **and** add to HA* — resolves to one of three
buckets per device. Decide the bucket, then follow the per-device steps in §4.

### 3.1 Pattern A — Native dual control (device speaks HomeKit itself)

The device is a real HomeKit accessory **and** has a separate local HA integration. Add
it to **both**, independently — they don't conflict.

- **Hue Bridge (+ all 50 bulbs):** add the bridge to **Apple Home** (native HomeKit) *and*
  to **HA → Philips Hue** (local). Both controllers talk to the same bridge happily.
- **LG CX / C4 TVs:** keep **AirPlay 2 + HomeKit** on in webOS (works with Siri/Apple
  Home) *and* add **HA → LG webOS** (local control: power-on needs Wake-on-LAN).

### 3.2 Pattern B — HA-bridged to Siri (device does NOT speak HomeKit)

The device is cloud- or LAN-only with no native HomeKit. Add it to **HA** via its
integration, then turn on **HA's HomeKit Bridge** so the entities appear in Apple Home
and respond to Siri. One bridge covers all of them.

Applies to: **Midea AC ×4, Midea Dehumidifier, Emporia Vue 3 ×2, LG oven & microwave,
Roborock QV 35S, Roomba i7+, Tesla** (and anything else non-HomeKit).

> Setup once: HA → Settings → Devices & Services → **+ Add Integration → HomeKit Bridge**
> → choose which domains/entities to expose (e.g. climate, switch, vacuum). They show up
> in Apple Home as a single bridge; Siri then controls them. Energy sensors (Emporia)
> have no useful HomeKit type — expose those only if you want them as Home sensors.

### 3.3 Pattern C — Exclusive HomeKit pairing (pick one ecosystem)

**Level Lock+ 2023** is Bluetooth/HomeKit only — its Thread radio never got the promised
Matter firmware. A HomeKit accessory can be paired to **only one** HomeKit fabric at a
time, so it can be in Apple Home **or** HA's HomeKit-Controller, not both.

- **Recommended:** keep both locks in **Apple Home** (Home Key, Siri, remote unlock via
  your HomePod/Apple TV hub). Accept that they won't appear in HA for now.
- If you *must* have them in HA: un-pair from Apple Home, add via **HA → HomeKit Device
  (Controller)**, then re-expose with HA's HomeKit Bridge — but you lose native Home Key
  UX. Not worth it. Revisit only if Level ever ships the Matter update for this model
  (then Matter multi-admin gives you both cleanly).

### 3.4 The Apple hubs themselves

**HomePods + Apple TVs** stay in Apple Home (they *are* the Siri/HomeKit hubs). Add each
**Apple TV to HA → Apple TV** for media/remote control. HomePods aren't "added" as
controllable devices, but HA can AirPlay/announce to them.

---

## 4. Per-IoT-device onboarding (step by step)

Each block: **join the network → static lease → add to HA → HomeKit/Siri**. All IoT
devices below land on **VLAN 20 / IoT SSID**, 2.4 GHz, with HA reaching them from Trusted
(Trusted→IoT is allowed; the mDNS proxy + firewall rules #2/#4 handle discovery).

### 4.1 Hue Bridge + 50 bulbs  — *Pattern A*
1. Plug the **Hue Bridge** into the network on the **IoT** VLAN (Ethernet to an IoT-tagged
   port, or its own static lease). Bulbs pair to the bridge over Zigbee — they never touch
   Wi-Fi.
2. Give the bridge a **static lease** on `192.168.20.x`.
3. Apple Home: open **Home app → Add Accessory → Hue Bridge**, press the bridge button.
4. HA: **Settings → Devices & Services → + Add → Philips Hue**, press the button. All 50
   bulbs import as entities. (Both controllers now run in parallel, fully local.)
5. mDNS: ensure the IoT *and* Trusted VLANs both have the **Gateway mDNS Proxy ON** so the
   Apple hubs on Trusted see `_hap._tcp` on IoT (mdns-multicast-checklist.md).

### 4.2 LG CX / C4 TVs  — *Pattern A*
1. Join each TV to the **IoT SSID**; set a **static lease**.
2. In webOS: **Home Dashboard → Home Settings → Apple AirPlay & HomeKit** → enable both,
   then add the TV in **Apple Home** when prompted.
3. HA: **+ Add → LG webOS Smart TV**, enter the IP, accept the on-screen pairing prompt.
4. To power the TV *on* from HA/Home, enable **"Listen for Wake on LAN"** in the webOS
   network settings (TVs ignore network wake when fully off otherwise).

### 4.3 Midea AC ×4 + Dehumidifier  — *Pattern B*
Follow **[`midea-local-setup.md`](../homeassistant/midea-local-setup.md)** — summary:
1. Join each unit to the **IoT SSID** (2.4 GHz; phone on 2.4 GHz during the Midea-app
   pairing). Static lease each.
2. AC units: prefer **Path B (SLWF-01Pro ESPHome dongle)** for a guaranteed cloud-free
   future; the dehumidifier uses **Path A (`midea_ac_lan`)**.
3. HA: add **midea_ac_lan** (HACS) or **ESPHome**; for V3 units do the one-time cloud
   handshake.
4. **Immediately back up `/config/.storage/midea_ac_lan/<id>.json` off the HA box** — the
   single most important step (Midea is retiring the token APIs).
5. Siri: expose the climate entities via **HA HomeKit Bridge**.

### 4.4 Emporia Vue 3 ×2  — *Pattern B (energy)*
1. Join to the **IoT SSID** as shipped (or skip straight to flashing).
2. **Flash ESPHome** (Emporia Vue 3 is an ESP32) using the community Emporia-Vue ESPHome
   project → device reports **locally** to HA, no Emporia cloud.
3. HA auto-discovers via **ESPHome**; static-lease it.
4. Wire the CT clamps per Emporia's guide, then feed the phase/circuit sensors into
   **HA → Energy dashboard**. (HomeKit has no real energy type — leave off the bridge.)

### 4.5 LG smart oven/range + microwave  — *Pattern B*
1. Join each to the **IoT SSID** (2.4 GHz) via the **LG ThinQ** app; static lease.
2. HA: **+ Add → LG ThinQ** (cloud-polled). Expose the useful entities (status, timers).
3. Siri via **HA HomeKit Bridge**. (Safety: ranges generally expose status/monitoring,
   not remote-start — by design.)

### 4.6 Roborock QV 35S  — *Pattern B, with a caveat*
1. Join to the **IoT SSID** (2.4 GHz) via the Roborock app; static lease.
2. HA: try **+ Add → Roborock** first. The **newer Q-series protocol may not be supported**
   by the native integration — if it fails:
   - use the device's **Matter** support (basic start/stop/return) if present, **or**
   - the community cloud-based Roborock integration as a fallback.
3. Local polling uses **port 58867** — already covered by Trusted→IoT allow.
4. Siri via **HA HomeKit Bridge** (vacuum entity).

### 4.7 iRobot Roomba i7+  — *Pattern B*
1. Join to the **IoT SSID** (2.4 GHz) via the iRobot app; static lease.
2. HA: **+ Add → iRobot Roomba and Braava** — needs the robot's **BLID + password**
   (HA can fetch it during the on-dock pairing flow). Local push thereafter.
3. Siri via **HA HomeKit Bridge**.

### 4.8 Tesla Model 3  — *Pattern B (cloud)*
1. The car uses your **home Wi-Fi only for OTA/parked data** — join it to the **IoT SSID**
   when parked (Controls → Wi-Fi). Control is via Tesla's **Fleet API**, not the LAN.
2. HA: add the **Tesla Fleet** integration (or a community option like Tessie/Teslemetry)
   with your Tesla account. No local lease needed for control.
3. Siri via **HA HomeKit Bridge** (lock, climate, charge switches). Keep automations
   conservative — cloud latency + vampire drain.

### 4.9 Nintendo Alarmo  — *no HA integration*
1. Join to the **IoT SSID** (2.4 GHz); static lease; it phones home to Nintendo only.
2. No HA/HomeKit integration exists — leave it standalone on IoT. (If you later want
   presence/alarm signals in HA, that's a future reverse-engineering project, not today.)

---

## 5. The migration helper

This is the missing piece: a **repeatable order + a tracking matrix** so you can move the
fleet without breaking HomeKit mid-flight. Work in waves; finish a wave before the next.

### 5.1 Pre-flight (do today, before moving any device)

- [ ] **Back up the UniFi config** (Settings → System → Backups → *Settings Only*) — ZBF
      changes are a one-way door.
- [ ] **mDNS proxy ON for Trusted *and* IoT**; **IGMP snooping OFF**; check WiFi
      *Multicast Filtering* (mdns-multicast-checklist.md). Do this **before** migrating
      Apple gear or casting/HomeKit will look broken.
- [ ] Confirm firewall policies **#2 (Trusted→IoT)** and **#4 (mDNS control ports)** exist
      and the camera internet-block (#14) is in place (firewall-policy-order.md).
- [ ] **Set up the HA Green** (arriving today): power on, onboard at `http://homeassistant.local:8123`,
      give it a **static lease on VLAN 10**, update OS/Core, install **HACS**, and add the
      **Matter Server** add-on (future-proofing for Matter devices).
- [ ] Verify an **IoT 2.4 GHz onboarding path** exists and a phone can sit on 2.4 GHz.

### 5.2 Migration order (waves)

1. **Wave 0 — Apple hubs first.** Move **HomePods + Apple TVs to Trusted**. Confirm Apple
   Home still shows "Connected" hubs and Siri works. (Everything else depends on the hubs
   being healthy on the right subnet.)
2. **Wave 1 — Infrastructure.** Hue Bridge → IoT. Cameras → Cameras VLAN (switch ports).
   Add Hue to Apple Home + HA. This gives you an immediate, low-risk win.
3. **Wave 2 — Native-HomeKit endpoints.** LG TVs → IoT; enable AirPlay/HomeKit; add webOS
   to HA. Verify casting/AirPlay from a Trusted phone (tests the mDNS proxy end-to-end).
4. **Wave 3 — HA-bridged climate/energy.** Midea ×5, Emporia ×2, LG oven/microwave → IoT;
   integrate in HA; **back up Midea `.json` immediately**; stand up the **HA HomeKit
   Bridge** and confirm Siri sees them.
5. **Wave 4 — Robots + car + misc.** Roborock, Roomba, Tesla, Alarmo → IoT; integrate;
   add to the HomeKit Bridge.
6. **Wave 5 — Locks + clients.** Confirm **Level Lock+** still healthy in Apple Home (no
   change). Move **MacBooks/iPads/PCs/consoles → Trusted**, **Work MacBook → Work**,
   **DS → decision per §1.1**.
7. **Wave 6 — Verify & tighten.** Run the §6 checklist; scope firewall rules #2–#4 from
   `any` down to the real ports; delete any ZBF migration duplicate policies.

### 5.3 Per-device migration matrix (the tracker)

Status legend: ☐ not started · ◐ on network · ✅ in HA · 🍎 in Apple Home/Siri · 🔒 `.json`/creds backed up.

| Device | Target VLAN | SSID / Port | Static lease | HA integration | HomeKit path | Backup | Status |
|---|---|---|---|---|---|---|---|
| HomePod ×3 | Trusted 10 | Trusted SSID | — | (hub) | Apple Home (hub) | — | ☐ |
| Apple TV 4K ×2 | Trusted 10 | Trusted SSID | yes | Apple TV | Apple Home (hub) | — | ☐ |
| HA Green | Trusted 10 | Trusted/wired | yes | — (is HA) | — | config backup | ☐ |
| Hue Bridge | IoT 20 | IoT/wired | yes | Philips Hue | A: native HomeKit | — | ☐ |
| Hue bulbs ×50 | (Zigbee) | via bridge | — | via bridge | via bridge | — | ☐ |
| LG CX/C4 TV ×2 | IoT 20 | IoT SSID | yes | LG webOS | A: AirPlay/HomeKit | — | ☐ |
| Midea AC ×4 | IoT 20 | IoT 2.4 | yes | midea_ac_lan/ESPHome | B: HA bridge | 🔒 `.json` | ☐ |
| Midea Dehumidifier | IoT 20 | IoT 2.4 | yes | midea_ac_lan | B: HA bridge | 🔒 `.json` | ☐ |
| Emporia Vue 3 ×2 | IoT 20 | IoT 2.4 | yes | ESPHome (flash) | (energy; off bridge) | — | ☐ |
| LG oven/range | IoT 20 | IoT 2.4 | yes | LG ThinQ | B: HA bridge | — | ☐ |
| LG microwave | IoT 20 | IoT 2.4 | yes | LG ThinQ | B: HA bridge | — | ☐ |
| Roborock QV 35S | IoT 20 | IoT 2.4 | yes | Roborock/Matter/cloud | B: HA bridge | — | ☐ |
| Roomba i7+ | IoT 20 | IoT 2.4 | yes | iRobot Roomba | B: HA bridge | 🔒 BLID+pw | ☐ |
| Tesla Model 3 | IoT 20 | IoT (parked) | n/a | Tesla Fleet | B: HA bridge | 🔒 token | ☐ |
| Nintendo Alarmo | IoT 20 | IoT 2.4 | yes | none | none | — | ☐ |
| Level Lock+ ×2 | (BLE) | via Apple hub | — | (none — see §3.3) | C: Apple Home only | — | ☐ |
| UniFi G5 Flex | Cameras 30 | PoE/Wi-Fi | yes | (Protect; opt. HA) | — | — | ☐ |
| UniFi G5 Turret Ultra | Cameras 30 | PoE | yes | (Protect; opt. HA) | — | — | ☐ |
| MacBook ×3 | Trusted 10 | Trusted SSID | opt. | — | — | — | ☐ |
| iPad ×2 | Trusted 10 | Trusted SSID | opt. | — | (Home remote) | — | ☐ |
| Gaming PC ×2 | Trusted 10 | Trusted SSID | opt. | — | — | — | ☐ |
| Steam Deck ×2 | Trusted 10 | Trusted SSID | opt. | — | — | — | ☐ |
| Switch 2 / OLED | Trusted 10 | Trusted SSID | opt. | — | — | — | ☐ |
| Nintendo DS ×2 | see §1.1 | legacy/none | — | — | — | — | ☐ |
| Work MacBook Pro | Work 40 | Work SSID | — | — | — | — | ☐ |

### 5.4 Gotchas that bite during migration

- **Re-pair, don't just re-IP.** Many IoT devices bind to the SSID/subnet they were set up
  on. Moving them to the IoT SSID usually means a **factory reset + fresh app onboarding**,
  not just a Wi-Fi switch. Budget for it.
- **Phone band mismatch** is the top failure — phone on 5 GHz can't provision a 2.4 GHz
  device. Pin to 2.4 GHz for §4.3–4.9.
- **Don't reflect Matter** across VLANs (don't add `_matter._tcp`/`_matterc._udp` to the
  mDNS proxy). Keep Matter/Thread with HA on Trusted — that's why the Apple hubs moved.
- **Midea token APIs are closing** — back up each `.json` the moment the device is added.
- **Cameras block-internet rule** can break NTP/cloud adoption flows; adopt in Protect
  first, then apply the no-internet rule.

---

## 6. Post-migration verification

- [ ] From a **Trusted** phone: Apple Home shows hubs **Connected**; Siri locks/unlocks a
      Level Lock+; AirPlay to a HomePod (same VLAN) and to an **LG TV on IoT** (proves the
      mDNS proxy + firewall control rule).
- [ ] HA dashboard shows **every IoT device online**; toggle a Hue scene, a Midea AC, the
      Roomba — confirm local/cloud control works.
- [ ] **HomeKit Bridge** in Apple Home exposes the Pattern-B devices; Siri controls one of
      each (climate, vacuum).
- [ ] `./scripts/network/zbf-isolation-verify.sh` from an IoT client: **cannot** reach a
      Trusted host; **can** reach DNS/Internet. Camera client: **cannot** reach Internet.
- [ ] Midea `.json` files + Roomba BLID + Tesla token are stored **off the HA box**.
- [ ] Reduce firewall rules #2–#4 from `any` to the real service ports; delete ZBF
      migration duplicates.

---

## Authoritative docs

- Zone-Based Firewalls in UniFi — https://help.ui.com/hc/en-us/articles/115003173168-Zone-Based-Firewalls-in-UniFi
- UniFi Gateway mDNS Proxy — https://help.ui.com/hc/en-us/articles/12648701398807-UniFi-Gateway-Multicast-DNS-mDNS-Proxy
- HA HomeKit Bridge — https://www.home-assistant.io/integrations/homekit/
- HA Matter — https://www.home-assistant.io/integrations/matter/
- HA Philips Hue — https://www.home-assistant.io/integrations/hue/
- HA LG webOS TV — https://www.home-assistant.io/integrations/webostv/
- HA Roborock — https://www.home-assistant.io/integrations/roborock/
- HA Roomba — https://www.home-assistant.io/integrations/roomba/
- Emporia Vue 3 + ESPHome — https://digiblur.com/2025/03/14/how-to-esphome-emporia-vue-gen3-esp32-home-assistant/
- Level Lock+ (HomeKit/Home Key, no Matter on 2023 model) — https://sixcolors.com/post/2024/01/review-level-lock-brings-apple-home-key-support-to-the-stealth-smart-lock/
- Midea local control — see [`../homeassistant/midea-local-setup.md`](../homeassistant/midea-local-setup.md)
