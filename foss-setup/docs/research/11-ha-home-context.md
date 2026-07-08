# 11 — Home Assistant: house context, device inventory & migration plan (2026-07-08)

Canonical reference for the smart-home build (Run 5). The tracker tasks (`ha-*`, `fut-*`) point
here for the "why". Keep this updated as devices are added.

## House profile

- **71 Culver Rd, Rochester NY 14620** — built 1910, two finished floors, unfinished dormer
  attic, unfinished basement.
- **Heat:** central boiler → cast-iron radiators (basement furnace room). **No central cooling** —
  4 Midea window/portable ACs cover summer. Thermostat at the boiler circuit (Nest 3rd gen
  installed today; **ecobee Smart Thermostat Premium new-in-box** replaces it — see ha-06).
- **Cooling/damp reality:** Rochester winters = freeze/pipe risk in attic + porches; 1910
  basement = damp (Midea dehumidifier) and a real **radon** candidate. Laundry room, water
  heater, furnace in basement — all leak/failure monitoring targets.
- **Internet:** Greenlight fiber, ISP-controlled modem → **UDM Dream Wall** (GUI-only for
  agents), 2 UniFi APs, 1 switch, 2 UniFi Protect cameras on the UDM.
- **Network:** VLANs/zones already built (net-00..06 done): Trusted / IoT / Guest / Work +
  mDNS reflection. **IoT devices have NOT yet been moved** onto the IoT SSID/VLAN — that
  migration is ha-19.

## Rooms (canonical) vs HA areas

Floors + areas were created/renamed in HA on 2026-07-08 (registry work, reversible).
HA state: 4 floors, areas below. **Bold = needs the human's answer** (which physical room is it?).

| Floor | Canonical room | HA area today | Notes |
|---|---|---|---|
| Basement | Laundry Room | Laundry Room (new, empty) | "Basement" area still holds 11 lights to redistribute |
| Basement | Gym | Gym (new, empty) | |
| Basement | Storage Room | Storage Room (new, empty) | |
| Basement | — | Basement (11 lights) | dissolve after lights are sorted into the 3 rooms above |
| First | Bathroom | Bathroom (renamed from First Floor Bathroom) | bathtub light moved back here from Kitchen (was misassigned) |
| First | Kitchen | Kitchen | |
| First | Entertainment Room | Entertainment Room (renamed from Living Room) | |
| First | Dining Room | Dining Room (renamed from Dining) | |
| First | Office | Office | Elgato lights live here |
| First | Front Porch | Front Porch | |
| First | Mud Room | Mud Room (renamed from Mudroom) | |
| First | First Floor Hallway | First Floor Hallway (renamed from Downstairs Hallway) | |
| First | Back Porch | Back Porch | |
| Second | Master Bedroom | Master Bedroom (renamed from Bedroom) | |
| Second | Kaelyn Lounge | **Lounge or Guest Bedroom?** | human answer → rename |
| Second | Brandon Lounge | **Lounge or Guest Bedroom?** | human answer → rename |
| Second | Kaelyn Bathroom | **Master Bathroom or Upstairs Bathroom?** | human answer → rename |
| Second | Cats Bathroom | **Master Bathroom or Upstairs Bathroom?** | human answer → rename |
| Second | Upstairs Hallway | Upstairs Hallway | |
| Attic | Attic | Attic | 9 lights |

## Device inventory → integration map

"Local?" = can run with internet blocked. "WAN" = firewall policy for the device on the IoT
VLAN once migrated (**block** = add to the no-internet group; **allow** = needs its cloud).

| Device | Model | HA integration | Local? | WAN | VLAN | Task |
|---|---|---|---|---|---|---|
| Hue Bridge + 45+ lights | Hue Bridge v2 (id ecb5fa99b37d) | `hue` — **already integrated** | yes | block (lose out-of-home Hue app; HA remote access replaces it) | IoT (wired) | ha-05 |
| Door locks ×2 (front/back) | Level Lock+ (C-L18U, 2023) | **none — stays Apple-native** (HomeKit BLE + Home Key). Pairing to HA would steal them from Apple Home and kill Apple Wallet Home Key. Revisit if Level ships Matter for this model. | n/a (BLE) | n/a | n/a | ha-20 |
| Thermostat (installed) | Nest Learning 3rd gen (T3016US) | none — **being replaced**; SDM cloud path (old ha-06) dropped | no | — | — | ha-06 |
| Thermostat (new in box) | **ecobee Smart Thermostat Premium** | `homekit_controller` — **fully local**, plus built-in air quality + occupancy + works natively with Siri | **yes** | block after setup (optional: allow for ecobee app/updates) | IoT | ha-06 |
| Dehumidifier | Midea cube (B0866XLRTX) | `midea_ac_lan` (HACS) now; ESPHome SLWF-01Pro dongle = cloud-free end-state | mostly | allow until dongle swap, then block | IoT | ha-07/08 |
| Window ACs ×4 | Midea U-shaped | `midea_ac_lan` (HACS); same dongle option | mostly | allow → block | IoT | ha-07/08 |
| Robot vacuum | Roborock QV 35S | `roborock` (core) — cloud account for setup/maps, local MQTT for control | partial | allow | IoT | ha-21 |
| Robot vacuum | iRobot Roomba i7+ | `roomba` (core) — local after BLID/password capture | yes | allow initially (app/firmware), then try block | IoT | ha-22 |
| TVs | LG CX + C4 (webOS) | `webostv` + `wake_on_lan` — local | yes | block (kills ads/telemetry; allow temporarily for firmware/app updates; pinhole to Plex on mini/NAS needed) | IoT | ha-23 |
| Soundbar + rears | Samsung HW-Q80R + SWA-9000S | optional `smartthings` (cloud); works fine dumb over HDMI-ARC | no | off-network preferred | — | ha-23 (note) |
| Range + microwave | LG ThinQ | `lg_thinq` (core, cloud) — status/alerts only, low value | no | allow | IoT | ha-24 |
| Apple TVs ×2 | Apple TV | `apple_tv` — local (media control, automation triggers) | yes | allow (it's an Apple box; also Apple Home hub) | **Trusted** | ha-25 |
| HomePods ×3 | HomePod | `apple_tv` (AirPlay targets for TTS/announcements); Apple Home hubs for HomeKit Bridge | yes | allow | **Trusted** | ha-25 |
| Air fryer | COSORI Pro III | `vesync` (core, cloud) | no | allow | IoT | ha-26 |
| Energy monitor | Emporia Vue Gen 3 | `emporia_vue` HACS (cloud) now → **ESPHome flash later = local** (Vue 3 is ESP32-based; UART flash documented by community) | after flash | allow → block after flash | IoT | ha-27 |
| Smart scale | Withings Body Cardio | `withings` (core, cloud OAuth) — health data stays in Withings/Apple Health either way | no | allow | IoT | ha-28 |
| BP monitor | Withings BPM Connect | `withings` (same OAuth app) | no | allow | IoT | ha-28 |
| Key lights ×2 | Elgato Key Light | `elgato` — **already integrated**, fully local | yes | block | IoT (or Trusted w/ Mac) | done |
| Indoor garden | Edn SmallGarden | none exists (cloud app only). Treat as dumb; optional smart plug for energy/schedule visibility | no | allow (its app) or leave | IoT | ha-29 |
| Cameras ×2 | UniFi Protect (on UDM) | `unifiprotect` — local; needs a **local-access admin** user on the UDM (vault: unifi_protect.*, currently empty) | yes | n/a (UDM) | existing | ha-14 |
| Phones | iPhones | `mobile_app` — Brandon's already connected ("Btiphone"); add Kaelyn's | yes | — | Trusted | ha-13 |

**Architecture for Siri (the household keeps iPhones/HomePods):** HA is the single hub; the
**HomeKit Bridge** (ha-16) exposes a *curated* set of HA entities to Apple Home, where the
HomePods act as Apple Home hubs. Siri keeps working for everything HA owns. The one exception:
the Level locks stay paired directly to Apple Home (Home Key tap-to-unlock requires it) — HA
does not manage them in v1.

## IoT network policy (ha-19)

VLANs and zone firewall already exist. Migration = re-provisioning each WiFi device onto the
IoT SSID (human, per-device app work) + wiring the Hue bridge to an IoT-tagged port. Then, in
UniFi, two device groups inside IoT:

1. **iot-local (no WAN):** Hue bridge, Midea units (after ESPHome swap), LG TVs, Elgato,
   ecobee (optional), Roomba (trial), Emporia (after flash) — traffic to internet dropped;
   only DNS/DHCP/NTP to gateway + established return traffic.
2. **iot-cloud (WAN allowed):** Roborock, ThinQ, VeSync, Withings, Edn, Emporia+Midea until
   their local paths land.

Pinholes: IoT → mini:32400 + NAS:32400 (Plex for TVs); mDNS reflection already on (net-06).
HA stays single-homed on Trusted (per master plan §1) and reaches IoT via Trusted→IoT allow.

## Shopping list — v1.0 sensor/actuator fill-in (local-first, AliExpress-friendly)

Backbone first (ha-12): **Sonoff ZBDongle-E** (~$20) + USB-2 extension + Mosquitto + Zigbee2MQTT.
Everything below is Zigbee (or ESPHome/WiFi-local) — zero cloud, works during internet outages.

| Qty | Item | ~$ | Where / why |
|---|---|---|---|
| 10 | Sonoff SNZB-02P temp/humidity | $9 ea | one per key room (per-room climate; drives AC/dehumidifier/radiator automations) |
| 6 | Tuya Zigbee water-leak sensors | $8 ea | laundry, water heater, boiler, kitchen sink, both bathroom supply lines |
| 6 | Sonoff SNZB-04P door/window contacts | $7 ea | front/back/mud doors; window-open-while-heating alerts |
| 4 | Sonoff SNZB-03P PIR motion | $8 ea | hallways, porches, storage |
| 2 | Tuya ZY-M100-24G mmWave presence | $18 ea | office + lounges (seated stillness ≠ absence, unlike PIR) |
| 8 | Zigbee smart plugs w/ energy metering (Tuya/Sonoff S31ZB) | $10 ea | Edn garden, fans, humidifier, entertainment standby, holiday lights |
| 3 | Sonoff SNZB-01P / IKEA Rodret buttons | $8 ea | scene control; also the fix for "wall switch kills Hue bulb power" |
| 2 | Sonoff ZBMINIL2 (no-neutral relay) | $13 ea | 1910 wiring rarely has neutrals — these fit behind existing switches for non-Hue fixtures |
| 2 | Apollo AIR-1 (ESPHome: CO2/PM2.5/VOC/temp/hum) | $90 ea | basement gym + first floor; open-source, fully local |
| 1 | RadonEye RD200 | $180 | basement radon — local BLE, native HA integration (1910 Rochester basement = test it) |
| 1 | Heiman/frient Zigbee CO detector | $30 | boiler + water heater room (combustion appliances) |
| 1 | Heiman Zigbee smoke detector | $25 | laundry/boiler room supplement |
| 4 | ESP32 dev boards (ESPHome Bluetooth proxies) | $6 ea | extends BLE coverage: RadonEye, future BLE sensors, Bermuda room-presence |
| 2 | Tuya Zigbee soil-moisture sensors | $10 ea | houseplants now; grow tent later |

≈ **$550 total.** Deliberately excluded: WiFi Tuya gear (cloud-locked), Aqara-only-hub gear,
anything needing a vendor app to function.

**Smart shades (pitched, optional):** Zemismart Zigbee roller-shade motors (~$70/window) or
retrofit chain drivers from AliExpress (~$45) — pilot one in the Master Bedroom (sunrise-open
automation) before committing the house.

**Radiators (investigate before buying):** Zigbee TRVs (Sonoff TRVZB, ~$25) give per-room
radiator control **only if** the system is hot-water with per-radiator valves that take M30
adapters. If it's single-pipe steam, TRVs don't apply — per-room control then = smart vent
covers or just the ecobee + room sensors. → ha-30 includes a "identify radiator system type"
step.

## Opportunities pitched (beyond the asked-for list)

1. **Freeze sentinel** — temp sensors in attic + porch pipe runs + leak sensor at the boiler;
   alert + boiler-runtime check when any room < 45°F. The single highest-value automation for
   a 1910 Rochester house.
2. **Boiler analytics** — ecobee runtime + Emporia circuit → heating degree-day efficiency
   trend; catches a failing boiler/thermocouple before it dies in January.
3. **Laundry-done notifications** — Emporia circuit-level detection (dryer is 240V, washer via
   plug or circuit); no smart appliances needed.
4. **Cats Bathroom air automation** — AIR-1 VOC spike (litter) → smart-plug exhaust fan.
5. **Bermuda room-level presence** — the $6 ESP32 proxies + iPhones/Watches = "which room is
   each person in", enabling follow-me lights/audio without wearables or cameras.
6. **Winter humidity balance** — radiator heat = bone-dry air; humidifiers on metered plugs
   driven by the per-room sensors (target 35-45% RH).
7. **Window-open-while-heating** — contact sensors + ecobee → nag or setback.
8. **Whole-home energy dashboard** (ha-10) — Emporia circuits + per-plug metering; find
   phantom loads.
9. **Water-main auto-shutoff** (later, ~$150-400) — motorized ball valve driven by the leak
   sensors; turns "alert" into "prevented flood". Good year-2 add.
10. **Local voice** (ha-09) — HA Voice PE (~$59) gives fully-local voice as Siri fallback;
    pairs with LiteLLM/Ollama already running on the rig.
11. **Frigate on the NAS** (ha-15) — package/person/animal detection on the existing Protect
    cameras, local.
12. **Mailbox/package sensor** — contact sensor on the porch mailbox + Protect person event.

## Future projects (2-5 yr) — tracked as fut-01..fut-06 (Run 7)

| id | Project | Local-first approach |
|---|---|---|
| fut-01 | Outdoor garden watering | **OpenSprinkler** (open hardware/source, native HA) or ESPHome + irrigation valves; avoid B-hyve/Rachio cloud |
| fut-02 | Solar (incl. NY plug-in/balcony legislation) | plug-in microinverter kit; monitor via Emporia CTs (already owned) so production data stays local regardless of inverter cloud |
| fut-03 | DIY weather station | **Ecowitt** gateway (local API, native HA) or rtl_433 SDR on the mini picking up 915MHz sensors |
| fut-04 | Hobbyist mesh network (citywide, non-ISP) | **Meshtastic** (LoRa) node(s) + MQTT bridge into HA; check Rochester-area mesh communities |
| fut-05 | Sump pump w/ smart monitoring | pump on Emporia circuit + ESPHome ultrasonic water-level in the pit + Zigbee leak ring + runtime/failure alerts; ties into freeze sentinel |
| fut-06 | Smart grow tent | VIVOSUN's controller is Tuya-cloud — prefer ESPHome-built controller (temp/RH/VPD + plugs for light/fan) or accept localtuya wrangling; soil sensors from shopping list |

## Open questions for the human (blocking small pieces)

1. Room mapping: which of HA's "Lounge"/"Guest Bedroom" is Kaelyn's vs Brandon's Lounge?
   Which of "Master Bathroom"/"Upstairs Bathroom" is Kaelyn's vs the Cats'?
2. Which basement lights (11 in the "Basement" area) belong to Laundry/Gym/Storage?
3. Radiator system: steam or hot water? (photo of a radiator valve + the boiler answers it)
4. IoT SSID name as created in net-02 (needed for per-device migration instructions).
