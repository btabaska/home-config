# Hardware to buy

Mirror of `docs/hardware-shopping-list.md` — everything the roadmap still needs you to purchase, tagged to the [roadmap task](../roadmap/index.md) it unlocks. Source of truth is the repo file; keep them in sync.

---

Everything the roadmap still needs you to **buy**, compiled from the 2026-07-14
roadmap walk. Checkboxes to track as you purchase. Prices are rough (AliExpress /
Amazon 2026). Each item notes the task it unlocks. Nothing here is deployed until
bought + installed; software-only tasks are not listed.

Owned-already (no purchase): ecobee Premium thermostat (`ha-06`, in box), Emporia
Vue 3 ×2 (`ha-27`, on the breaker), Midea AC ×4 + dehumidifier (`ha-07`, reuse
existing WiFi modules), Roborock / Roomba / LG TVs / Withings / COSORI (their
integrations need no new hardware).

---

## Phase 1 — the smart-home backbone (small, unblocks the most)

- [ ] **Zigbee coordinator — Sonoff ZBDongle-E** (~$20) + a USB-2 extension cable (~$5) — **`ha-12`**. This one dongle is the gate for the entire sensor wave below.
- [ ] *(optional)* **HA Voice PE** (~$59) or **M5 Atom Echo** (~$13) for always-listening room mics — **`ha-09`**. Skip if the phone Companion app mic is enough.

## Phase 2 — sensor rollout wave 1 (`ha-30`, deferred; buy in stages)

**≈ $505 core / $865 all-in** (the AIR-1 ×2 + RadonEye are the premium $360). All local Zigbee/ESPHome, no cloud. Pair through Zigbee2MQTT once Phase 1 is in.

| ✓ | Qty | Item | ~Each | ~Total | For |
|---|---|---|---|---|---|
| [ ] | 10 | Sonoff SNZB-02P temp/humidity | $9 | $90 | per-room climate → AC/dehumidifier/radiator automations |
| [ ] | 6 | Tuya Zigbee water-leak | $8 | $48 | laundry, water heater, boiler, sink, bathroom supply lines |
| [ ] | 6 | Sonoff SNZB-04P door/window contact | $7 | $42 | doors + window-open-while-heating |
| [ ] | 4 | Sonoff SNZB-03P PIR motion | $8 | $32 | hallways, porches, storage |
| [ ] | 2 | Tuya ZY-M100-24G mmWave presence | $18 | $36 | office + lounges (stillness ≠ absence) |
| [ ] | 8 | Zigbee smart plugs w/ energy metering (S31ZB) | $10 | $80 | fans, humidifier, standby, holiday lights |
| [ ] | 3 | Sonoff SNZB-01P / IKEA Rodret buttons | $8 | $24 | scene control; "wall switch kills Hue" fix |
| [ ] | 2 | Sonoff ZBMINIL2 no-neutral relay | $13 | $26 | 1910 wiring w/o neutrals, behind existing switches |
| [ ] | 4 | ESP32 dev boards (ESPHome BLE proxies) | $6 | $24 | BLE coverage: RadonEye, Level locks (`ha-20`), room presence |
| [ ] | 2 | Tuya Zigbee soil-moisture | $10 | $20 | houseplants now; grow tent later |
| [ ] | 1 | Heiman/frient Zigbee CO detector | $30 | $30 | boiler + water-heater room |
| [ ] | 1 | Heiman Zigbee smoke detector | $25 | $25 | laundry/boiler supplement |
| | | **— core subtotal —** | | **≈ $505** | |
| [ ] | 2 | Apollo AIR-1 (CO2/PM2.5/VOC, ESPHome) | $90 | $180 | basement gym + first floor (premium) |
| [ ] | 1 | RadonEye RD200 | $180 | $180 | basement radon (1910 Rochester basement) (premium) |
| | | **— all-in total —** | | **≈ $865** | |

**Optional / investigate:** smart shades (Zemismart Zigbee ~$70/window or chain drivers ~$45); Zigbee TRVs (Sonoff TRVZB ~$25/radiator — **check radiator type first**: steam single-pipe → TRVs don't apply); water-main auto-shutoff motorized valve (~$150–400, good year-2 flood-prevention add).

## Phase 3 — resilience & optional

- [ ] **UPS for the NAS** (~$100–200, line-interactive 1000–1500VA, e.g. CyberPower/APC) — **`glue-01`**. The mini then reads it over NUT for graceful shutdown on outage. *(Deferred — budget.)*
- [ ] *(optional)* **Google Coral TPU** (~$60) for Frigate — **`ha-15`** *(deferred; the NAS iGPU can detect for free, and you judged UniFi Protect's built-in detection sufficient — only buy if you revisit Frigate).*

## Phase 4 — future projects (`fut-*`, 2–5 yr horizon, deferred)

- [ ] **`fut-01` garden watering** — OpenSprinkler controller (~$130) *or* ESPHome + latching solenoid valves (~$50).
- [ ] **`fut-02` plug-in solar** — balcony microinverter kit (~$300–800, sized to a circuit) — **gated on NY plug-in-PV legislation**; monitored via the owned Emporia.
- [ ] **`fut-03` weather station** — Ecowitt gateway + sensor array (~$80–150, native HA) *or* an rtl_433 USB SDR (~$30) on the mini.
- [ ] **`fut-04` Meshtastic** — LoRa node(s) (~$30–40 ea; e.g. Heltec/RAK), one attic-placed.
- [ ] **`fut-05` sump-pump monitor** — ESPHome ultrasonic level sensor (~$10) + a Zigbee leak sensor (from Phase 2) + a dedicated Emporia circuit (owned). ~$10 net.
- [ ] **`fut-06` grow tent** — ESPHome controller (~$30–50) + soil sensors + smart plugs (from Phase 2).
- [ ] *(optional)* **`retro-07` retro handheld** — e.g. AYN Thor Max (~$300+) — pure hobby, buy whenever.

---

### Rough budget roll-up
- **Get-started backbone (Phase 1):** ~$25 (just the Zigbee dongle).
- **Full sensor wave (Phase 2 core):** ~$505 · all-in with air-quality: ~$865.
- **Resilience (Phase 3):** ~$100–260.
- **Future (Phase 4):** highly variable, mostly $30–150 per project except solar.

_Source: the sensor list in `reference/home-assistant/home-context.md` (v1.0) + the 2026-07-14 roadmap walk. Update this file as you buy; the tasks stay `deferred` in `progress.json` until their hardware lands._