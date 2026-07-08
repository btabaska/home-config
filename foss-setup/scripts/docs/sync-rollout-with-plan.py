#!/usr/bin/env python3
"""Align Rollout Guide taskData in docs/index.html with current plan decisions."""
import json
import re
from pathlib import Path

HTML = Path(__file__).resolve().parents[2] / "docs" / "index.html"
text = HTML.read_text()
m = re.search(
    r'(<script type="application/json" id="taskData">\s*)(\[.*?\])(\s*</script>)',
    text,
    re.S,
)
if not m:
    raise SystemExit("taskData block not found")

tasks = json.loads(m.group(2))
by_id = {t["id"]: t for t in tasks}

STORAGE_SCHEMA = "nas-storage-schema.md"

# --- NAS foundation: three-volume schema file paths ----------------------------
for tid in ("nas-00a", "nas-00b", "nas-00c", "nas-00d"):
    if tid in by_id:
        by_id[tid]["files"] = [STORAGE_SCHEMA]
        if tid == "nas-00d":
            by_id[tid]["files"].append("configs/network/vlan-zone-firewall-plan.md")

# --- docker-05 Navidrome: NFS after nas-00d (not removed nas-00e) --------------
by_id["docker-05"]["depends_on"] = ["docker-02", "nas-00d"]
by_id["docker-05"]["steps"] = [
    "Prerequisite: docker-01, docker-02 and nas-00d (NFS exports) complete.",
    "On the Mac mini, mount the NAS music library from Volume 1 (three-volume layout): "
    "`sudo mkdir -p /mnt/nas/music` and add to /etc/fstab: "
    "`192.168.10.4:/volume1/music /mnt/nas/music nfs defaults,_netdev 0 0` then `sudo mount -a`.",
    "Copy the stack: `scp -r ~/Documents/Home/foss-setup/configs/docker-stack/stacks/navidrome mini:/tmp/navidrome`",
    "`ssh mini 'sudo mkdir -p /opt/stacks/navidrome && sudo rsync -a /tmp/navidrome/ /opt/stacks/navidrome/'`",
    "`ssh mini 'cd /opt/stacks/navidrome && cp -n .env.example .env'` — set MUSIC_FOLDER=/mnt/nas/music "
    "(Lidarr imports to /volume1/music on the NAS; Navidrome reads the same tree via NFS).",
    "`ssh mini 'cd /opt/stacks/navidrome && docker compose up -d && docker compose ps'`",
    "Browse to http://macmini.<tailnet>:4533 — confirm library scan finds tracks from the NAS music share.",
]
by_id["docker-05"]["verify"] = (
    "Navidrome :4533 lists music from /mnt/nas/music (NAS /volume1/music); a track streams in a Subsonic client."
)

# --- read-14 Pinchflat: depends on NFS exports ---------------------------------
by_id["read-14"]["depends_on"] = ["docker-02", "nas-00d"]
steps = by_id["read-14"]["steps"]
by_id["read-14"]["steps"] = [
    "Prerequisite: docker-01, docker-02 and nas-00d (NFS export of /volume1/youtube) complete.",
    "`ssh mini 'sudo mkdir -p /mnt/nas/youtube && grep -q /mnt/nas/youtube /etc/fstab || "
    "echo \"192.168.10.4:/volume1/youtube /mnt/nas/youtube nfs defaults,_netdev 0 0\" | sudo tee -a /etc/fstab'`",
    "`ssh mini 'sudo mount -a && ls /mnt/nas/youtube'`",
    "`scp -r ~/Documents/Home/foss-setup/configs/docker-stack/stacks/pinchflat mini:/tmp/pinchflat`",
    "`ssh mini 'sudo mkdir -p /opt/stacks/pinchflat && sudo rsync -a /tmp/pinchflat/ /opt/stacks/pinchflat/'`",
    "`ssh mini 'cd /opt/stacks/pinchflat && cp -n .env.example .env'` — PINCHFLAT_DOWNLOADS=/mnt/nas/youtube",
    "`ssh mini 'cd /opt/stacks/pinchflat && docker compose up -d && docker compose ps'`",
    "Add a YouTube channel in Pinchflat; optional Plex library root is /volume1/youtube on the NAS (nas-10).",
]

# --- read-11 iPod: NFS mount music from vol1, not /volume1 on rig --------------
by_id["read-11"]["depends_on"] = ["read-10", "nas-00d", "nas-23"]
by_id["read-11"]["steps"] = [
    "Prerequisite: read-10, nas-00d (NFS), and nas-23 (Lidarr → /volume1/music) complete.",
    "On the rig: mount the NAS music master — `sudo mkdir -p /mnt/nas/music`; fstab entry "
    "`192.168.10.4:/volume1/music /mnt/nas/music nfs defaults,_netdev 0 0`; `sudo mount -a`.",
    "Rhythmbox → Preferences → Music → add /mnt/nas/music as a library location. "
    "Do NOT rename Lidarr's /music layout without checking both Plex and this sync.",
    "Plug in the iPod; Rhythmbox auto-detects it. Sync selected playlists/tracks to the device.",
    "Eject from Rhythmbox before unplugging. See scripts/media/ipod-sync-cachyos.md for FirewireGuid/SysInfoExtended first-time setup.",
]
by_id["read-11"]["verify"] = (
    "A playlist synced from /mnt/nas/music (NAS /volume1/music) plays on the iPod."
)

# --- docker-03 Seerr: defer *arr wiring to seed-05 -------------------------------
if "Do not" not in " ".join(by_id["docker-03"].get("steps", [])):
    by_id["docker-03"]["steps"].insert(
        -1,
        "Create admin and sign in with Plex. **Do not** add Sonarr/Radarr yet — that is seed-05 "
        "after the NAS *arr stack (nas-22) and Recyclarr (nas-28) are ready. Album requests use "
        "**MusicSeerr** (docker-16 / seed-06), not Seerr.",
    )

# --- nas-21: explicit three-volume .env paths ----------------------------------
by_id["nas-21"]["steps"] = [
    "Prerequisite: nas-20 rclone mount live at /volume1/mounts/seedbox-files and nas-prep-01 complete.",
    "**Migrate configs (before first start):** on Ubuntu `docker compose stop` sonarr radarr lidarr readarr.",
    "Fresh-copy from Ubuntu into per-app /config mounts: sonarr→/volume1/docker/sonarr/, radarr→radarr/, "
    "liadarr→lidarr/, readarr→readarr/ (see configs/nas/media-automation/migration-from-ubuntu.md).",
    "Copy repo folder configs/nas/media-automation/ → /volume1/docker/media-automation/ on the NAS.",
    "cd /volume1/docker/media-automation && cp .env.example .env. Run `id <user>` on DSM — set PUID, PGID, "
    "TZ=America/New_York, RG_DB_PASSWORD (openssl rand -hex 24), and path vars for the **three-volume layout**: "
    "TV_LIBRARY=/volume3/tv, MOVIES_LIBRARY=/volume2/movies, MUSIC_LIBRARY=/volume1/music, "
    "DOCKER_ROOT=/volume1/docker, SEEDBOX_MOUNT=/volume1/mounts/seedbox-files, "
    "CWA_INGEST=/volume1/docker/calibre-web-automated/ingest.",
    "**Phase A** (core TV/movies): docker compose up -d prowlarr flaresolverr sonarr radarr",
    "**Phase B** (music + books): docker compose up -d lidarr readarr rreading-glasses rreading-glasses-db",
    "**Phase C** (archives): docker compose up -d unpackerr — only after API keys in unpackerr.conf (nas-25).",
    "All images pinned in docker-compose.yml (never :latest). See README.md RAM-phased checklist.",
]
by_id["nas-21"]["verify"] = (
    "Sonarr/Radarr/Lidarr/Readarr UIs respond on the NAS; migrated library counts look correct."
)
by_id["nas-21"]["files"] = [
    "configs/nas/media-automation/docker-compose.yml",
    "configs/nas/media-automation/.env.example",
    "configs/nas/media-automation/README.md",
    "configs/nas/media-automation/migration-from-ubuntu.md",
]

# --- nas-22: Deluge-only seedbox + three-volume roots ----------------------------
by_id["nas-22"]["steps"] = [
    "Open each *arr web UI on the NAS (Sonarr :8989, Radarr :7878, Lidarr :8686, Readarr :8787).",
    "**If migrating from Ubuntu:** change root folders from /data/* to /tv /movies /music /cwa-book-ingest; "
    "Refresh & Scan so existing NAS files re-link.",
    "Remove qBittorrent download clients. Settings → Download Clients → + **Deluge**: Host **185.162.184.38**, "
    "Port = Deluge daemon port, Password = daemon password. Label per app: sonarr / radarr / lidarr / readarr. "
    "**Remove Completed = OFF** in every *arr (Betty keeps seeding).",
    "Remove Jackett Torznab indexers. Prowlarr → Settings → Apps: add Sonarr, Radarr, Lidarr, Readarr with "
    "**Full Sync**. Re-add private indexers using old Jackett Indexers/*.json from migration-snapshot as "
    "credential reference. Add FlareSolverr proxy http://flaresolverr:8191 for Cloudflare indexers.",
    "Settings → Download Clients → Remote Path Mappings → Add: Host 185.162.184.38, "
    "Remote Path /home/hd34/btabaska/files/, Local Path /seedbox/ (repeat in each *arr).",
    "Test a manual search in Sonarr. Test import: manual Deluge torrent with label sonarr → Sonarr imports from "
    "/seedbox to /volume3/tv (cross-filesystem copy, not a hardlink).",
]
by_id["nas-22"]["verify"] = (
    "Migrated library counts match expectations; manual Deluge grab imports from /seedbox to the correct volume path."
)
by_id["nas-22"]["files"] = [
    "configs/nas/media-automation/README.md",
    "configs/nas/media-automation/migration-from-ubuntu.md",
]

# --- nas-23: Lidarr torrent path on NAS (Soulseek = seed-09 + nas-29) ------------
by_id["nas-23"]["steps"] = [
    "**Torrent path (this task):** Lidarr imports into **/music** (host: /volume1/music on Volume 1). "
    "Download client = remote Deluge on 185.162.184.38, label **lidarr**; import from /seedbox/music/.",
    "Remote Path Mapping: Host 185.162.184.38, Remote /home/hd34/btabaska/files/, Local /seedbox/.",
    "Root folder: /music. Enable **Rename Tracks**. Quality: FLAC-preferred with MP3 fallback.",
    "In Prowlarr add a music-capable indexer and sync to Lidarr (Settings → Apps → Full Sync).",
    "**Soulseek path** (slskd on Betty + Soularr on NAS) is **seed-09** and **nas-29** — run after this task.",
    "Do NOT change /music naming without checking BOTH Plex Music and Rhythmbox/libgpod iPod sync (read-11).",
]
by_id["nas-23"]["verify"] = (
    "Torrent album imports to /volume1/music and appears in Plex Music and Navidrome (docker-05)."
)

# --- seed-01 / betty-01: Deluge-only seedbox -----------------------------------
by_id["seed-01"]["steps"] = [
    'Sign up at bytesized-hosting.com for **Stream +3** (3000 GB, 6–10 TB/mo upload cap, €16/mo, EU). '
    "Record SFTP username, home path (/home/hd34/btabaska), and shared IP **185.162.184.38** in Bitwarden.",
    "Architecture lock-in: Betty runs **Deluge** (torrents) and **slskd** (Soulseek, added in seed-09) — "
    "both P2P, both off-site. Do **NOT** install Sonarr, Radarr, Prowlarr, Lidarr, Readarr, qBittorrent, "
    "Bazarr, Soularr, beets, Unpackerr, or sync agents on Betty — the *arr stack + Soularr live on the NAS.",
    "Install Deluge from the Bytesized panel (Deluge only — skip the *arr one-click catalog). "
    "Set ratio/seed-time limits so torrents age out and the box self-prunes under 3 TB.",
    "Record Deluge daemon port + password (needed by nas-22). Continue to **betty-01** for label folders.",
]
by_id["seed-01"]["verify"] = (
    "Bytesized panel shows an active AppBox with Deluge; credentials documented; no *arr apps on Betty."
)

by_id["betty-01"]["steps"] = [
    "SSH into Betty (`ssh seedbox` or provider shell). Confirm Deluge WebUI is reachable.",
    "Note Deluge daemon port + password for nas-22 (remote download client on the NAS *arrs).",
    "Enable the Label plugin (Preferences → Plugins → Label).",
    "Create labels that map to folders under ~/files/ (Deluge sorts completed downloads here; "
    "NAS *arrs import via rclone mount — labels are routing hints, not apps on the seedbox): "
    "sonarr→files/tv, radarr→files/movies, lidarr→files/music, readarr→files/books, manual→files/manual.",
    "`mkdir -p ~/files/{tv,movies,music,books,manual,slskd}` — slskd/ is for Soulseek downloads (seed-09).",
]
by_id["betty-01"]["files"] = [
    "configs/nas/media-automation/README.md",
    "configs/seedbox/rclone.conf.example",
]

# --- seed-05 / seed-07: NAS *arr endpoints -------------------------------------
by_id["seed-05"]["title"] = "Connect Seerr to NAS Sonarr/Radarr (movies/TV — not music)"
by_id["seed-05"]["steps"] = [
    "Open Seerr at http://<mac-mini>:5055 → Settings → Services.",
    "Add **Radarr**: Hostname = NAS IP or MagicDNS (192.168.10.4 / nas.<tailnet>), Port **7878**, "
    "API key from Radarr → Settings → General. Default root folder **/movies**; quality profile = TRaSH from nas-28.",
    "Add **Sonarr**: same NAS host, Port **8989**, root folder **/tv**, same quality profile.",
    "Do **not** add Lidarr in Seerr — Seerr v3.x has no Lidarr support. Album requests use **MusicSeerr** (docker-16 / seed-06).",
    "Settings → Plex: link the **NAS** Plex server (http://<nas>:32400 + token).",
    "Test each service → Save. A test request must appear in the **NAS** *arr UI — not on Betty.",
]
by_id["seed-05"]["files"] = [
    "configs/docker-stack/stacks/seerr/compose.yaml",
    "configs/nas/media-automation/README.md",
    "configs/seedbox/music-pipeline.md",
]

by_id["seed-07"]["steps"] = [
    "Confirm prerequisites: rclone mount live (nas-20), *arr stack wired (nas-21–22), Unpackerr (nas-25), "
    "Plex libraries on vol2/vol3/vol1 (nas-10), Seerr → NAS *arrs (seed-05).",
    "In Seerr, request one **small known title** (movie + TV episode if both wired).",
    "Watch Betty Deluge: torrent appears under files/tv or files/movies with the correct label.",
    "Watch NAS Sonarr/Radarr: grab → import from /seedbox via Remote Path Mapping → file lands in "
    "/volume3/tv or /volume2/movies with TRaSH naming.",
    "Trigger Plex library scan. Confirm the title plays from the NAS libraries.",
    "Confirm Seerr flips the request to **Available** and notifies the requester.",
]
by_id["seed-07"]["files"] = [
    "configs/nas/media-automation/README.md",
    "configs/nas/plex/README.md",
]

# --- nas-10: three separate Plex library roots -----------------------------------
by_id["nas-10"]["steps"] = [
    "Prerequisite: three-volume shares exist (nas-00c) and NFS/SMB exports work (nas-00d). "
    "Paths: /volume2/movies, /volume3/tv, /volume1/music, /volume1/books.",
    "**Before install:** stop Ubuntu Plex (`docker compose stop`). Never run old + new Plex with the same MachineIdentifier.",
    "Take a **fresh** copy from Ubuntu Plex appdata into the DSM Plex data dir (Package Center → Installation folder). "
    "Copy P0 before first start: Preferences.xml, .LocalAdminToken, library.db + blobs.db. "
    "Optional P1/P2: Plug-in Support/Preferences|Data/, Metadata/, Media/. Skip Logs/ and dated *.db-* backups. "
    "See configs/nas/plex/README.md §4.",
    "DSM → Package Center → **Plex Media Server** → Install (native package for Intel Quick Sync on J4125).",
    "Open http://<nas>:32400/web → sign in (skip claim wizard if Preferences.xml has valid PlexOnlineToken).",
    "Settings → Manage → Libraries → **Movies** → /volume2/movies; **TV Shows** → /volume3/tv; "
    "**Music** → /volume1/music. Run **Scan Library Files** if libraries do not auto-match.",
    "Settings → Transcoder → enable **Use hardware acceleration when available** (Quick Sync).",
    "Verify Home users + resume playback. Add Plex appdata to Hyper Backup Tier 1.",
]
by_id["nas-10"]["verify"] = (
    "Plex plays with HW transcode; Home users and watch history preserved (or scan-only fallback in README §4)."
)

# --- nas-26: reinforce single manual-lane job ----------------------------------
by_id["nas-26"]["steps"] = [
    "Prerequisite: nas-20 rclone mount live.",
    "Copy scripts/media/rclone-manual-copy.sh to /volume1/scripts/media/ on the NAS if not already there.",
    "DSM Task Scheduler: run rclone-manual-copy.sh every 15 minutes as root.",
    "This is the **only** scheduled rclone job — copies Deluge label `manual` → /volume1/manual only.",
    "*arr media (tv/movies/music/books) arrives via the live /seedbox mount + *arr import — never via scheduled copy.",
]
by_id["nas-26"]["verify"] = (
    "A file in Betty files/manual/ copies to /volume1/manual; no scheduled job touches *arr label folders."
)

# --- media-03 Maintainerr: NAS *arrs not seedbox --------------------------------
by_id["media-03"]["steps"] = [
    "Deploy Maintainerr at /opt/stacks/maintainerr (docker-02 layout). cp -n .env.example .env && docker compose up -d.",
    "Connect to **NAS Plex** (http://<nas>:32400 + token), **Seerr**, and **NAS Sonarr/Radarr** at 192.168.10.4 "
    "— not the seedbox (Betty is Deluge-only).",
    "Create rules (e.g. unwatched > 90 days and not in a collection) with a grace period.",
    "Run dry-run/notification mode first; review candidates; enable enforcement to cap Tier-2 growth on vol2/vol3.",
]

# --- read-12 gPodder funnel ----------------------------------------------------
by_id["read-12"]["steps"] = [
    "Prerequisite: read-10 complete.",
    "Install gPodder on the rig (`sudo pacman -S --needed gpodder`).",
    "Set gPodder's download folder to a directory inside Rhythmbox's library (e.g. ~/Music/Podcasts or /mnt/nas/music/Podcasts).",
    "Subscribe to feeds; gPodder downloads episodes into that folder.",
    "On iPod plug-in: Rhythmbox sync pushes new podcast episodes alongside music in one operation.",
]

# =============================================================================
# ALL-TRACKS PASS — align every track with foss-setup-plan-2.md + configs/
# =============================================================================

# --- nas-foundation: remove obsolete nas-00e references ------------------------
by_id["nas-00b"]["steps"] = [
    "Prerequisite: nas-00a complete.",
    "**Only if vol2/vol3 are unorganized:** DSM → Control Panel → Shared Folder → delete misplaced media shares on vol2/vol3.",
    "**Only if needed:** Storage Manager → wipe vol2/vol3; recreate empty Basic Btrfs volumes on bays 2 and 3. Do **not** convert to SHR or merge pools.",
    "If vol2/vol3 already hold movies/TV in the right place, **skip wipe** — go straight to nas-00c.",
    "Do NOT touch vol1 — docker, Tier 1, and rsync sources stay until nas-00c completes.",
    "Storage Manager → confirm three **independent** Basic pools (~14.6 / 10.9 / 16.4 TB usable).",
]
by_id["nas-00c"]["steps"] = [
    "Prerequisite: nas-00b complete. Safety: net-08 (Tailscale on NAS) before bulk data moves.",
    "You have **three independent Basic volumes** — each share lives on **one volume only** (vol3=TV, vol2=movies, vol1=music/books/Tier1/docker). No merged pool.",
    "**Volume 3:** create share **`tv`** on Volume 3. **Volume 2:** create **`movies`** on Volume 2.",
    "**Volume 1:** create shares: music, books, youtube, games, manual, photo, docs, appdata, backups, vault, home, staging, frigate, cache — all on Volume 1.",
    "Infrastructure dirs (not shares): `ssh -t nas 'sudo mkdir -p /volume1/docker /volume1/mounts/seedbox-files /volume1/scripts/media'`",
    "Btrfs: checksums ON; compression ON for docs/appdata/vault on vol1; OFF for media; atime OFF.",
    "Move data only where nas-00a map shows wrong placement: TV→/volume3/tv, movies→/volume2/movies; music/books into vol1 shares if still flat on vol1.",
    "Verify rsync: `du -sb` byte counts match; dry-run `rsync -avhn --delete` shows zero pending.",
    "Keep vol1 duplicates until nas-00d (NFS/SMB exports) works and **nas-10 + nas-21** confirm Plex/*arr see the new paths.",
]

# --- network: HA Green on Trusted --------------------------------------------
by_id["net-01"]["steps"] = [
    "Settings → Networks → New Virtual Network for each: Trusted (VLAN 10), IoT (VLAN 20), Cameras (VLAN 30, optional), Work (VLAN 40).",
    "For Guest (VLAN 50), use the Guest/Hotspot network type for built-in client isolation.",
    "Set host/gateway per vlan-zone-firewall-plan.md (e.g. Trusted 192.168.10.1/24, IoT 192.168.20.1/24). Keep DHCP on.",
    "Leave Default (VLAN 1) as management — UniFi gear only, no clients.",
    "**Trusted VLAN hosts:** PCs, NAS (.10), Mac mini (.11), rig (.12), **HA Green (.13)**, phones, consoles, Apollo + Moonlight clients.",
    "Do NOT create a gaming VLAN — Moonlight needs same-subnet mDNS on Trusted.",
]
by_id["net-12"]["steps"] = [
    "Settings → Security → Threat Management: enable IDS/IPS on the Dream Wall.",
    "Use WPA3 (or WPA2/WPA3 transition) where devices support it; map one SSID each to Trusted, IoT, Guest, and Work.",
    "Network-wide DNS filtering lands in **docker-07 (AdGuard Home — chosen)** + **dns-01 (Unbound core on mini)**. "
    "Resilience (**dns-02 → dns-05**) adds NAS secondary AdGuard + fail-open DHCP chain (mini → NAS → gateway) "
    "before pointing client VLANs at AdGuard-only DNS — see configs/network/dns-resilience-plan.md.",
    "Once Hue is fully local in HA, block the Hue bridge from the internet on the IoT VLAN.",
]

# --- smart-home ----------------------------------------------------------------
by_id["ha-01"]["steps"] = [
    "Decision landed: **HA Green purchased** — unbox and connect Ethernet to **Trusted VLAN 10**.",
    "UniFi: DHCP reservation **192.168.10.13** for HA Green (see Network tab). Note MAC for inventory.",
    "Photograph cable/serial; add to Homepage when docker-15 deploys.",
]
by_id["ha-02"]["title"] = "Set up HA Green (purchased — primary path)"
by_id["ha-03"]["steps"] = [
    "**Skip if HA Green is set up (ha-02).** This is the abandoned alternative — HAOS VM on the Mac mini.",
    "The plan decided **HA Green purchased** to keep the always-on hub off the 8GB Mac mini.",
    "Only use this path if the Green hardware fails and you need a temporary VM on the rig (not the mini).",
]
by_id["ha-03"]["verify"] = "Skipped — HA Green is the primary path (ha-02)."

by_id["ha-06"]["steps"] = [
    "Follow configs/homeassistant/nest-sdm-oauth-checklist.md end-to-end (~45–60 min, one sitting).",
    "Google Cloud: create project, enable Smart Device Management API, pay $5 Device Access fee, create OAuth client.",
    "HA → Add Google Nest integration → complete OAuth (redirect via my.home-assistant.io if needed).",
    "Store OAuth client ID/secret + refresh token backup in Bitwarden.",
    "Nest is **cloud-routed** (not local) — acceptable trade-off for thermostat control.",
]
by_id["ha-06"]["files"] = ["configs/homeassistant/nest-sdm-oauth-checklist.md"]

by_id["ha-07"]["steps"] = [
    "Prerequisite: ha-04 (HACS) complete. Follow configs/homeassistant/midea-local-setup.md Path A.",
    "HACS → install **midea_ac_lan** → restart HA.",
    "Static DHCP on IoT VLAN for each Midea unit. Add integration → one-time cloud handshake for V3 token/key.",
    "**Immediately back up** `/config/.storage/midea_ac_lan/*.json` to NAS + Bitwarden — Midea is closing token APIs.",
    "Test local control with Midea cloud blocked on IoT VLAN (after token captured).",
]
by_id["ha-08"]["steps"] = [
    "Optional privacy upgrade after ha-07: replace OEM WiFi dongle with **ESPHome SLWF-01Pro** (~$13).",
    "Flash per configs/homeassistant/esphome-midea-slwf01.yaml (or smlight.tech flasher).",
    "Add ESPHome integration in HA; block original Midea cloud dongle from internet.",
    "Fully cloud-free Midea control — recommended if you are hands-on.",
]

by_id["ha-12"]["steps"] = [
    "Prerequisite: ha-04 complete. Install **Mosquitto** broker add-on on HA Green.",
    "Install **Zigbee2MQTT** add-on; plug USB coordinator into HA Green (Sonoff Zigbee 3.0 Plus-E or HA Connect ZBT-2).",
    "Use a short USB-2 extension cable to avoid USB-3 interference.",
    "Pair first sensor near coordinator, then move it; add mains-powered smart plugs as Zigbee routers (5–7 spread around house).",
    "Z2M → MQTT → HA auto-discovery. Avoid Aqara-branded hubs if mixing brands.",
]

by_id["read-06"]["steps"] = [
    "Prerequisite: read-03, read-04 complete.",
    "CWA must be **nas-09** with `ghcr.io/new-usemame/calibre-web-nextgen:v4.0.7+` (CVE-2026-7713 patched).",
    "Enable KOSync in CWA admin + KOReader cwasync plugin; match username on Kobo.",
    "See scripts/reading/koreader-cwa-wallabag-wiring.md for OPDS/Wallabag wiring.",
]
by_id["read-06"]["verify"] = "KOSync works on patched CWA v4.0.7+; progress syncs across devices."

# --- photos / apps -------------------------------------------------------------
by_id["nas-08"]["depends_on"] = ["nas-01", "nas-00c", "nas-prep-01"]
by_id["nas-08"]["steps"].insert(2, "**At 4GB NAS RAM:** cap ML concurrency + schedule indexing off-peak. Full ML + heavy offloads need 20GB upgrade first.")

by_id["doc-01"]["depends_on"] = ["nas-01", "nas-00c", "nas-prep-01"]
by_id["doc-01"]["steps"] = [
    "Prerequisite: nas-00c, nas-prep-01, Container Manager on NAS.",
    "**GATE:** NAS RAM ≥20GB — defer Paperless until Crucial CT16G4SFD8266 upgrade (cannot share 4GB with Immich ML).",
    "On the rig (24/7) or hold until NAS RAM upgrade — do not OOM the 4GB NAS.",
    "`ssh -t nas 'sudo mkdir -p /volume1/docs/{consume,media,export} /volume1/docker/paperless-ngx'`",
    "Copy configs/docker-stack/stacks/paperless-ngx/ → /volume1/docker/paperless-ngx/; remove external `edge` network; bind /volume1/docs/*.",
    "Set PUID/PGID from `id`, PAPERLESS_SECRET_KEY, PAPERLESS_DBPASS, PAPERLESS_ADMIN_PASSWORD in .env.",
    "`docker compose up -d` on NAS. Drop test PDF in /volume1/docs/consume/ via SMB.",
]
by_id["doc-01"]["verify"] = "http://nas:8000 shows OCR'd searchable PDF; consume folder works via SMB."

# --- backups -------------------------------------------------------------------
by_id["nas-02"]["steps"] = [
    "Prerequisite: nas-01 complete. Backblaze: create **private** B2 bucket + application key; enable **Object Lock** (immutable tier).",
    "DSM → Hyper Backup → Cloud → S3 Compatible → Backblaze B2.",
    "Select **Tier 1 shares on Volume 1:** photo, docs, appdata, backups, vault, home — add Immich dump folder after nas-08.",
    "Enable **client-side encryption**; export .pem to Bitwarden + paper offline.",
    "Schedule daily 03:00. Scope B2 key to this bucket only.",
    "**Tier 2 media (vol2/vol3/vol1 music/books) does NOT go to B2** — see nas-03 for rotated HDD.",
]
by_id["nas-03"]["verify"] = "Weekly job backs up /volume3/tv, /volume2/movies, /volume1/music, /volume1/books to rotated USB."

by_id["nas-06"]["title"] = "Deploy BorgBackup + borgmatic → Hetzner Storage Box (optional 2nd off-site)"
by_id["nas-06"]["steps"] = [
    "Prerequisite: nas-04 complete. **Optional** second off-site path for Linux host backups (B2 via restic is the primary immutable tier).",
    "Order Hetzner Storage Box; enable SSH on port 23.",
    "`ssh mini 'ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_borg -C borgmatic'`",
    "Install borgmatic; copy scripts/backup/borgmatic-config.yaml to /etc/borgmatic/.",
    "Init repo; first backup; enable timer (03:10). Ransomware-proof copy = **B2 Object Lock on restic**, not borg append-only.",
]

# --- ops -----------------------------------------------------------------------
by_id["docker-07"]["title"] = "Deploy AdGuard Home network DNS filtering (chosen over Pi-hole)"
by_id["docker-07"]["verify"] = "AdGuard query log shows blocked ads; upstream becomes unbound:5335 after dns-01."

by_id["docker-08"]["title"] = "Deploy Dockge container manager (chosen default; Dockhand is optional upgrade)"
by_id["docker-08"]["steps"].append(
    "Plan decision: **Dockge** for simple Compose management. Dockhand (configs/docker-stack/alternatives/dockhand/) is the power-user swap-in."
)

by_id["docker-14"]["steps"] = [
    "Prerequisite: docker-06 (Caddy), docker-07, docker-08 complete.",
    "**Decision: Caddy owns ports 80/443 on the Mac mini.** Do NOT let Coolify's bundled proxy bind 80/443.",
    "**Path A (recommended):** ship vibecoded apps as Compose stacks in /opt/stacks + one-line Caddy vhost each.",
    "**Path B (optional):** run Coolify with its proxy on alt ports (8000/8443); Caddy wildcard-proxies *.app.<domain> → Coolify.",
    "Document which path you chose in the control repo.",
]
by_id["docker-14"]["verify"] = "A test app is reachable via Caddy HTTPS without port conflicts."

by_id["dns-01"]["steps"] = [
    "Prerequisite: docker-07 (AdGuard) complete.",
    "**Core (done):** Unbound on mini; AdGuard upstream `unbound:5335`; `*.tabaska.us` rewrites.",
    "Verify: `dig @192.168.10.2 google.com +short` and `dig @192.168.10.2 home.tabaska.us +short`.",
    "**Do not** point UniFi DHCP at AdGuard-only DNS until **dns-03** (fail-open chain) is live.",
    "Resilience: **dns-02 → dns-05** — see configs/network/dns-resilience-plan.md.",
]
by_id["dns-01"]["verify"] = (
    "Mini AdGuard resolves public + internal names. dns-02–dns-05 required before AdGuard-only DHCP."
)

by_id["glue-07"]["steps"] = [
    "MacBook: `pipx install ansible` or `brew install ansible`.",
    "cd ~/Documents/Home/foss-setup/configs/ansible && ansible-galaxy collection install -r requirements.yml",
    "Edit inventory.ini — ansible_host matches ~/.ssh/config aliases (net-14).",
    "`ansible all -i inventory.ini -m ping` — the rig is 24/7 and should answer.",
    "**Scope:** Mac mini + rig + seedbox user-space only — NAS (DSM) and HA (HAOS) are intentionally excluded.",
]
by_id["glue-07"]["files"] = ["configs/ansible/README.md", "configs/ansible/inventory.ini"]

by_id["glue-08"]["steps"] = [
    "Prerequisite: glue-07, glue-06 complete. Each host hostname matches inventory (macmini, cachyos, seedbox).",
    "Edit ansible-pull.service CONTROL_REPO_URL → Forgejo SSH URL from glue-05.",
    "Deploy ansible-pull.service + timer to mini and rig (same OnCalendar schedule on all hosts; Persistent=true is generic catch-up).",
    "Seedbox: optional ansible-pull for user-space compose only (no root/OS on managed box).",
    "`systemctl list-timers ansible-pull.timer` — first run should be check-mode drift report.",
]
by_id["glue-08"]["files"] = ["configs/ansible/ansible-pull.service", "configs/ansible/ansible-pull.timer"]

by_id["sbom-01"]["depends_on"] = ["nas-prep-01", "docker-09"]
by_id["sbom-01"]["steps"].insert(2, "Deploy on **NAS** after 20GB RAM upgrade. On stock 4GB, defer or run DT temporarily on the rig (24/7).")

by_id["sbom-02"]["steps"] = [
    "Prerequisite: sbom-01 complete. Install scripts/inventory/sbom-nightly on mini, rig, and NAS (Container Manager where applicable).",
    "Nightly: `syft dir:/ -o cyclonedx-json` + `syft <image>` per running container → upload to Dependency-Track REST API.",
    "Also export pacman -Qqe, apt-mark showmanual, flatpak list, pinned compose tags → control repo inventory.",
    "On rig: standard nightly timer (Persistent=true catch-up), same as restic.",
]
by_id["sbom-02"]["files"] = ["scripts/inventory/sbom-nightly.sh"]

by_id["sbom-03"]["steps"] = [
    "Prerequisite: glue-05 (Forgejo) complete.",
    "Install etckeeper on mini + rig: auto-commit /etc on every apt/pacman operation.",
    "Set PUSH_REMOTE to private Forgejo repo. **Warning:** /etc contains secrets — repo MUST be private + SOPS for sensitive files.",
]
by_id["sbom-04"]["steps"] = [
    "Prerequisite: glue-05 complete.",
    "Deploy scripts/inventory/export-manifests.sh on each host via cron/systemd timer.",
    "Exports: crontab -l (per user), systemctl list-timers, ~/.config/systemd/user/ → hosts/<box>/ in control repo.",
]
by_id["sbom-05"]["steps"] = [
    "Prerequisite: sbom-02, sbom-03, sbom-04, glue-06 complete.",
    "Write hosts/<box>/restore.md per configs/inventory/restore-runbook-template.md.",
    "Execute one full rebuild drill in a throwaway VM; log gaps; update runbooks in Forgejo.",
    "Drill quarterly — untested runbooks are fiction.",
]
by_id["sbom-05"]["files"] = ["configs/inventory/restore-runbook-template.md"]

# --- security ------------------------------------------------------------------
by_id["sec-01"]["steps"] = [
    "Hardware key (WebAuthn) on crown jewels: Bitwarden, Proton, DSM admin, Tailscale admin, Forgejo admin.",
    "TOTP on: Immich, Plex, Seerr, HA, Bytesized seedbox panel.",
    "Store backup codes offline (paper in fireproof box).",
    "Bitwarden holds: backup encryption keys, HA backup key, SOPS/age key, B2 keys (reference only).",
]
by_id["sec-03"]["steps"] = [
    "Prerequisite: nas-02, nas-06, docker-09 complete.",
    "Enable **B2 Object Lock** on the restic/Hyper Backup bucket (primary immutable 3-2-1-1-0 tier).",
    "Enable **Synology immutable snapshots** on Tier 1 shares (7–14 day lock).",
    "Deploy Healthchecks.io stack; wire restic/borgmatic/Hyper Backup jobs to ping + ntfy on miss.",
]
by_id["sec-04"]["steps"] = [
    "Prerequisite: seed-01, docker-06 complete.",
    "Seedbox (Betty): install CrowdSec if provider allows; protect Deluge WebUI.",
    "Mac mini: CrowdSec on Caddy-facing services; configure forward-auth (Authelia or Pocket-ID) for public vhosts lacking native 2FA.",
    "No blanket port-forwards — Tailscale is the default remote path.",
    "Test: deliberate failed auth triggers ban/forward-auth redirect.",
]
by_id["sec-04"]["files"] = ["configs/docker-stack/stacks/caddy/Caddyfile"]

# --- media-polish --------------------------------------------------------------
# media-04 (Tdarr) REMOVED FROM PLAN 2026-07-08 — re-encoding conflicts with TRaSH
# quality automation; storage not scarce. Entry kept for reference.
by_id["media-04"]["host"] = "NAS"
by_id["media-04"]["title"] = "(Removed from plan) Deploy Tdarr (pre-transcode library; node on the rig)"
by_id["media-04"]["steps"] = [
    "REMOVED FROM PLAN 2026-07-08 — won't-do: re-encoding conflicts with TRaSH quality automation and storage is not scarce. Kept for reference.",
    "Prerequisite: nas-10 (Plex libraries on vol2/vol3), game-08 (rig reachable). **GATE:** NAS RAM ≥20GB recommended.",
    "Deploy **Tdarr server on NAS** (Container Manager) — co-located with media on vol2/vol3.",
    "Copy configs/docker-stack/stacks/tdarr/ → /volume1/docker/tdarr/; adapt compose: mount /volume2/movies and /volume3/tv read-only; TRANSCODE_CACHE on local NAS scratch (not the arrays).",
    "Deploy **Tdarr NVENC node on rig** (see compose comments): restart=no, serverIP=mini Tailscale IP.",
    "Create direct-play-friendly HEVC profile; run test transcode on one file via rig node.",
]
by_id["media-04"]["verify"] = "Tdarr server on NAS lists rig NVENC node; test file transcodes on rig and lands back in library."
# media-03 (Maintainerr) REMOVED FROM PLAN 2026-07-08 — no auto-deletion wanted.
by_id["media-03"]["title"] = "(Removed from plan) Deploy Maintainerr (rule-based library pruning)"
if not by_id["media-03"]["steps"][0].startswith("REMOVED FROM PLAN"):
    by_id["media-03"]["steps"].insert(0, "REMOVED FROM PLAN 2026-07-08 — won't-do: no auto-deletion wanted. Kept for reference.")

# --- gaming --------------------------------------------------------------------
by_id["game-01"]["steps"] = [
    "Prerequisite: docker-01 complete. **Capacity rule:** Mac mini (8GB soldered) hosts **at most ONE light always-on server** — e.g. Paper Minecraft or Terraria.",
    "Follow scripts/gaming/linuxgsm-quickstart.md on the Mac mini.",
    "Install one game only — do not stack multiple servers alongside Seerr/Caddy/AdGuard/LiteLLM.",
    "Expose via **Tailscale only** (game-04) — no port-forward by default.",
]
by_id["game-01"]["verify"] = "One light server runs on mini without OOM; friends join via tailnet."

by_id["game-02"]["title"] = "(Optional) Pelican Panel on rig for heavy servers"
by_id["game-02"]["steps"] = [
    "Prerequisite: game-08 complete. **Optional** — only if you want a web UI for spinning up many game types.",
    "Deploy Pelican on the **CachyOS rig** (24/7), not the Mac mini.",
    "The rig is 24/7 — the panel is available whenever you need it.",
]

by_id["game-03"]["title"] = "Run heavy game servers on the CachyOS rig"
by_id["game-03"]["steps"] = [
    "Prerequisite: game-08 complete.",
    "Heavy servers (Valheim, Factorio, Palworld, ARK, modded packs) run on the **rig only**.",
    "Start server → friends join via Tailscale (the rig is 24/7).",
    "Never run heavy servers 24/7 on the Mac mini (8GB) or NAS.",
]

by_id["ai-01"]["steps"] = [
    "Prerequisite: ha-17 (LiteLLM) complete. All on the **rig** (24/7) unless noted.",
    "**ComfyUI:** image generation on the rig (NVENC).",
    "**Continue/Aider:** point at LiteLLM endpoint (http://mini:4000) for coding assistant.",
    "**Open WebUI RAG:** upload Obsidian vault / Paperless exports for local doc Q&A.",
    "Set OLLAMA_KEEP_ALIVE=0 on rig so VRAM frees between sessions (game-13 contention policy).",
    "Voice/quick queries use LiteLLM → small Mac-mini model as a resilience fallback if the rig is down.",
]
by_id["ai-01"]["verify"] = "ComfyUI generates an image; Continue answers via LiteLLM; rig VRAM clears after idle."

# --- media pipeline extras -----------------------------------------------------
by_id["nas-24"]["steps"] = [
    "Prerequisite: nas-22 and nas-09 (CWA) complete.",
    "Readarr → Settings → Development → metadata provider: `http://rreading-glasses:8788` (self-hosted, not public).",
    "Download client: remote Deluge label **readarr**; Remote Path Mapping as other *arrs.",
    "Bootstrap root folder: **/cwa-book-ingest** (works for first import test).",
    "For production — permanent Readarr inventory, CWA copy-on-import, and Libreseerr requests — complete the **ebook-mgmt** workstream (ebook-01–ebook-06).",
    "Book automation is less reliable than video — expect occasional manual metadata fixes (Readarr is retired upstream).",
    "Verify: file in ingest **and** processed into `/volume1/books` (CWA must be running — nas-09).",
]
by_id["nas-25"]["steps"] = [
    "Prerequisite: nas-22 complete.",
    "Edit /volume1/docker/media-automation/unpackerr/unpackerr.conf — fill Sonarr/Radarr/Lidarr/Readarr API keys.",
    "`docker compose up -d unpackerr` on NAS.",
    "Test: Deluge label with RAR release → Unpackerr extracts → *arr imports.",
]
by_id["nas-27"]["steps"] = [
    "Prerequisite: nas-22 through nas-26 complete.",
    "Run self-check from configs/nas/media-automation/README.md (docker inspect mounts section).",
    "Confirm: /seedbox on sonarr/radarr/lidarr/readarr/unpackerr; per-volume roots; one scheduled rclone job (manual only).",
    "Soulseek stack (seed-09, nas-29, nas-30) is verified separately — not a blocker for this core self-check.",
    "Report violations — do not silently fix drift.",
]

# --- gaming (expand thin tasks) ------------------------------------------------
by_id["game-04"]["steps"] = [
    "Prerequisite: game-01 complete.",
    "**Default: Tailscale only** — invite friends to your tailnet or share just the game-server node.",
    "No Dream Wall port-forwards unless you deliberately need public/many-player (then use Playit.gg tunnel instead of exposing home IP).",
    "Document which game ports each server uses; keep server host on Trusted VLAN.",
]
by_id["game-06"]["steps"] = [
    "Prerequisite: game-05 complete.",
    "Install Moonlight on phone, laptop, Apple TV — **same Trusted VLAN as the rig** for in-home (mDNS auto-discovery).",
    "Pair with the Apollo PIN from first launch.",
    "Wire the client near the TV if possible — latency matters more than WiFi for couch streaming.",
]
by_id["game-07"]["steps"] = [
    "Prerequisite: game-05, game-06 complete.",
    "In Moonlight, add the rig manually by its **Tailscale IP** (100.x.x.x) — mDNS does not work over Tailscale.",
    "Run `tailscale ping rig --until-direct` — must show **direct**, not DERP relay (relays ruin throughput).",
    "If relayed: forward UDP 41641 on Dream Wall to the rig, or use Tailscale Peer Relay as fallback.",
]
# game-09 rescoped 2026-07-08: auto-suspend closed as won't-do (rig is 24/7);
# task is now idle-power tuning of the 24/7 baseline.
by_id["game-09"]["title"] = "Rig idle-power tuning (24/7 baseline)"
by_id["game-09"]["steps"] = [
    "Rig runs 24/7 (decision 2026-07-08: ~130W idle ≈ $23/mo accepted for availability) — auto-suspend is closed as won't-do.",
    "Fix the plasmashell busy-loop that burns CPU at idle.",
    "Headless/greeter idle-power pass — no desktop session left logged in when idle.",
    "Measure idle draw at the wall (smart plug / Kill-A-Watt).",
    "Target <100W idle.",
]
by_id["game-09"]["commands"] = ["ssh rig 'top -bn1 | head -15'"]
by_id["game-09"]["docs"] = [{"title": "Arch Wiki: Power management", "url": "https://wiki.archlinux.org/title/Power_management"}]
by_id["game-09"]["verify"] = "Wall measurement shows <100W idle; plasmashell no longer busy-looping."
by_id["game-11"]["steps"] = [
    "Prerequisite: game-05 complete.",
    "**Simplest (headless rig):** use Apollo's built-in virtual display — set `capture=kms` for Wayland headless; no dummy HDMI dongle needed.",
    "**Alt path:** a dummy HDMI dongle or EVDI virtual display if you want the GPU to see a fixed physical output.",
    "Add PipeWire virtual sink if no audio device (headless capture needs a sink).",
]
by_id["game-12"]["steps"] = [
    "Prerequisite: read-02 (Syncthing on rig) complete.",
    "Install Ludusavi on rig + clients (Steam Deck, laptop). Point backup folder at a Syncthing-shared directory.",
    "Back up before a session; restore on the other device — self-hosted Steam Cloud.",
]
by_id["game-13"]["steps"] = [
    "Prerequisite: game-05, ha-17 complete.",
    "One GPU, three jobs: Apollo stream, game servers, Ollama inference — set explicit rules.",
    "Ollama on rig: `OLLAMA_KEEP_ALIVE=0` so VRAM frees immediately after each request.",
    "Do not run heavy inference during an active Apollo session or game server.",
    "LiteLLM on Mac mini is the resilience fallback if the rig is ever down (ha-17).",
]
by_id["game-14"]["steps"] = [
    "Prerequisite: game-05 complete.",
    "Install Heroic (GOG/Epic) or Lutris on rig; add games to the Apollo Applications list for couch streaming.",
    "Optional: deploy RomM on Mac mini for retro library metadata + EmulatorJS; stream/play from Moonlight.",
]

# --- reading / security / smart-home thin tasks --------------------------------
by_id["read-08"]["steps"] = [
    "Prerequisite: read-04, read-07 complete.",
    "KOReader → Wallabag plugin → URL http://macmini.<tailnet>:8200 (or Caddy vhost).",
    "Wallabag → Settings → API → create token; paste into KOReader plugin on Kobo.",
    "See scripts/reading/koreader-cwa-wallabag-wiring.md.",
]
by_id["read-09"]["steps"] = [
    "Prerequisite: read-04, docker-04 complete.",
    "Miniflux → Settings → API → create key.",
    "KOReader news plugin → Miniflux API URL http://macmini.<tailnet>:8082 + key.",
]
by_id["read-10"]["steps"] = [
    "`scp ~/Documents/Home/foss-setup/scripts/media/install-ipod-tools-cachyos.sh rig:~/`",
    "`ssh rig 'bash ~/install-ipod-tools-cachyos.sh'` — installs Rhythmbox + libgpod.",
    "Verify Rhythmbox iPod plugin enabled (Preferences → Plugins → Portable Players).",
    "See scripts/media/ipod-sync-cachyos.md for FirewireGuid/SysInfoExtended first-time setup.",
]
by_id["sec-02"]["steps"] = [
    "Prerequisite: docker-01 complete.",
    "Set `/etc/docker/daemon.json` on mini + rig (and NAS Container Manager if supported): `\"log-driver\":\"json-file\",\"log-opts\":{\"max-size\":\"10m\",\"max-file\":\"3\"}`",
    "Restart Docker; recreate running containers so limits apply.",
    "Prevents a noisy container from silently filling disks.",
]
by_id["ha-10"]["steps"] = [
    "Prerequisite: ha-05, ha-07 complete.",
    "Settings → Dashboards → Energy → add grid consumption.",
    "Add Emporia Vue circuits (plan: whole-home + key circuits) if integrated.",
    "Add smart-plug monitors from Zigbee devices as they land.",
    "Useful for validating Section 5 power estimates (always-on ~$150–200/yr; rig 24/7 ~130W idle ≈ $23/mo, tuning target <100W).",
]

by_id["game-10"]["steps"] = [
    "3090 Ti can idle at ~100W+ on Linux if stuck in high-power state — target ~20–30W at idle.",
    "`scp ~/Documents/Home/foss-setup/scripts/gaming/gpu-power-tune.sh ~/Documents/Home/foss-setup/scripts/gaming/gpu-power-tune.service rig:~/`",
    "Install gpu-power-tune.service on rig (persistence mode, power limit, optional undervolt).",
    "Verify at idle: `nvidia-smi` shows reduced draw; survives reboot.",
]
by_id["game-10"]["files"] = ["scripts/gaming/gpu-power-tune.sh", "scripts/gaming/gpu-power-tune.service"]

# --- HTML reference tabs (Features / Hardware) ---------------------------------
HTML_PATCHES = [
    (
        '<h4>Seedbox "Betty" — Bytesized Stream +3</h4><p>3000 GB, 6-10 TB/mo upload cap, €16/mo. <b>Deluge only</b> — downloads and seeds off-site. NAS *arr stack grabs via Deluge API and imports through an rclone SFTP mount. ISP never sees a swarm.</p>',
        '<h4>Seedbox "Betty" — Bytesized Stream +3</h4><p>3000 GB, 6-10 TB/mo upload cap, €16/mo. <b>Deluge + slskd</b> — torrent and Soulseek P2P off-site. NAS *arr stack + Soularr import via rclone SFTP mount. ISP never sees a swarm.</p>',
    ),
    (
        "<td>Off-site Deluge only (P2P + seeding buffer); NAS *arr stack imports via rclone mount</td>",
        "<td>Off-site Deluge + slskd (P2P); NAS *arr + Soularr import via rclone mount</td>",
    ),
    (
        "<td>Music — acquisition + import/organize (Lidarr-only)</td>",
        "<td>Music — Lidarr + Soularr (torrents + Soulseek)</td>",
    ),
    (
        "<tr><td>Lidarr</td><td>NAS</td><td class=\"num\">8686</td><td>TCP</td><td>Music — acquisition + import/organize (Lidarr-only)</td></tr>\n        <tr><td>Readarr</td>",
        "<tr><td>Lidarr</td><td>NAS</td><td class=\"num\">8686</td><td>TCP</td><td>Music — Lidarr + Soularr (torrents + Soulseek)</td></tr>\n        <tr><td>Soularr</td><td>NAS</td><td class=\"num\">—</td><td>—</td><td>Soulseek bridge (Lidarr ↔ slskd on Betty)</td></tr>\n        <tr><td>beets</td><td>NAS</td><td class=\"num\">8337</td><td>TCP</td><td>Tag-only metadata on /music (optional profile)</td></tr>\n        <tr><td>Readarr</td>",
    ),
    (
        "<p class=\"panel-sub\"><b>Deluge only.</b> Betty downloads and seeds — nothing else is installed here. The NAS *arr stack (Sonarr/Radarr/Lidarr/Readarr/Prowlarr) searches indexers, sends grabs to Deluge over its API, and imports completed files through a persistent rclone SFTP mount at <code>/volume1/mounts/seedbox-files</code>. No Sonarr, Radarr, Prowlarr, qBittorrent, Bazarr, slskd, or sync agents on the seedbox.</p>",
        "<p class=\"panel-sub\"><b>Deluge + slskd.</b> Betty runs torrent (Deluge) and Soulseek (slskd) P2P off-site. The NAS *arr stack searches indexers and sends torrent grabs to Deluge; <b>Soularr</b> on the NAS drives remote slskd for Soulseek. All imports use the rclone SFTP mount at <code>/volume1/mounts/seedbox-files</code>. No *arr apps, Soularr, or beets on Betty.</p>",
    ),
    (
        "<tr><td>Automated music acquisition</td><td>Request an album in Seerr; Lidarr on the NAS searches indexers, Deluge downloads off-site, and the NAS imports into /music for Plex and Navidrome — no slskd or Soularr.</td><td>Lidarr + Deluge (seedbox)</td><td>NAS + seedbox</td></tr>",
        "<tr><td>Automated music acquisition</td><td>Request an album in <b>MusicSeerr</b> → Lidarr on the NAS. <b>Torrents:</b> Deluge on Betty → /seedbox/music/. <b>Soulseek:</b> Soularr on NAS → slskd on Betty → /seedbox/slskd/ → /music. Optional beets tag pass. (Seerr = movies/TV only.)</td><td>MusicSeerr + Lidarr + Soularr + slskd + beets</td><td>Mac mini + NAS + seedbox</td></tr>",
    ),
    (
        "Betty seedbox, NAS *arr import stack, Plex on the NAS, and Seerr requests — no P2P at home.",
        "Betty (Deluge + slskd), NAS *arr + Soularr, optional beets, Plex, Seerr + MusicSeerr — no P2P at home.",
    ),
    (
        "<tr><td>Deluge (download + seed ONLY)</td><td>Seedbox \"Betty\" (off-site)</td>",
        "<tr><td>Deluge (torrents)</td><td>Seedbox \"Betty\" (off-site)</td>",
    ),
    (
        '<tr><td>slskd (Soulseek)</td><td>Seedbox "Betty" (off-site)</td><td class="num">5030 / 50300</td><td>TCP</td><td>P2P off-site; Soularr on NAS drives API over Tailscale</td></tr>',
        '<tr><td>slskd (Soulseek)</td><td>Seedbox "Betty" (off-site, native binary)</td><td class="num">5030 / 50300</td><td>TCP</td><td>:50300 P2P (host-bound); :5030 API on tailnet or SSH tunnel; Soularr on NAS</td></tr>',
    ),
    (
        "Reached by *arr API; files pulled via rclone SFTP mount</td></tr>\n      </tbody>",
        "Reached by *arr API; files via rclone SFTP mount</td></tr>\n        <tr><td>slskd (Soulseek)</td><td>Seedbox \"Betty\" (off-site, native binary)</td><td class=\"num\">5030 / 50300</td><td>TCP</td><td>:50300 P2P (host-bound); :5030 API on tailnet or SSH tunnel; Soularr on NAS</td></tr>\n      </tbody>",
    ),
    (
        "Frigate (camera AI — iGPU, or Mac mini + Coral)",
        "Frigate (camera AI — NAS Quick Sync iGPU; optional Coral on Mac mini)",
    ),
    (
        "LinuxGSM light servers (Minecraft · Valheim · Terraria · Factorio · Project Zomboid · Core Keeper)",
        "One LinuxGSM light server max (e.g. Minecraft or Terraria — 8GB Mac mini limit)",
    ),
    (
        "<td>AdGuard Home / Pi-hole</td><td>Ubuntu</td>",
        "<td>AdGuard Home (primary; Pi-hole in alternatives/)</td><td>Ubuntu</td>",
    ),
    (
        "<td>Unbound + AdGuard/Pi-hole</td><td>Ubuntu / NAS</td>",
        "<td>Unbound + AdGuard Home</td><td>Ubuntu (+ optional NAS secondary)</td>",
    ),
    (
        "<td>Dockge / Dockhand</td><td>Ubuntu</td>",
        "<td>Dockge (Dockhand optional upgrade)</td><td>Ubuntu</td>",
    ),
    (
        "<td>Recyclarr + Unpackerr + Kometa + Tdarr</td><td>Mac mini + NAS + rig</td>",
        "<td>Recyclarr + Kometa (Mac mini) + Unpackerr (NAS) + Tdarr (NAS server + rig NVENC node)</td><td>Mac mini + NAS + rig</td>",
    ),
    (
        "<td>UniFi Protect → HA (+ optional Frigate)</td><td>Dream Wall / HA (Frigate: NAS iGPU or Mac mini + Coral)</td>",
        "<td>UniFi Protect → HA (+ optional Frigate)</td><td>Dream Wall / HA (Frigate: NAS Quick Sync primary)</td>",
    ),
    (
        "<tr><td>Tdarr</td><td>Mac mini</td><td class=\"num\">8265 / 8266</td><td>TCP</td><td>Transcode server + node comms</td></tr>",
        "<tr><td>Tdarr</td><td>NAS</td><td class=\"num\">8265 / 8266</td><td>TCP</td><td>Transcode server (rig runs NVENC node)</td></tr>",
    ),
    (
        "<td>Pinchflat (yt-dlp)</td><td>NAS / Mac mini</td>",
        "<td>Pinchflat (yt-dlp)</td><td>Mac mini (NFS → /volume1/youtube)</td>",
    ),
    (
        "<td>Proton (or Nextcloud / Syncthing + Baikal)</td><td>Cloud / NAS</td>",
        "<td>Proton + Syncthing (Nextcloud optional)</td><td>Cloud + local</td>",
    ),
    (
        "<td>Game servers</td><td>Rig / Mac mini</td>",
        "<td>Game servers</td><td>Rig (heavy) · one light server max on Mac mini</td>",
    ),
    (
        "<tr><td>Seerr</td><td>Mac mini</td><td class=\"num\">5055</td><td>TCP</td><td>Media requests</td></tr>",
        "<tr><td>Seerr</td><td>Mac mini</td><td class=\"num\">5055</td><td>TCP</td><td>Movie/TV requests (Radarr/Sonarr)</td></tr>\n        <tr><td>MusicSeerr</td><td>Mac mini</td><td class=\"num\">8688</td><td>TCP</td><td>Album requests (Lidarr)</td></tr>",
    ),
    (
        "Light Docker host: Seerr, Miniflux, Navidrome, Mealie, Caddy, AdGuard + Unbound, monitoring, Forgejo.",
        "Light Docker host: Seerr, MusicSeerr, Miniflux, Navidrome, Mealie, Caddy, AdGuard + Unbound, monitoring, Forgejo.",
    ),
    (
        "<span class=\"sw\">Seerr</span>",
        "<span class=\"sw\">Seerr</span>\n        <span class=\"sw\">MusicSeerr</span>",
    ),
]

# --- glue-04 / glue-04b: MacBook bootstrap + fleet rollout follow-on ------------
by_id["glue-04"]["title"] = "Version-controlled dotfiles with chezmoi — MacBook bootstrap"
by_id["glue-04"]["estimate"] = "30-60 min"
by_id["glue-04"]["steps"] = [
    "On your MacBook: open this task's verify block and keep the repo at ~/Documents/Home/foss-setup handy.",
    "MacBook: `brew install chezmoi` (or `~/Documents/Home/foss-setup/scripts/dotfiles/bootstrap-dotfiles.sh` with `CHEZMOI_NO_APPLY=1`).",
    "`chezmoi init` — import live configs: `chezmoi add ~/.config/fish ~/.config/nvim ~/.config/alacritty ~/.gitconfig` (adjust paths).",
    "Add homelab SSH config: `cp ~/Documents/Home/foss-setup/configs/network/ssh-config.example ~/.ssh/config`, edit tailnet/users, `chezmoi add --encrypt ~/.ssh/config` (age key in Proton Pass).",
    "`chezmoi apply` → `chezmoi cd` → commit and push to GitHub (`git branch -M main` if branch is still `master`).",
    "MacBook verify: `chezmoi diff` empty; `chezmoi managed` lists fish/nvim/alacritty/ssh/gitconfig.",
    "Continue to **glue-04b** to bootstrap the CachyOS rig and Mac mini.",
]
by_id["glue-04"]["commands"] = [
    "brew install chezmoi",
    "chezmoi init",
    "chezmoi add ~/.config/fish ~/.config/nvim ~/.config/alacritty ~/.gitconfig",
    "cp ~/Documents/Home/foss-setup/configs/network/ssh-config.example ~/.ssh/config",
    "chezmoi apply",
    "chezmoi cd && git branch -M main && git push -u origin main",
    "chezmoi diff",
    "chezmoi status",
]
by_id["glue-04"]["files"] = [
    "scripts/dotfiles/bootstrap-dotfiles.sh",
    "scripts/dotfiles/chezmoi-quickstart.md",
    "configs/network/ssh-config.example",
]
by_id["glue-04"]["verify"] = (
    "GitHub `btabaska/dotfiles` has chezmoi source layout; MacBook `chezmoi diff` is empty."
)

by_id["glue-04b"] = {
    "id": "glue-04b",
    "title": "Apply chezmoi dotfiles to rig + mini (fleet rollout)",
    "host": "any",
    "type": "async",
    "depends_on": ["glue-04"],
    "estimate": "20-30 min",
    "steps": [
        "On your MacBook: open this task's verify block and keep the repo at ~/Documents/Home/foss-setup handy.",
        "Prerequisite: glue-04 complete.",
        "**Before bootstrapping other hosts:** confirm the age private key (`~/.config/chezmoi/key.txt`) is backed up in Proton Pass — encrypted SSH config won't decrypt without it.",
        "**CachyOS rig** (fish/nvim/alacritty + ssh): `scp ~/Documents/Home/foss-setup/scripts/dotfiles/bootstrap-dotfiles.sh rig:/tmp/` then `ssh rig 'DOTFILES_REPO=btabaska bash /tmp/bootstrap-dotfiles.sh'`.",
        "**Mac mini** (ssh + gitconfig): `scp ~/Documents/Home/foss-setup/scripts/dotfiles/bootstrap-dotfiles.sh mini:/tmp/` then `ssh mini 'DOTFILES_REPO=btabaska bash /tmp/bootstrap-dotfiles.sh'`.",
        "On each host after bootstrap: copy age key from Proton Pass to `~/.config/chezmoi/key.txt` if SSH config is encrypted, then `chezmoi apply`.",
        "Verify fleet-wide from MacBook: `ssh rig 'chezmoi diff && chezmoi status'` and `ssh mini 'chezmoi diff && chezmoi status'` — both diffs must be empty.",
        "Test SSH aliases: `ssh mini hostname`, `ssh rig hostname`.",
        "**Ongoing sync:** edit on one box → `chezmoi edit` → `chezmoi apply` → `chezmoi cd && git push`; on others → `chezmoi update`. Use `.tmpl` files for per-host differences (see chezmoi-quickstart.md).",
        "glue-08 ansible-pull will automate `chezmoi init --apply` later; manual bootstrap is fine until Forgejo (glue-05) is up.",
        "From MacBook: confirm completion matches the verify block before checking this task done.",
    ],
    "commands": [
        "scp ~/Documents/Home/foss-setup/scripts/dotfiles/bootstrap-dotfiles.sh rig:/tmp/",
        "ssh rig 'DOTFILES_REPO=btabaska bash /tmp/bootstrap-dotfiles.sh'",
        "scp ~/Documents/Home/foss-setup/scripts/dotfiles/bootstrap-dotfiles.sh mini:/tmp/",
        "ssh mini 'DOTFILES_REPO=btabaska bash /tmp/bootstrap-dotfiles.sh'",
        "ssh rig 'chezmoi diff && chezmoi status'",
        "ssh mini 'chezmoi diff && chezmoi status'",
        "ssh mini 'hostname'",
        "ssh rig 'hostname'",
    ],
    "files": [
        "scripts/dotfiles/bootstrap-dotfiles.sh",
        "scripts/dotfiles/chezmoi-quickstart.md",
        "configs/network/ssh-config.example",
        "configs/network/ssh-maintenance-access.md",
    ],
    "docs": [
        {"title": "chezmoi", "url": "https://www.chezmoi.io/"},
        {"title": "chezmoi templating", "url": "https://www.chezmoi.io/user-guide/templating/"},
    ],
    "verify": "`chezmoi diff` empty on rig and mini; `ssh mini` / `ssh rig` work from MacBook.",
    "track": "desktop",
    "required": False,
}

# --- MusicSeerr stack (Mac mini) + wiring + E2E --------------------------------
MUSICSEERR_TASK_DEFS = {
    "docker-16": {
        "id": "docker-16",
        "title": "Deploy MusicSeerr on Mac mini (album request portal)",
        "host": "Ubuntu",
        "type": "sync",
        "depends_on": ["docker-02", "nas-00d", "nas-23"],
        "estimate": "20-30 min",
        "steps": [
            "Prerequisite: docker-02, nas-00d (NFS export /volume1/music), nas-23 (Lidarr torrent path) complete.",
            "On Mac mini mount NAS music: `sudo mkdir -p /mnt/nas/music` + fstab "
            "`192.168.10.4:/volume1/music /mnt/nas/music nfs defaults,_netdev 0 0` (same as Navidrome docker-05).",
            "`scp -r ~/Documents/Home/foss-setup/configs/docker-stack/stacks/musicseerr mini:/tmp/musicseerr`",
            "`ssh mini 'sudo mkdir -p /opt/stacks/musicseerr && sudo rsync -a /tmp/musicseerr/ /opt/stacks/musicseerr/'`",
            "`ssh mini 'cd /opt/stacks/musicseerr && cp -n .env.example .env'` — MUSIC_FOLDER=/mnt/nas/music",
            "`ssh mini 'cd /opt/stacks/musicseerr && docker compose up -d'`",
            "Browse http://macmini.<tailnet>:8688 — create admin on first launch.",
        ],
        "commands": [
            "scp -r ~/Documents/Home/foss-setup/configs/docker-stack/stacks/musicseerr mini:/tmp/musicseerr",
            "ssh mini 'sudo rsync -a /tmp/musicseerr/ /opt/stacks/musicseerr/'",
            "ssh mini 'cd /opt/stacks/musicseerr && cp -n .env.example .env && docker compose up -d'",
            "ssh mini 'curl -sf http://127.0.0.1:8688/health'",
        ],
        "files": [
            "configs/docker-stack/stacks/musicseerr/compose.yaml",
            "configs/docker-stack/stacks/musicseerr/.env.example",
            "configs/seedbox/music-pipeline.md",
        ],
        "docs": [{"title": "MusicSeerr", "url": "https://musicseerr.com/docs/getting-started/"}],
        "verify": "MusicSeerr :8688 healthy; admin account created.",
        "track": "media-pipeline",
        "required": False,
    },
    "seed-06": {
        "id": "seed-06",
        "title": "Connect MusicSeerr to NAS Lidarr + Plex/Navidrome",
        "host": "Ubuntu",
        "type": "sync",
        "depends_on": ["docker-16", "nas-23", "nas-10"],
        "estimate": "20-30 min",
        "steps": [
            "Open MusicSeerr at http://<mac-mini>:8688 → Settings.",
            "Connect **Lidarr**: http://192.168.10.4:8686 + API key (Lidarr → Settings → General); root folder **/music**.",
            "Optional **Plex**: NAS http://<nas>:32400 + token — Plex Music availability badges.",
            "Optional **Navidrome**: http://navidrome:4533 (docker-05; same edge network on Mac mini).",
            "Optional local playback: Settings → Local Files → /music (NFS mount in compose).",
            "Request a test album → confirm NAS Lidarr Activity (not Betty).",
        ],
        "commands": [
            "LIDARR_KEY=$(ssh nas 'grep -oP \"(?<=<ApiKey>)[^<]+\" /volume1/docker/lidarr/config/config.xml')",
            "curl -s 'http://192.168.10.4:8686/api/v1/system/status' -H \"X-Api-Key: $LIDARR_KEY\"",
        ],
        "files": ["configs/seedbox/music-pipeline.md", "configs/nas/media-automation/README.md"],
        "docs": [{"title": "MusicSeerr", "url": "https://musicseerr.com/docs/getting-started/"}],
        "verify": "MusicSeerr request appears in NAS Lidarr Activity.",
        "track": "media-pipeline",
        "required": False,
    },
    "seed-10": {
        "id": "seed-10",
        "title": "End-to-end music verification (MusicSeerr → Betty → NAS → Plex/Navidrome)",
        "host": "NAS",
        "type": "sync",
        "depends_on": ["seed-06", "nas-29", "docker-05"],
        "estimate": "30-45 min",
        "steps": [
            "Prerequisites: rclone mount (nas-20), Lidarr torrent path (nas-23), Soularr (nas-29), MusicSeerr (seed-06), Plex Music (nas-10) + Navidrome (docker-05).",
            "**Torrent path:** Request small album in MusicSeerr → Lidarr Wanted → Deluge label lidarr on Betty → import from /seedbox/music/ → /volume1/music.",
            "**Soulseek path:** Add album to Lidarr Wanted → Soularr searches slskd → files/slskd/ → Lidarr import from /seedbox/slskd/.",
            "Confirm album in Plex Music and Navidrome; optional beet write (nas-30).",
        ],
        "commands": [
            "ssh nas 'ls /volume1/mounts/seedbox-files/music /volume1/mounts/seedbox-files/slskd'",
            "ssh seedbox 'ls ~/files/music ~/files/slskd'",
        ],
        "files": ["configs/seedbox/music-pipeline.md", "configs/nas/plex/README.md"],
        "verify": "Album playable in Plex Music and Navidrome via torrent or Soulseek path.",
        "track": "media-pipeline",
        "required": False,
    },
}
for tid, body in MUSICSEERR_TASK_DEFS.items():
    by_id[tid] = body

# --- Ebook Management Improvements (ebook-mgmt workstream) ---------------------
EBOOK_TASK_DEFS = {
    "ebook-01": {
        "id": "ebook-01",
        "title": "Add Readarr permanent library mount (compose + paths)",
        "host": "NAS",
        "type": "sync",
        "depends_on": ["nas-24", "nas-09"],
        "estimate": "20-30 min",
        "steps": [
            "Prerequisite: nas-24 (Readarr wired) and nas-09 (CWA running) complete.",
            "On NAS: `sudo mkdir -p /volume1/docker/readarr/{library,scripts}`",
            "Copy repo updates: media-automation compose adds `/readarr-library`, `/cwa-book-ingest`, and `/scripts` mounts.",
            "Add `READARR_LIBRARY=/volume1/docker/readarr/library` to `/volume1/docker/media-automation/.env`.",
            "Stage copy script: `scripts/media/readarr-copy-to-cwa-ingest.sh` → `/volume1/docker/readarr/scripts/` (chmod +x).",
            "`docker compose up -d readarr` — confirm `docker inspect readarr` shows `/readarr-library` and `/cwa-book-ingest`.",
        ],
        "commands": [
            "ssh -t nas 'sudo mkdir -p /volume1/docker/readarr/{library,scripts}'",
            "cd ~/Documents/Home/foss-setup && scp scripts/media/readarr-copy-to-cwa-ingest.sh nas:/tmp/",
            "ssh -t nas 'sudo install -m 755 /tmp/readarr-copy-to-cwa-ingest.sh /volume1/docker/readarr/scripts/'",
            "ssh nas 'cd /volume1/docker/media-automation && sudo /usr/local/bin/docker compose up -d readarr'",
        ],
        "files": [
            "configs/nas/media-automation/docker-compose.yml",
            "configs/nas/media-automation/.env.example",
            "scripts/media/readarr-copy-to-cwa-ingest.sh",
        ],
        "docs": [
            {"title": "CWA + Readarr workflow", "url": "https://github.com/crocodilestick/Calibre-Web-Automated/discussions/248"},
        ],
        "verify": "Readarr container mounts /readarr-library, /cwa-book-ingest, and /scripts; host library dir exists.",
        "track": "ebook-mgmt",
        "required": False,
    },
    "ebook-02": {
        "id": "ebook-02",
        "title": "Wire Readarr Connect copy script (import → CWA ingest)",
        "host": "NAS",
        "type": "sync",
        "depends_on": ["ebook-01"],
        "estimate": "15-20 min",
        "steps": [
            "Prerequisite: ebook-01 complete.",
            "Readarr → Settings → Connect → **+** → **Custom Script**.",
            "Name: `Copy to CWA ingest`; Path: `/scripts/readarr-copy-to-cwa-ingest.sh`.",
            "Triggers: **On Import** and **On Upgrade** only (not On Grab — file paths do not exist yet).",
            "Click **Test** — check `/volume1/docker/readarr/config/logs/readarr-copy-to-cwa-ingest.log` for `Test event`.",
            "Optional: trigger a small test import and confirm a copy appears in ingest while the original stays in `/readarr-library`.",
        ],
        "commands": [
            "ssh nas 'tail -20 /volume1/docker/readarr/config/logs/readarr-copy-to-cwa-ingest.log 2>/dev/null || echo run Test in Readarr Connect first'",
        ],
        "files": ["scripts/media/readarr-copy-to-cwa-ingest.sh"],
        "docs": [
            {"title": "readarr_addedbookpaths script", "url": "https://github.com/crocodilestick/Calibre-Web-Automated/discussions/248"},
        ],
        "verify": "Connect Test succeeds; log shows Test event; import copies to ingest without removing Readarr's file.",
        "track": "ebook-mgmt",
        "required": False,
    },
    "ebook-03": {
        "id": "ebook-03",
        "title": "Migrate Readarr root folder to /readarr-library",
        "host": "NAS",
        "type": "sync",
        "depends_on": ["ebook-02"],
        "estimate": "20-30 min",
        "steps": [
            "Prerequisite: ebook-02 complete (copy script tested).",
            "Readarr → Settings → Media Management → Root Folders: add **`/readarr-library`**, set as default.",
            "Remove **`/cwa-book-ingest`** as a root folder (ingest is CWA-only; Readarr must not import directly there).",
            "Existing books imported to ingest-as-root: either re-import under `/readarr-library` or add to Readarr manually — titles already in `/volume1/books` via CWA do not need re-downloading.",
            "Request or import one test book — confirm file lands in `/volume1/docker/readarr/library` **and** a copy reaches ingest → CWA → `/volume1/books`.",
            "Confirm Readarr still shows the book as **Downloaded** after CWA ingests (no Missing badge).",
        ],
        "commands": [
            "ssh nas 'ls /volume1/docker/readarr/library /volume1/docker/calibre-web-automated/ingest /volume1/books'",
        ],
        "files": ["configs/nas/media-automation/README.md"],
        "verify": "Readarr root is /readarr-library only; post-CWA ingest the title stays Downloaded in Readarr.",
        "track": "ebook-mgmt",
        "required": False,
    },
    "ebook-04": {
        "id": "ebook-04",
        "title": "Deploy Libreseerr on Mac mini (book request portal)",
        "host": "Ubuntu",
        "type": "sync",
        "depends_on": ["docker-02", "ebook-03"],
        "estimate": "20-30 min",
        "steps": [
            "Prerequisite: docker-02 and ebook-03 (Readarr on /readarr-library) complete.",
            "`scp -r ~/Documents/Home/foss-setup/configs/docker-stack/stacks/libreseerr mini:/tmp/libreseerr`",
            "`ssh mini 'sudo mkdir -p /opt/stacks/libreseerr && sudo rsync -a /tmp/libreseerr/ /opt/stacks/libreseerr/'`",
            "`ssh mini 'cd /opt/stacks/libreseerr && cp -n .env.example .env'` — set SECRET_KEY (`openssl rand -hex 32`).",
            "`ssh mini 'cd /opt/stacks/libreseerr && docker compose up -d'`",
            "Browse http://macmini.<tailnet>:8789 — log in (default admin/admin) and **change the password immediately**.",
        ],
        "commands": [
            "scp -r ~/Documents/Home/foss-setup/configs/docker-stack/stacks/libreseerr mini:/tmp/libreseerr",
            "ssh mini 'sudo rsync -a /tmp/libreseerr/ /opt/stacks/libreseerr/'",
            "ssh mini 'cd /opt/stacks/libreseerr && cp -n .env.example .env && docker compose up -d'",
            "ssh mini 'curl -sf http://127.0.0.1:8789/ || curl -sf http://127.0.0.1:5000/'",
        ],
        "files": [
            "configs/docker-stack/stacks/libreseerr/compose.yaml",
            "configs/docker-stack/stacks/libreseerr/.env.example",
        ],
        "docs": [{"title": "Libreseerr", "url": "https://github.com/zamnzim/Libreseerr"}],
        "verify": "Libreseerr :8789 healthy; admin password changed from default.",
        "track": "ebook-mgmt",
        "required": False,
    },
    "ebook-05": {
        "id": "ebook-05",
        "title": "Connect Libreseerr to NAS Readarr (+ optional Plex Books)",
        "host": "Ubuntu",
        "type": "sync",
        "depends_on": ["ebook-04", "nas-10"],
        "estimate": "20-30 min",
        "steps": [
            "Open Libreseerr at http://<mac-mini>:8789 → Settings (admin).",
            "Ebook server: **Readarr**, URL `http://192.168.10.4:8787`, API key from Readarr → Settings → General.",
            "Root folder **`/readarr-library`**; pick a quality profile. Click **Test Connection** → Save.",
            "Optional **Plex Books**: link NAS Plex (http://<nas>:32400 + token) if Libreseerr build supports availability badges.",
            "Create a non-admin household user if others will request books.",
            "Submit a test request → confirm it appears in Readarr Activity (not Betty directly).",
        ],
        "commands": [
            "READARR_KEY=$(ssh nas 'grep -oP \"(?<=<ApiKey>)[^<]+\" /volume1/docker/readarr/config/config.xml')",
            "curl -s 'http://192.168.10.4:8787/api/v1/system/status' -H \"X-Api-Key: $READARR_KEY\"",
        ],
        "files": [
            "configs/nas/media-automation/README.md",
            "configs/nas/calibre-web-automated/README.md",
        ],
        "docs": [{"title": "Libreseerr", "url": "https://github.com/zamnzim/Libreseerr"}],
        "verify": "Libreseerr test request appears in NAS Readarr Activity.",
        "track": "ebook-mgmt",
        "required": False,
    },
    "ebook-06": {
        "id": "ebook-06",
        "title": "End-to-end ebook verification (Libreseerr → Betty → Readarr → CWA → Plex/Kobo)",
        "host": "NAS",
        "type": "sync",
        "depends_on": ["ebook-05", "read-05"],
        "estimate": "30-45 min",
        "steps": [
            "Prerequisites: rclone mount (nas-20), Readarr split pipeline (ebook-03), Libreseerr wired (ebook-05), CWA (nas-09), Plex Books library on /volume1/books (nas-10), KOReader OPDS (read-05).",
            "Request a small known ebook in **Libreseerr** → Readarr Wanted → Deluge label **readarr** on Betty.",
            "Watch import: `/seedbox/books/` → Readarr copies to **`/readarr-library`** → Connect script copies to **ingest** → CWA moves to **`/volume1/books`**.",
            "Confirm Readarr still shows **Downloaded** after CWA ingest (inventory fix validated).",
            "Confirm title in Plex Books and downloadable via CWA OPDS on the Kobo.",
        ],
        "commands": [
            "ssh nas 'ls /volume1/docker/readarr/library /volume1/docker/calibre-web-automated/ingest /volume1/books'",
            "ssh nas 'tail -30 /volume1/docker/readarr/config/logs/readarr-copy-to-cwa-ingest.log'",
        ],
        "files": [
            "configs/nas/media-automation/README.md",
            "configs/nas/calibre-web-automated/README.md",
            "scripts/reading/koreader-cwa-wallabag-wiring.md",
        ],
        "verify": "Libreseerr request → playable in Plex Books + OPDS; Readarr stays Downloaded after CWA ingest.",
        "track": "ebook-mgmt",
        "required": False,
    },
}
for tid, body in EBOOK_TASK_DEFS.items():
    by_id[tid] = body

# --- Soulseek music pipeline (late media-pipeline tasks) -----------------------
for _tid, _title, _host, _type, _deps, _est in (
    ("seed-09", "Deploy slskd on Betty (Soulseek P2P, native binary)", "Seedbox", "async", ["seed-03", "betty-01"], "45-60 min"),
    ("nas-29", "Deploy Soularr on NAS (Lidarr ↔ remote slskd bridge)", "NAS", "sync", ["nas-23", "seed-09"], "30-45 min"),
    ("nas-30", "Deploy beets tag layer on NAS (optional)", "NAS", "async", ["nas-29"], "20-30 min"),
):
    if _tid not in by_id:
        by_id[_tid] = {
            "id": _tid,
            "title": _title,
            "host": _host,
            "type": _type,
            "depends_on": _deps,
            "estimate": _est,
            "steps": [],
            "commands": [],
            "files": [],
            "docs": [],
            "verify": "",
            "track": "media-pipeline",
            "required": False,
        }

# Rebuild task list preserving order; insert glue-04b after glue-04 if missing
out = []
for t in tasks:
    out.append(by_id.get(t["id"], t))
    if t["id"] == "glue-04" and not any(x["id"] == "glue-04b" for x in tasks):
        out.append(by_id["glue-04b"])

# Insert Soulseek + MusicSeerr music tasks after seed-08 if missing
LATE_MEDIA_TASKS = ("docker-16", "seed-06", "seed-09", "nas-29", "nas-30", "seed-10")
if not any(x["id"] == "seed-09" for x in out):
    insert_at = next((i + 1 for i, x in enumerate(out) if x["id"] == "seed-08"), len(out))
    for j, tid in enumerate(LATE_MEDIA_TASKS):
        if tid in by_id:
            out.insert(insert_at + j, by_id[tid])
elif not any(x["id"] == "docker-16" for x in out):
    insert_at = next((i + 1 for i, x in enumerate(out) if x["id"] == "seed-08"), len(out))
    for j, tid in enumerate(("docker-16", "seed-06", "seed-10")):
        if tid in by_id:
            out.insert(insert_at + j, by_id[tid])

# Insert ebook-mgmt tasks after read-06 if missing
EBOOK_TASKS = ("ebook-01", "ebook-02", "ebook-03", "ebook-04", "ebook-05", "ebook-06")
if not any(x["id"] == "ebook-01" for x in out):
    insert_at = next((i + 1 for i, x in enumerate(out) if x["id"] == "read-06"), len(out))
    for j, tid in enumerate(EBOOK_TASKS):
        if tid in by_id:
            out.insert(insert_at + j, by_id[tid])

new_json = json.dumps(out, separators=(",", ":"))
text = text[: m.start(2)] + new_json + text[m.end(2) :]

# --- trackMeta: add ebook-mgmt workstream --------------------------------------
tm = re.search(
    r'(<script type="application/json" id="trackMeta">\s*)(\{.*?\})(\s*</script>)',
    text,
    re.S,
)
if tm:
    track_meta = json.loads(tm.group(2))
    if "ebook-mgmt" not in track_meta:
        track_meta["ebook-mgmt"] = {
            "tier": "workstreams",
            "order": 7,
            "title": "Ebook Management Improvements",
            "sub": "Readarr permanent library + CWA copy-on-import, Libreseerr request portal — fixes inventory tracking and household book requests.",
        }
        track_meta_json = json.dumps(track_meta, indent=2)
        text = text[: tm.start(2)] + track_meta_json + text[tm.end(2) :]

patched = 0
for old, new in HTML_PATCHES:
    if old in text:
        text = text.replace(old, new)
        patched += 1

HTML.write_text(text)
print(f"Updated {HTML.name}: synced {len(out)} tasks; {patched} HTML reference patches")
