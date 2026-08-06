# TODO — Going Analogue homelab

**The single todo list for this project.** Generated from `foss-setup/docs/tasks.json` (task definitions) + `foss-setup/docs/progress.json` (status) by `foss-setup/scripts/docs/gen-todo.py`. The wiki is the browsable mirror + the reference source of truth: <https://wiki.tabaska.us/roadmap/>. Re-run the generator after any change.

**291/386 done** · **61 open** · **19 deferred** · 15 retired.

---

## Open (remaining work)

### agent-handoff
- [ ] **`handoff-12`** Post-sprint cleanup — delete vault and rotate keys _(est 10 min)_

### books-cutover
- [ ] **`books-hc-upstream-swap`** Swap rreading-glasses-hc off the temporary local image once upstream fixes Hardcover batch limit (#574) _(est 15-30 min)_

### bug-intake
- [ ] **`bug-03`** Discord downtime reports for friends (game servers) → same triage pipeline _(est 3-4 h)_

### desktop
- [ ] **`foss-02`** Package the FOSS desktop suite: cachyos-desktop-suite.sh + macOS Brewfile (chezmoi-tracked) _(est ~half day)_
- [ ] **`glue-02`** Desktop baseline on CachyOS: browser(s) + LibreOffice (anytime) _(est 20-40 min)_

### docker-host
- [ ] **`fix-72`** Reconcile the etckeeper /etc repo so git-etckeeper-clean greens _(est <1 hr)_
- [ ] **`fix-74`** Perform the pending mini kernel reboot in a maintenance window _(est 1-3 hrs)_ — ⛔ gate: disruptive — mini reboot is a fleet-wide outage (Caddy/DNS/alerting plane); 4-7AM window + operator approval
- [ ] **`fix-80`** Commit the regenerated /opt/foss-setup manifests + clear clone drift _(est <1 hr)_

### ebook-mgmt
- [ ] **`ebook-06`** End-to-end ebook verification (Libreseerr → Betty → Readarr → CWA → Plex/Kobo) _(est 30-45 min)_

### gaming
- [ ] **`game-09`** Rig idle-power tuning (24/7 baseline) _(est 20-30 min)_
- [ ] **`retro-03`** Save/state sync mesh (Syncthing) _(est 60 min)_ — ⛔ gate: device pairing approvals
- [ ] **`retro-04`** SteamDeck: EmuDeck/RetroDeck wiring _(est 45 min)_ — ⛔ gate: on-device steps
- [ ] **`retro-06`** RetroAchievements + cheat DB _(est 30 min)_ — ⛔ gate: RA account USERNAME+PASSWORD for RetroArch login (distinct from the RomM API key) + an emulator installed first (retro-05 rig / retro-04 Deck)
- [ ] **`retro-08`** RomM RetroAchievements dashboard (view-only unlock %/hardcore stats) _(est ~15 min config)_ — ⛔ gate: operator RetroAchievements username

### local-ai-buildout
- [ ] **`lai-18`** Agent memory layer _(est 2-4 hrs)_
- [ ] **`lai-19`** local-ai consolidation sweep _(est 2-4 hrs)_
- [ ] **`lai-20`** local-ai buildout close-out _(est 1-3 hrs)_
- [ ] **`lai-21`** Open WebUI 0.11.0 upgrade _(est 1-3 hrs)_

### media-pipeline
- [ ] **`fix-70`** NAS Plex is one build behind — apply the pending Plex package update _(est <1 hr)_
- [ ] **`fix-73`** Clear the residual deluge pre-import-stuck grab (Only Murders S02E05) _(est <1 hr)_
- [ ] **`media-09`** fix-27 residual: re-grab 5 un-extractable titles + reclaim ~200GB of redundant library RARs _(est 1-2 hrs)_
- [ ] **`media-10`** Seedbox: retire drained readarr label pair from deluge-reaper _(est 10 min)_ — ⛔ gate: not before 2026-08-04
- [ ] **`media-13`** Release reclaimed disk pinned by stale 2026-07-02 Btrfs @sharesnap snapshots (volume2/volume3) _(est 20-40 min)_

### media-polish
- [ ] **`fix-77`** Drain the Bazarr subtitle backlog + optional provider-key upgrade _(est 1-3 hrs)_

### ops
- [ ] **`fix-75`** Set Windows RealTimeIsUniversal on rig — durable RTC-skew cure _(est <1 hr)_
- [ ] **`fix-76`** Prove alert delivery reaches a device + add a whole-house dead-man _(est <1 hr)_
- [ ] **`fix-79`** Identify + fix the down Uptime-Kuma monitor on /status/fleet _(est <1 hr)_
- [ ] **`fix-81`** Verify the nvidia-cdi-refresh fix survives a rig reboot _(est <1 hr)_

### photos
- [ ] **`fix-71`** Kaelyn Immich onboarding — enable phone photo backup for the 2nd household user _(est <1 hr)_
- [ ] **`nas-08b`** Import mirrorless-camera SD card into Immich via immich-go (+ pbak option) _(est 30 min)_

### reading
- [ ] **`fix-78`** Suwayomi/Komga manga backlog mass-backfill (16 series, 0 chapters) _(est 1-3 hrs)_ — ⛔ gate: storage/bandwidth decision — confirm which series + volume before mass download
- [ ] **`read-05`** Connect KOReader to Calibre/CWA over WiFi (OPDS + wireless send) _(est 20 min)_
- [ ] **`read-06`** Enable CWA built-in KOReader progress sync (KOSync) on the Kobo _(est 20 min)_
- [ ] **`read-08`** Wire the KOReader Wallabag plugin on the Kobo _(est 20 min)_
- [ ] **`read-09`** Add RSS/news to KOReader (Miniflux tie-in) _(est 20 min)_

### security
- [ ] **`foss-04`** Ente Auth adoption + YubiKey enrollment (Authy migration) _(est 1-2 hrs)_
- [ ] **`sec-01`** Turn on MFA/2FA everywhere (hardware key on the crown jewels) _(est 1-2 hrs)_
- [ ] **`sec-04`** Harden exposed surfaces (CrowdSec + forward-auth on the seedbox/public ports) _(est 1 hr)_ — ⛔ gate: Tailscale SSH ACL for operator → seedbox (currently blocked)
- [ ] **`sec-06`** B2 master key custody: regenerate in console, store offline (Proton Pass/paper); optionally scope HB's key _(est 15-30 min)_
- [ ] **`sec-07`** ntfy least-privilege: per-publisher users/tokens instead of everything on admin _(est 1-2 hrs)_
- [ ] **`sec-08`** Rotate credentials that left the fleet: Plex token (iCloud snapshot) + secrets printed in the committed audit doc; purge iCloud Recently Deleted _(est 1-2 hrs)_ — ⛔ gate: plex-token-rotation-signs-out-devices
- [ ] **`sec-09`** Cloudflare token least-privilege: read-only DNS token for verification; keep the write token vault-only _(est 30-45 min)_
- [ ] **`sec-10`** arr API keys committed in cleartext in the repo (unpackerr.conf) — rotate + externalize to a gitignored env _(est 45-90 min)_
- [ ] **`sec-11`** Rotate bookshelf API key (exposed in agent session transcript) _(est 30-45 min)_

### smart-home
- [ ] **`ha-04`** Install HACS (community store) _(est 15 min)_
- [ ] **`ha-06`** Thermostat: install ecobee Premium (in box) — local HomeKit control; retire Nest SDM plan _(est 45-60 min)_
- [ ] **`ha-07`** Add Midea AC + dehumidifier via midea_ac_lan (local) — and BACK UP the .json _(est 30 min)_
- [ ] **`ha-09`** Set up local voice (Assist + Whisper + Piper); LLM agent via LiteLLM (ha-17) _(est 30-45 min)_ — ⛔ gate: mic test
- [ ] **`ha-10`** Configure the Energy dashboard _(est 20 min)_
- [ ] **`ha-14`** Bring UniFi Protect cameras into Home Assistant (local, no subscription) _(est 30 min)_ — ⛔ gate: Protect API creds in vault (currently empty)
- [ ] **`ha-18`** Rooms & floors: HA registry matches the real house _(est 30 min)_
- [ ] **`ha-19`** IoT VLAN migration: move every WiFi IoT device onto VLAN 20 + firewall groups _(est 2-3 h over days)_
- [ ] **`ha-21`** Roborock QV 35S → HA (official integration) _(est 20 min)_
- [ ] **`ha-22`** iRobot Roomba i7+ → HA (local BLID/password) _(est 20 min)_
- [ ] **`ha-23`** LG CX + C4 TVs → webOS (local) + Wake-on-LAN; soundbar stays dumb _(est 25 min)_
- [ ] **`ha-25`** Apple TVs ×2 + HomePods ×3 → HA media players (local) _(est 20 min)_
- [ ] **`ha-26`** COSORI air fryer via VeSync (cloud, optional) _(est 10 min)_
- [ ] **`ha-27`** Emporia Vue 3 → HA energy: cloud now, ESPHome flash = local end-state _(est 30 min + later 2 h)_
- [ ] **`ha-28`** Withings Body Cardio scale + BPM Connect (cloud OAuth) _(est 30 min)_
- [ ] **`ha-31`** Automations pack v1 (git-backed YAML) _(est half day)_
- [ ] **`ha-32`** HA ops glue: SSH add-on, git-backed /config, nightly backups verify, checks.d/ha.yaml, Homepage _(est 1 h)_

---

## Deferred (parked — optional / hardware-gated / someday)

- **`fut-01`** Garden watering: OpenSprinkler (or ESPHome valves) — local irrigation — _DEFERRED — garden watering; 2-5yr future project (on shopping list)._
- **`fut-02`** Plug-in solar (NY legislation) + local production monitoring — _DEFERRED — plug-in solar + local monitoring; 2-5yr, pending NY legislation (on shopping list)._
- **`fut-03`** DIY weather station (local) — _DEFERRED — DIY weather station; 2-5yr future (on shopping list)._
- **`fut-04`** Meshtastic node(s): hobbyist LoRa mesh, non-ISP comms — _DEFERRED — Meshtastic LoRa mesh; 2-5yr hobbyist (on shopping list)._
- **`fut-05`** Sump pump with smart monitoring — _DEFERRED — sump-pump smart monitoring; 2-5yr future (on shopping list)._
- **`fut-06`** Grow tent, local-first (not VIVOSUN cloud) — _DEFERRED — grow tent local-first; 2-5yr future (on shopping list)._
- **`game-14`** Game launcher (Heroic/Lutris) + RomM retro library — _DEFERRED (optional, no active plan) — game launcher (Heroic/Lutris) + RomM retro library._
- **`glue-01`** UPS power resilience: NUT netclient on Ubuntu listening to the NAS UPS — _DEFERRED — UPS/NUT power resilience; no budget for a UPS right now._
- **`glue-06`** Push ALL configs to Git + run the rebuild drill (capstone) — _DEFERRED — bare-OS rebuild-drill capstone; DR validation parked._
- **`ha-08`** (Optional) Replace Midea OEM dongle with ESPHome SLWF-01Pro (cloud-free) — _DEFERRED (optional, no active plan) — replace the Midea OEM WiFi dongle with an ESPHome SLWF-01Pro (cloud-free). Midea i_
- **`ha-12`** Zigbee backbone: Mosquitto + Zigbee2MQTT + USB coordinator — _DEFERRED — the Zigbee backbone (Mosquitto + Zigbee2MQTT + USB coordinator) is only needed for the ha-30 sensor rollout; _
- **`ha-13`** Presence detection: HA Companion app + room-level (mmWave/Bermuda) — _DEFERRED (optional, no active plan) — mmWave/Zigbee room-level presence sensors; needs hardware purchase + placement._
- **`ha-15`** (Optional) Frigate for better local camera AI (zones, package/animal/face) — _DEFERRED — Frigate; UniFi Protect's built-in detection judged sufficient._
- **`ha-20`** Level Lock+ ×2: Apple Home now; trial HA pairing via BLE proxy after sensors arrive — _DEFERRED — Level Lock+ into HA; locks work in Apple Home now, HA path is hardware-gated on ha-30 ESP32 BLE proxies._
- **`ha-24`** LG ThinQ range + microwave (cloud — status/alerts only, optional) — _DEFERRED — LG ThinQ range/microwave; optional low-value cloud status only._
- **`ha-30`** Sensor rollout wave 1: Zigbee sensors, plugs, buttons (shopping list) — _DEFERRED — sensor rollout wave 1 (~$505-865 hardware); buy in stages (budget). On the hardware shopping list._
- **`lai-15`** StrategyWiki ZIM build — _BLOCKED by Cloudflare — StrategyWiki fingerprints and 403s mwoffliner's Node/undici HTTP client (curl on host AND in-con_
- **`retro-07`** Retro handheld onboarding (e.g. AYN Thor Max) — _DEFERRED — retro handheld onboarding; hardware-gated (no handheld owned yet)._
- **`sbom-05`** Write per-host restore runbooks and run a whole-host rebuild drill — _DEFERRED — per-host restore runbooks + rebuild drill; twin of glue-06, deferred together._

---

_Hardware to buy for these: the wiki hardware page (<https://wiki.tabaska.us/reference/hardware/>). Full per-track tables + done/retired history: the wiki roadmap._
