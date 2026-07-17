# TODO — Going Analogue homelab

**The single todo list for this project.** Generated from `foss-setup/docs/tasks.json` (task definitions) + `foss-setup/docs/progress.json` (status) by `foss-setup/scripts/docs/gen-todo.py`. The wiki is the browsable mirror + the reference source of truth: <https://wiki.tabaska.us/roadmap/>. Re-run the generator after any change.

**169/260 done** · **65 open** · **18 deferred** · 10 retired.

---

## Open (remaining work)

### agent-handoff
- [ ] **`handoff-12`** Post-sprint cleanup — delete vault and rotate keys _(est 10 min)_

### backups-offsite
- [ ] **`fix-42`** Make off-site DR reproducible (ansible backup role is a no-op diverged from live) _(est 1-3 hrs)_

### desktop
- [ ] **`foss-02`** Package the FOSS desktop suite: cachyos-desktop-suite.sh + macOS Brewfile (chezmoi-tracked) _(est ~half day)_
- [ ] **`foss-03`** Syncthing v2 hub on NAS + mini node (local-first file sync) _(est ~half day)_
- [ ] **`glue-02`** Desktop baseline on CachyOS: browser(s) + LibreOffice (anytime) _(est 20-40 min)_
- [ ] **`glue-04b`** Apply chezmoi dotfiles to rig + mini (fleet rollout) _(est 20-30 min)_

### docker-host
- [ ] **`fix-39`** mini host cleanup: dead Pterodactyl LEMP + root cron, broken crons, dead stack dirs, reclaimable docker _(est 1-3 hrs)_
- [ ] **`fix-45`** Fleet hygiene batch: host junk, core dumps, stale caches, log/backup bloat (mini/rig/seedbox) _(est 1-3 hrs)_

### ebook-mgmt
- [ ] **`ebook-06`** End-to-end ebook verification (Libreseerr → Betty → Readarr → CWA → Plex/Kobo) _(est 30-45 min)_

### gaming
- [ ] **`fix-34`** Fix AMP scheduled backups (silently failing) + backup-bloat in restic + playit UDP churn _(est 1-3 hrs)_
- [ ] **`game-09`** Rig idle-power tuning (24/7 baseline) _(est 20-30 min)_
- [ ] **`game-12`** Save-game sync with Ludusavi + Syncthing _(est 30 min)_
- [ ] **`retro-03`** Save/state sync mesh (Syncthing) _(est 60 min)_ — ⛔ gate: device pairing approvals
- [ ] **`retro-04`** SteamDeck: EmuDeck/RetroDeck wiring _(est 45 min)_ — ⛔ gate: on-device steps
- [ ] **`retro-05`** Rig: emulation frontend + RomM integration _(est 60 min)_
- [ ] **`retro-06`** RetroAchievements + cheat DB _(est 30 min)_ — ⛔ gate: RetroAchievements account creds in vault
- [ ] **`retro-08`** RomM RetroAchievements dashboard (view-only unlock %/hardcore stats) _(est ~15 min config)_ — ⛔ gate: operator RetroAchievements username

### media-pipeline
- [ ] **`fix-25`** Fix the silent "grabbed → never imported" class (download-client import + reaper label coverage) _(est 1-3 hrs)_
- [ ] **`fix-26`** Reconcile stuck request-layer states (seerr/libreseerr/musicseerr dangling & unmonitored) _(est 1-3 hrs)_
- [ ] **`fix-27`** Remediate "green but not watchable": sample-file imports + unextracted RARs _(est 1-3 hrs)_
- [ ] **`media-05`** Deploy Jellyfin as a fully-local media server (plex.tv-independent parallel to Plex) _(est 1-2 hrs)_
- [ ] **`seed-12`** Deploy Bitmagnet self-hosted DHT crawler on NAS (rate-limit-proof indexer hedge) _(est ~1 hr + runbook)_

### media-polish
- [ ] **`fix-28`** Fix Plex/Navidrome library correctness (unmatched items, missing tracks, #recycle indexing) _(est 1-3 hrs)_
- [ ] **`fix-37`** Media-aux service config fixes (navidrome backup, kometa, pinchflat/bgutil, RomM empty) _(est 1-3 hrs)_

### nas-foundation
- [ ] **`fix-31`** Restore UPS/NUT power-loss protection (or cleanly retire the dead client) _(est 1-3 hrs)_
- [ ] **`fix-40`** NAS host hygiene: timezone drift, soularr parked import, core dumps, junk files, single-disk note _(est 1-3 hrs)_

### network
- [ ] **`fix-24`** Close unintended public exposure: WAN-reachable Plex 32400 + public A-record to LAN IP _(est 1-3 hrs)_

### ops
- [ ] **`fix-32`** Fix Caddy reverse-proxy routes (ha.tabaska.us 400, llamaswap not reloaded, stray placeholders/vhosts) _(est 1-3 hrs)_
- [ ] **`fix-41`** Repo-vs-live drift codification (forgejo stack, manifests, .env keys, ansible units) _(est 1-3 hrs)_

### photos
- [ ] **`fix-35`** Immich: start real phone backups (empty library) + lock down the unused second admin _(est 1-3 hrs)_
- [ ] **`nas-08b`** Import mirrorless-camera SD card into Immich via immich-go (+ pbak option) _(est 30 min)_

### reading
- [ ] **`fix-38`** Reading/CWA: reconcile Kobo store-passthrough state + note fork-image supply-chain risk _(est 1-3 hrs)_
- [ ] **`read-02`** Set up Syncthing as a systemd user service on CachyOS _(est 20 min)_
- [ ] **`read-05`** Connect KOReader to Calibre/CWA over WiFi (OPDS + wireless send) _(est 20 min)_
- [ ] **`read-06`** Enable CWA built-in KOReader progress sync (KOSync) on the Kobo _(est 20 min)_
- [ ] **`read-08`** Wire the KOReader Wallabag plugin on the Kobo _(est 20 min)_
- [ ] **`read-09`** Add RSS/news to KOReader (Miniflux tie-in) _(est 20 min)_
- [ ] **`read-12`** Install + configure gPodder for podcasts on CachyOS (funnel into Rhythmbox) _(est 20 min)_

### security
- [ ] **`fix-23`** Secrets & filesystem-permission hygiene (world-readable env, stale local secret dumps) _(est 1-3 hrs)_
- [ ] **`foss-01`** Bitwarden → Vaultwarden data cutover (point clients at vault.tabaska.us) _(est 1-2 hrs)_
- [ ] **`foss-04`** Ente Auth adoption + YubiKey enrollment (Authy migration) _(est 1-2 hrs)_
- [ ] **`sec-01`** Turn on MFA/2FA everywhere (hardware key on the crown jewels) _(est 1-2 hrs)_
- [ ] **`sec-04`** Harden exposed surfaces (CrowdSec + forward-auth on the seedbox/public ports) _(est 1 hr)_ — ⛔ gate: Tailscale SSH ACL for operator → seedbox (currently blocked)

### smart-home
- [ ] **`fix-36`** Home Assistant health: unavailable entities, dead integrations, pending updates _(est 1-3 hrs)_
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

### verification
- [ ] **`fix-29`** Close the liveness-vs-reality monitoring gap (end-to-end checks for the failure classes just found) _(est 1-3 hrs)_
- [ ] **`fix-30`** Repair the verification framework itself (LLM triage, false positives, deploy drift) _(est 1-3 hrs)_

### wiki
- [ ] **`fix-43`** Repo junk & dead-path cleanup (tracked pycache, stale root files, worktree, retired-service remnants) _(est 1-3 hrs)_
- [ ] **`fix-44`** Tracker + wiki drift cleanup (stale generated pages, orphan ids, arithmetic, recurring wiki-drift red) _(est 1-3 hrs)_

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
- **`retro-07`** Retro handheld onboarding (e.g. AYN Thor Max) — _DEFERRED — retro handheld onboarding; hardware-gated (no handheld owned yet)._
- **`sbom-05`** Write per-host restore runbooks and run a whole-host rebuild drill — _DEFERRED — per-host restore runbooks + rebuild drill; twin of glue-06, deferred together._

---

_Hardware to buy for these: the wiki hardware page (<https://wiki.tabaska.us/reference/hardware/>). Full per-track tables + done/retired history: the wiki roadmap._
