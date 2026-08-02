# TODO — Going Analogue homelab

**The single todo list for this project.** Generated from `foss-setup/docs/tasks.json` (task definitions) + `foss-setup/docs/progress.json` (status) by `foss-setup/scripts/docs/gen-todo.py`. The wiki is the browsable mirror + the reference source of truth: <https://wiki.tabaska.us/roadmap/>. Re-run the generator after any change.

**251/351 done** · **67 open** · **18 deferred** · 15 retired.

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
- [ ] **`fix-69`** Fleet hygiene batch: meme-review check-vs-policy contradiction, log floods (synologand 7k, deluged 1.1/s, ufw), stale units/kernel, /tmp session litter incl. cookies, dead experiments _(est 1-3 hrs)_

### ebook-mgmt
- [ ] **`ebook-06`** End-to-end ebook verification (Libreseerr → Betty → Readarr → CWA → Plex/Kobo) _(est 30-45 min)_

### gaming
- [ ] **`game-09`** Rig idle-power tuning (24/7 baseline) _(est 20-30 min)_
- [ ] **`retro-03`** Save/state sync mesh (Syncthing) _(est 60 min)_ — ⛔ gate: device pairing approvals
- [ ] **`retro-04`** SteamDeck: EmuDeck/RetroDeck wiring _(est 45 min)_ — ⛔ gate: on-device steps
- [ ] **`retro-06`** RetroAchievements + cheat DB _(est 30 min)_ — ⛔ gate: RA account USERNAME+PASSWORD for RetroArch login (distinct from the RomM API key) + an emulator installed first (retro-05 rig / retro-04 Deck)
- [ ] **`retro-08`** RomM RetroAchievements dashboard (view-only unlock %/hardcore stats) _(est ~15 min config)_ — ⛔ gate: operator RetroAchievements username

### media-pipeline
- [ ] **`fix-49`** Navidrome total library wipeout: bad .ndignore written by the fix-28 guard + one empty-root CIFS scan flagged all 3495 tracks missing _(est 1-3 hrs)_
- [ ] **`fix-50`** Bitmagnet DHT junk-grab storm: arrs re-grabbing owned titles hourly, foreign-audio junk imported into the library today; indexer also timing out via Prowlarr _(est 1-3 hrs)_ — ⛔ gate: disruptive — removes wrongly-imported library files + changes indexer config; 4-7AM window + operator approval for deletions
- [ ] **`fix-54`** Movies/TV import stall: torrent payloads deleted under live torrents, move_completed wedge, 3-4 day arr retry loops, sample files back in the library _(est 1-3 hrs)_ — ⛔ gate: disruptive — removes wedged torrents/queue records and deletes junk sample files; 4-7AM window + operator approval
- [ ] **`fix-56`** Music acquisition hygiene: soularr failed-import backlog cycling, junk MusicBrainz albums grinding every 5 minutes, 3 albums stuck partial _(est 1-3 hrs)_
- [ ] **`media-09`** fix-27 residual: re-grab 5 un-extractable titles + reclaim ~200GB of redundant library RARs _(est 1-2 hrs)_
- [ ] **`media-10`** Seedbox: retire drained readarr label pair from deluge-reaper _(est 10 min)_ — ⛔ gate: not before 2026-08-04
- [ ] **`media-13`** Release reclaimed disk pinned by stale 2026-07-02 Btrfs @sharesnap snapshots (volume2/volume3) _(est 20-40 min)_

### media-polish
- [ ] **`fix-59`** Bazarr has ZERO subtitle providers enabled — 2868 wanted episodes can never fetch while the check stays green (media-12 regression) _(est 1-3 hrs)_
- [ ] **`fix-67`** Small-pipeline regression batch: kometa IMDb 403s (29 errors), pinchflat bot-check strandings, CWA cover, edited-memo journaling hole, bug-intake residue, syncthing hub inotify, Terraria tile _(est 1-3 hrs)_

### nas-foundation
- [ ] **`fix-55`** NAS chronic I/O pressure + SQLite 'database is locked' storm degrading 5 arr apps, killing soularr, hanging docker CLI and healthchecks _(est 1-3 hrs)_ — ⛔ gate: disruptive — may restart NAS DB-backed containers; 4-7AM window

### ops
- [ ] **`fix-63`** Alerting-plane architecture: everything that could report a mini outage lives ON mini; rig auto-recovery only in the daily tier; ntfy history 12h; no alert-delivery proof _(est 1-3 hrs)_
- [ ] **`fix-64`** Rig host stability: 27h operator poweroff (power key honored on a 24/7 host), RTC 4h skew corrupting timelines, boot-race + catch-up failures, crash-loop and segfault batch _(est 1-3 hrs)_ — ⛔ gate: disruptive — logind/RTC changes + possible rig reboot; 4-7AM window
- [ ] **`fix-65`** Config control-plane drift: local-ai-tooling Forgejo 16 commits behind (ai-03 regression), ansible perpetual changed=1 root-caused, Mac ssh-config 3-layer drift where an apply would delete live aliases _(est 1-3 hrs)_

### photos
- [ ] **`fix-60`** Immich cluster: nightly ffmpeg segfault on one corrupt .mov (5 nights), second household user has 0 photos ever, bogus 4501 date tops the timeline, pg-dumps unrotated _(est 1-3 hrs)_
- [ ] **`nas-08b`** Import mirrorless-camera SD card into Immich via immich-go (+ pbak option) _(est 30 min)_

### reading
- [ ] **`fix-57`** Books request layer broken-quiet: last successful request 07-20, 12/30 libreseerr requests errored, one grabbed book lost pre-import for 13 days _(est 1-3 hrs)_
- [ ] **`fix-58`** Manga chain silently severed at BOTH ends: Komga scheduler scans a deleted library-id (279 new chapters invisible 6 days) and Suwayomi's bind raced the CIFS mount into an empty view _(est 1-3 hrs)_ — ⛔ gate: disruptive — Komga library-id surgery + container restart ordering changes on rig; 4-7AM window
- [ ] **`read-05`** Connect KOReader to Calibre/CWA over WiFi (OPDS + wireless send) _(est 20 min)_
- [ ] **`read-06`** Enable CWA built-in KOReader progress sync (KOSync) on the Kobo _(est 20 min)_
- [ ] **`read-08`** Wire the KOReader Wallabag plugin on the Kobo _(est 20 min)_
- [ ] **`read-09`** Add RSS/news to KOReader (Miniflux tie-in) _(est 20 min)_

### security
- [ ] **`fix-51`** LAN exposure batch: rogue nc -lvnp 9999 listener on mini (17 days), ~85 fleet ports on 0.0.0.0 bypassing Caddy auth, BookLogr registration still open _(est 1-3 hrs)_
- [ ] **`fix-52`** Seedbox Syncthing: syncs nothing (0 folders, 0 peers, 0 bytes ever) while its plaintext-HTTP GUI is open to the public internet _(est 1-3 hrs)_
- [ ] **`fix-53`** File-permission regressions: mylar3 writes 0644 secret-bearing config + world-writable cache (fix-23 regression), HA offsite tars group-writable to every NAS group _(est 1-3 hrs)_
- [ ] **`foss-04`** Ente Auth adoption + YubiKey enrollment (Authy migration) _(est 1-2 hrs)_
- [ ] **`sec-01`** Turn on MFA/2FA everywhere (hardware key on the crown jewels) _(est 1-2 hrs)_
- [ ] **`sec-04`** Harden exposed surfaces (CrowdSec + forward-auth on the seedbox/public ports) _(est 1 hr)_ — ⛔ gate: Tailscale SSH ACL for operator → seedbox (currently blocked)
- [ ] **`sec-06`** B2 master key custody: regenerate in console, store offline (Proton Pass/paper); optionally scope HB's key _(est 15-30 min)_
- [ ] **`sec-07`** ntfy least-privilege: per-publisher users/tokens instead of everything on admin _(est 1-2 hrs)_
- [ ] **`sec-08`** Rotate credentials that left the fleet: Plex token (iCloud snapshot) + secrets printed in the committed audit doc; purge iCloud Recently Deleted _(est 1-2 hrs)_ — ⛔ gate: plex-token-rotation-signs-out-devices
- [ ] **`sec-09`** Cloudflare token least-privilege: read-only DNS token for verification; keep the write token vault-only _(est 30-45 min)_
- [ ] **`sec-10`** arr API keys committed in cleartext in the repo (unpackerr.conf) — rotate + externalize to a gitignored env _(est 45-90 min)_
- [ ] **`sec-11`** Rotate bookshelf API key (exposed in agent session transcript) _(est 30-45 min)_
- [ ] **`sec-12`** Repair malformed multi-line value in mini /etc/verification/env (a stored token spans physical lines and leaks when the file is sourced) + decide on rotating the exposed Hardcover token _(est 20-40 min)_

### smart-home
- [ ] **`fix-66`** mini cannot reach the IoT VLAN: journaling docker bridge 192.168.16.0/20 swallows 192.168.20.0/24 (net-05 regression) + HA appliance 3-min overnight network loss _(est 1-3 hrs)_
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
- [ ] **`fix-61`** Verification framework repair: daily run killed by its own 30-min timeout mid-incident (dead-man dark, no self-page), triage 91% nonfunctional, chronic false-positive + flapping checks _(est 1-3 hrs)_
- [ ] **`fix-62`** Check quality + coverage batch: 4 structurally-broken checks (plex-version, stash auth, immich-backup 60s find, esde), Stash no-op self-heal page storm, liveness-only quartet, filed monitoring gaps _(est 1-3 hrs)_

### wiki
- [ ] **`fix-68`** Tracker/docs truth repair: 20 done tasks failing checks with zero formal reopens, wiki-drift from a same-commit violation, catalog lagging 6 live services, stale-path/plan-era prose _(est 1-3 hrs)_

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
