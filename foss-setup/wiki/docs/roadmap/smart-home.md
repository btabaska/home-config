# Roadmap — smart-home

38 task(s). Status mirrors `docs/progress.json` (the source of truth).

| Task | Title | Status | Effort |
|---|---|---|---|
| `fut-01` | Garden watering: OpenSprinkler (or ESPHome valves) — local irrigation | ⏸️ deferred | weekend |
| `fut-02` | Plug-in solar (NY legislation) + local production monitoring | ⏸️ deferred | weekend+ |
| `fut-03` | DIY weather station (local) | ⏸️ deferred | day |
| `fut-04` | Meshtastic node(s): hobbyist LoRa mesh, non-ISP comms | ⏸️ deferred | day |
| `fut-05` | Sump pump with smart monitoring | ⏸️ deferred | half day |
| `fut-06` | Grow tent, local-first (not VIVOSUN cloud) | ⏸️ deferred | weekend |
| `ha-01` | HA platform: HA Green (purchased — decision landed) | ✅ done | 5 min |
| `ha-02` | Set up HA Green (purchased — primary path) | ✅ done | 15 min |
| `ha-03` | Install HAOS in a KVM/libvirt VM (alternative path) | 🗑️ retired | 30-45 min |
| `ha-04` | Install HACS (community store) | ⬜ open | 15 min |
| `ha-05` | Add Philips Hue (local LAN via Hue Bridge) | ✅ done | 10 min |
| `ha-06` | Thermostat: install ecobee Premium (in box) — local HomeKit control; retire Nest SDM plan | ⬜ open | 45-60 min |
| `ha-07` | Add Midea AC + dehumidifier via midea_ac_lan (local) — and BACK UP the .json | ⬜ open | 30 min |
| `ha-08` | (Optional) Replace Midea OEM dongle with ESPHome SLWF-01Pro (cloud-free) | ⏸️ deferred | 30 min/unit |
| `ha-09` | Set up local voice (Assist + Whisper + Piper); LLM agent via LiteLLM (ha-17) | ⬜ open | 30-45 min |
| `ha-10` | Configure the Energy dashboard | ⬜ open | 20 min |
| `ha-11` | Configure HA backups to NAS and SAVE the encryption key | ✅ done | 30 min |
| `ha-12` | Zigbee backbone: Mosquitto + Zigbee2MQTT + USB coordinator | ⬜ open | 45-60 min |
| `ha-13` | Presence detection: HA Companion app + room-level (mmWave/Bermuda) | ⏸️ deferred | 30 min |
| `ha-14` | Bring UniFi Protect cameras into Home Assistant (local, no subscription) | ⬜ open | 30 min |
| `ha-15` | (Optional) Frigate for better local camera AI (zones, package/animal/face) | ⏸️ deferred | 1-2 hrs |
| `ha-16` | Expose HA to Apple Home via the HomeKit Bridge (keep iPhones/Siri) | ✅ done | 20 min |
| `ha-17` | LiteLLM gateway + small always-on fallback model (resilience if the rig is down) | 🗑️ retired | 45 min |
| `ha-18` | Rooms & floors: HA registry matches the real house | ⬜ open | 30 min |
| `ha-19` | IoT VLAN migration: move every WiFi IoT device onto VLAN 20 + firewall groups | ⬜ open | 2-3 h over days |
| `ha-20` | Level Lock+ ×2: Apple Home now; trial HA pairing via BLE proxy after sensors arrive | ⏸️ deferred | 15 min |
| `ha-21` | Roborock QV 35S → HA (official integration) | ⬜ open | 20 min |
| `ha-22` | iRobot Roomba i7+ → HA (local BLID/password) | ⬜ open | 20 min |
| `ha-23` | LG CX + C4 TVs → webOS (local) + Wake-on-LAN; soundbar stays dumb | ⬜ open | 25 min |
| `ha-24` | LG ThinQ range + microwave (cloud — status/alerts only, optional) | ⏸️ deferred | 15 min |
| `ha-25` | Apple TVs ×2 + HomePods ×3 → HA media players (local) | ⬜ open | 20 min |
| `ha-26` | COSORI air fryer via VeSync (cloud, optional) | ⬜ open | 10 min |
| `ha-27` | Emporia Vue 3 → HA energy: cloud now, ESPHome flash = local end-state | ⬜ open | 30 min + later 2 h |
| `ha-28` | Withings Body Cardio scale + BPM Connect (cloud OAuth) | ⬜ open | 30 min |
| `ha-29` | Non-integratable devices policy: Edn SmallGarden, Samsung soundbar | ✅ done | 10 min |
| `ha-30` | Sensor rollout wave 1: Zigbee sensors, plugs, buttons (shopping list) | ⏸️ deferred | 1 day spread out |
| `ha-31` | Automations pack v1 (git-backed YAML) | ⬜ open | half day |
| `ha-32` | HA ops glue: SSH add-on, git-backed /config, nightly backups verify, checks.d/ha.yaml, Homepage | ⬜ open | 1 h |

[← Roadmap overview](index.md)
