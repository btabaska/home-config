# 3. Smart home: Home Assistant

Home Assistant (HA) is the hub and a privacy win in itself: it pulls cloud-tethered devices into local control where possible, so lights and climate keep working even when Google's or Midea's servers don't.

> **Status (validated live 2026-07-14):** HA runs on **HA Green** at **v2026.6.4**, state RUNNING, reachable at `http://192.168.10.50:8123`. HA has **no SSH** (not a tailnet node) — drive it via REST/WS.

## How to run it (set-and-forget)

**Decision: HA Green — purchased.** The dedicated appliance was the right call for set-and-forget: plug-and-play, ~2-3 W, isolated, auto-updates, full add-on ("Apps") support. **⚠️ Corrected:** the plan lists "HAOS in a KVM/libvirt VM on the Ubuntu box" as the alternative — that path (`ha-03`) is **superseded/retired**; HA runs on Green hardware and the VM install is moot.

Whichever host: **never run HA on an SD card** (constant DB writes kill them — the Green uses eMMC, so you're fine) and avoid HA in plain Docker (you lose the add-on store + Supervisor). Back up to the NAS and **save the backup encryption key in your password manager** (you can't restore without it).

## Your devices

- **Hue → native, local.** HA's Hue integration talks to the Hue Bridge over the LAN — no cloud, rock solid. **Live:** 14 Hue light entities. Keep the bridge.
- **Nest → works, but fiddly.** "Works with Nest" is gone; HA uses Google's Smart Device Management (SDM) API — needs a Google Cloud project, the Device Access Console (one-time $5 fee), and OAuth. Works (thermostat + sensors) but routes through Google's cloud. Matter support for Nest *thermostats* has improved (4th-gen Nest Learning ships native Matter), but Matter thermostat control in HA can be feature-limited, so SDM remains the most complete path today.
- **Midea AC + dehumidifier → local, with a one-time handshake.** Use the **`midea_ac_lan`** HACS integration (actively maintained; also dehumidifiers) or **`midea-air-appliances-lan`**. V3-protocol devices need one connection to Midea's cloud to fetch a token/key, then run fully local. **Back up the per-device `.json` config files** — Midea has been closing its cloud token APIs, which can block *adding new* devices later.
  - **Fully cloud-free option (recommended):** replace the OEM WiFi dongle with an **ESPHome-flashable dongle** (e.g., SLWF-01Pro, ~$13) — severs the cloud, gives local ESPHome/MQTT control. **Status: deferred** (`ha-08`, optional — Midea is already controllable locally via `midea_ac_lan`, so this is a nice-to-have hardening).
  - Caveat: some Midea units built 2021+ use the Tuya platform (LocalTuya integration, not Midea). Check your model.

## Cameras — bring UniFi feeds into HA (and optionally Frigate)

- **HA native UniFi Protect integration (do this — easy win).** Fully local, no subscription; pulls live streams **and** UniFi's motion/smart-detection events into HA as entities (needs a Protect **API key** as of HA 2025.8, RTSP enabled per camera). Payoff is automation ("person detected after dark → hall light + notification"), camera tiles, recordings stay on the NVR.
- **Frigate (optional).** Ingests the same RTSP streams and adds *local* object detection UniFi doesn't (custom zones, package/animal/face detection, better snapshots). Needs a **Coral TPU (~$60)** or **Intel Quick Sync iGPU (OpenVINO)** + YAML. *Host on the NAS iGPU*, or the Mac mini with a Coral. **⚠️ Status: deferred** (`ha-15`) — **UniFi Protect's built-in detection is judged sufficient**, so Frigate is **not deployed**. (Scrypted is the bridge if you ever want the cameras in Apple Home / HomeKit Secure Video.) Keep cameras on the locked-down Cameras VLAN.

## Local sensors — the Zigbee backbone

Hue/Nest/Midea are WiFi/cloud-ish appliances. The cheap **local** sensors that drive real automations speak **Zigbee** — add a radio and a broker:

- **Coordinator:** one USB Zigbee stick — **Sonoff Zigbee 3.0 Dongle Plus-E** (~$20) or the official **Home Assistant Connect ZBT-2**. Use a short USB-2 extension to dodge USB-3 interference.
- **Zigbee2MQTT (recommended) or ZHA.** ZHA is the zero-extra-service built-in path; **Zigbee2MQTT** supports more devices and exposes everything over MQTT (handy once you add ESPHome/Midea-dongle devices). Either runs as an HA add-on.
- **Mosquitto** — the MQTT broker, required for Zigbee2MQTT *and* the ESPHome Midea dongle. Stand it up once as the shared bus (HA add-on).
- **Mesh tip:** every mains-powered Zigbee device (smart plug) is a router — aim for 5-7 around the house, pair close to the coordinator then move, and **avoid Aqara-branded hubs** to mix brands.
- *(Z-Wave is the optional second radio; Zigbee covers everything in the shopping list.)*

> **Status:** the sensor rollout (wave 1, ~$505-865 hardware) is **deferred** (`ha-30`, buy in stages — on the hardware shopping list). See Cheap local sensor shopping list.

## Presence detection

- **HA Companion app** (iOS/Android) gives free device-tracker presence + actionable notifications — install on every phone. Drives arriving/leaving automations.
- For **room-level** presence, add **mmWave** occupancy sensors or **Bermuda** (BLE trilateration via ESPHome Bluetooth-proxy ESP32s). **Status: deferred** (`ha-13`, needs hardware + placement).

## Keep iPhones working — HomeKit / Matter bridge

**HA's HomeKit Bridge** (built-in) exposes HA entities to **Apple Home**, so everyone keeps Siri and the Home app while HA does the real work. **Live:** the `HASS Bridge:21064` config entry is loaded (`ha-16` done). (`home-assistant-matter-hub` is the Matter alternative.) Expose a curated set of entities, not everything.

> **Open follow-up (`#4`):** HomePod ↔ HA HomeKit hub pairing — the gate is which VLAN the HomePods are on + mDNS-proxy/IGMP state (operator UI) + an on-device Apple Home add-hub check. See [Network](network.md).

## Tie-ins worth doing

- **Local voice (replaces Siri/Alexa):** HA's Assist pipeline + the Whisper/Piper add-ons gives local speech, with the conversation agent pointed at **Ollama on the rig**.
  - **⚠️ Corrected — the LiteLLM fallback is retired.** The plan proposed putting **LiteLLM** (a small OpenAI-compatible gateway) in front so HA targets one stable URL and falls back to a small always-on model on the mini. That design (`ha-17`) is **retired: the AI-stack single-point-of-failure — rig-only, no fallback — is an accepted decision.** LiteLLM was **never deployed on the mini** (a phantom; only orphaned `.env` leftovers remain). **Live reality:** HA uses the native `ollama` integration pointed **directly at the rig** (`192.168.10.12:11434`), conversation agent **`conversation.rig_ollama_assist`** (`llama3.2:3b`) — verified live 2026-07-14. A live `/api/conversation/process` returns real completions. The default pipeline stays on the intent engine to preserve device control. A rig outage is an *incident*, not a handled state; WoL remains recovery-only.
- **Node-RED — visual automations:** install the HA add-on once automations outgrow the built-in editor. Flows live in `/config` and ride the HA backup.
- **HA backups — concrete method + live status:** Settings → System → **Backups**. **✅ Live (queue item 02, `ha-11`):** a dedicated least-priv Synology SMB user `ha-backup` + Supervisor CIFS mount `nas_backups` → `//192.168.10.4/backups` (agent `hassio.nas_backups`); **daily 04:45 automatic ENCRYPTED backups to both the local eMMC agent and the NAS, retention 3**. Validated a triggered backup landed encrypted on the NAS as a listable 7-member archive (a real restore path). Key in vault `hosts.ha.backup_password` (+ Bitwarden). Also separately back up the Midea `.json` token files.
- **Energy dashboard:** with a smart plug / whole-home monitor, HA tracks per-device power — feeds the 24/7 power question in Power.
- HA on Trusted reaches Hue + Midea on IoT via the Trusted → IoT allow rule; no extra config beyond the mDNS settings in [Network](network.md).

---
[← index](index.md)
