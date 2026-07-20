# TODO — Going Analogue homelab

**The single todo list for this project.** Generated from `foss-setup/docs/tasks.json` (task definitions) + `foss-setup/docs/progress.json` (status) by `foss-setup/scripts/docs/gen-todo.py`. The wiki is the browsable mirror + the reference source of truth: <https://wiki.tabaska.us/roadmap/>. Re-run the generator after any change.

**194/280 done** · **55 open** · **18 deferred** · 13 retired.

---

## Open (remaining work)

### agent-handoff
- [ ] **`handoff-12`** Post-sprint cleanup — delete vault and rotate keys _(est 10 min)_

### books-cutover
- [ ] **`bmig-03`** Books cutover 3/6: migrate the library into Bookshelf (authors + existing files, no re-downloads) _(est 90-150 min)_
- [ ] **`bmig-04`** Books cutover 4/6: libreseerr -> Bookshelf backend + author-gate + ISBN-first + fail-loudly (C1/C4 fix) _(est 60-120 min)_
- [ ] **`bmig-05`** Books cutover 5/6: collateral cleanup (C5), re-drive stuck requests, decommission readarr + goodreads metadata _(est 90-150 min)_
- [ ] **`bmig-06`** Books cutover 6/6: migrate all checks to Bookshelf + new tripwires (token expiry, author parity, search canary) + docs + close _(est 90-150 min)_
- [ ] **`books-hc-upstream-swap`** Swap rreading-glasses-hc off the temporary local image once upstream fixes Hardcover batch limit (#574) _(est 15-30 min)_

### desktop
- [ ] **`foss-02`** Package the FOSS desktop suite: cachyos-desktop-suite.sh + macOS Brewfile (chezmoi-tracked) _(est ~half day)_
- [ ] **`foss-03`** Syncthing v2 hub on NAS + mini node (local-first file sync) _(est ~half day)_
- [ ] **`glue-02`** Desktop baseline on CachyOS: browser(s) + LibreOffice (anytime) _(est 20-40 min)_
- [ ] **`glue-04b`** Apply chezmoi dotfiles to rig + mini (fleet rollout) _(est 20-30 min)_

### ebook-mgmt
- [ ] **`ebook-06`** End-to-end ebook verification (Libreseerr → Betty → Readarr → CWA → Plex/Kobo) _(est 30-45 min)_

### gaming
- [ ] **`game-09`** Rig idle-power tuning (24/7 baseline) _(est 20-30 min)_
- [ ] **`game-12`** Save-game sync with Ludusavi + Syncthing _(est 30 min)_
- [ ] **`retro-03`** Save/state sync mesh (Syncthing) _(est 60 min)_ — ⛔ gate: device pairing approvals
- [ ] **`retro-04`** SteamDeck: EmuDeck/RetroDeck wiring _(est 45 min)_ — ⛔ gate: on-device steps
- [ ] **`retro-05`** Rig: emulation frontend + RomM integration _(est 60 min)_
- [ ] **`retro-06`** RetroAchievements + cheat DB _(est 30 min)_ — ⛔ gate: RetroAchievements account creds in vault
- [ ] **`retro-08`** RomM RetroAchievements dashboard (view-only unlock %/hardcore stats) _(est ~15 min config)_ — ⛔ gate: operator RetroAchievements username

### media-pipeline
- [ ] **`media-05`** Deploy Jellyfin as a fully-local media server (plex.tv-independent parallel to Plex) _(est 1-2 hrs)_
- [ ] **`media-07`** MusicSeerr can still create unmonitored-artist requests (upstream monitor_artist=0 default) — tripwire-covered, close the generator _(est 30-45 min)_
- [ ] **`media-09`** fix-27 residual: re-grab 5 un-extractable titles + reclaim ~200GB of redundant library RARs _(est 1-2 hrs)_

### network
- [ ] **`net-15`** Edge/verification doc-truth trivia: stale seedbox-SSH claim in verification README; Plex ManualPortMappingMode mismatch _(est 20 min)_

### photos
- [ ] **`nas-08b`** Import mirrorless-camera SD card into Immich via immich-go (+ pbak option) _(est 30 min)_

### reading
- [ ] **`read-02`** Set up Syncthing as a systemd user service on CachyOS _(est 20 min)_
- [ ] **`read-05`** Connect KOReader to Calibre/CWA over WiFi (OPDS + wireless send) _(est 20 min)_
- [ ] **`read-06`** Enable CWA built-in KOReader progress sync (KOSync) on the Kobo _(est 20 min)_
- [ ] **`read-08`** Wire the KOReader Wallabag plugin on the Kobo _(est 20 min)_
- [ ] **`read-09`** Add RSS/news to KOReader (Miniflux tie-in) _(est 20 min)_
- [ ] **`read-12`** Install + configure gPodder for podcasts on CachyOS (funnel into Rhythmbox) _(est 20 min)_

### security
- [ ] **`foss-01`** Bitwarden → Vaultwarden data cutover (point clients at vault.tabaska.us) _(est 1-2 hrs)_
- [ ] **`foss-04`** Ente Auth adoption + YubiKey enrollment (Authy migration) _(est 1-2 hrs)_
- [ ] **`sec-01`** Turn on MFA/2FA everywhere (hardware key on the crown jewels) _(est 1-2 hrs)_
- [ ] **`sec-04`** Harden exposed surfaces (CrowdSec + forward-auth on the seedbox/public ports) _(est 1 hr)_ — ⛔ gate: Tailscale SSH ACL for operator → seedbox (currently blocked)
- [ ] **`sec-06`** B2 master key custody: regenerate in console, store offline (Bitwarden/paper); optionally scope HB's key _(est 15-30 min)_
- [ ] **`sec-07`** ntfy least-privilege: per-publisher users/tokens instead of everything on admin _(est 1-2 hrs)_
- [ ] **`sec-08`** Rotate credentials that left the fleet: Plex token (iCloud snapshot) + secrets printed in the committed audit doc; purge iCloud Recently Deleted _(est 1-2 hrs)_ — ⛔ gate: plex-token-rotation-signs-out-devices
- [ ] **`sec-09`** Cloudflare token least-privilege: read-only DNS token for verification; keep the write token vault-only _(est 30-45 min)_
- [ ] **`sec-10`** arr API keys committed in cleartext in the repo (unpackerr.conf) — rotate + externalize to a gitignored env _(est 45-90 min)_

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
- **`retro-07`** Retro handheld onboarding (e.g. AYN Thor Max) — _DEFERRED — retro handheld onboarding; hardware-gated (no handheld owned yet)._
- **`sbom-05`** Write per-host restore runbooks and run a whole-host rebuild drill — _DEFERRED — per-host restore runbooks + rebuild drill; twin of glue-06, deferred together._

---

_Hardware to buy for these: the wiki hardware page (<https://wiki.tabaska.us/reference/hardware/>). Full per-track tables + done/retired history: the wiki roadmap._
