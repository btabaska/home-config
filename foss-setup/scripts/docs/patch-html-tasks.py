#!/usr/bin/env python3
"""One-shot patcher for foss-setup/docs/index.html task data."""
import json
import re
from pathlib import Path

HTML = Path(__file__).resolve().parents[2] / "docs" / "index.html"
text = HTML.read_text()
m = re.search(r'(<script type="application/json" id="taskData">\s*)(\[.*?\])(\s*</script>)', text, re.S)
if not m:
    raise SystemExit("taskData block not found")
tasks = json.loads(m.group(2))
by_id = {t["id"]: t for t in tasks}

REMOVE = {"seed-02", "seed-04", "seed-06", "seed-10"}

# --- rewritten / new tasks ---------------------------------------------------
by_id["seed-01"] = {
    "id": "seed-01",
    "phase": 2,
    "title": 'Provision seedbox "Betty" — Bytesized Stream +3 (Deluge + slskd later)',
    "host": "Seedbox",
    "type": "async",
    "depends_on": [],
    "estimate": "1 hr + provisioning",
    "steps": [
        'Sign up at bytesized-hosting.com for **Stream +3** (3000 GB, 6–10 TB/mo upload cap, €16/mo, EU). Note your SFTP username, home path (/home/hd34/btabaska), and shared IP **185.162.184.38**.',
        "Architecture lock-in: Betty runs **Deluge** (torrents) and later **slskd** (Soulseek) — both P2P, both off-site. No *arr apps, Soularr, or beets on Betty — those live on the NAS.",
        "3000 GB is a working + seeding buffer, not your library. Set Deluge ratio/seed-time limits so torrents age out and the box self-prunes under 3 TB.",
        "After provisioning, continue to **betty-01** (Deluge labels) — do not install the old one-click *arr catalog apps.",
    ],
    "commands": [],
    "files": ["configs/seedbox/provider-comparison.md", "configs/seedbox/rclone.conf.example"],
    "docs": [
        {"title": "Bytesized hosting", "url": "https://bytesized-hosting.com/"},
        {"title": "Deluge labels", "url": "https://deluge.readthedocs.io/en/latest/"},
    ],
    "verify": "Bytesized panel shows an active AppBox; you have SFTP/SSH credentials and the home path documented.",
}

by_id["seed-03"] = {
    "id": "seed-03",
    "phase": 2,
    "title": "Put the seedbox on Tailscale (userspace networking)",
    "host": "Seedbox",
    "type": "sync",
    "depends_on": ["seed-01"],
    "estimate": "20-30 min",
    "steps": [
        "SSH into Betty. Create ~/tailscale and download the static tailscale + tailscaled binaries from pkgs.tailscale.com/stable (amd64 tgz).",
        "Start tailscaled with --tun=userspace-networking and custom --socket/--state (managed boxes have no root/TUN). Wire the command into a user boot script or systemd user unit so it survives reboots.",
        "Run tailscale up and authenticate via the printed URL; note this node's 100.x / MagicDNS name.",
        "Run verify-tailscale-seedbox.sh with PEERS=\"mac-mini nas\" — it checks tailnet login, home-peer ping, and Deluge WebUI (Betty is Deluge-only; *arrs are on the NAS).",
    ],
    "commands": [
        "mkdir -p ~/tailscale && cd ~/tailscale",
        'curl -fsSL "https://pkgs.tailscale.com/stable/tailscale_1.80.3_amd64.tgz" -o ts.tgz',
        "tar --strip-components=1 -xzf ts.tgz",
        "~/tailscale/tailscaled --tun=userspace-networking --state=$HOME/tailscale/tailscaled.state --socket=$HOME/tailscale/tailscaled.sock --port=41641 &",
        "~/tailscale/tailscale --socket=$HOME/tailscale/tailscaled.sock up",
        'PEERS="mac-mini nas" ./scripts/media/verify-tailscale-seedbox.sh',
    ],
    "files": ["scripts/media/verify-tailscale-seedbox.sh"],
    "docs": [
        {"title": "Tailscale userspace networking", "url": "https://tailscale.com/kb/1112/userspace-networking/"},
        {"title": "Tailscale static binaries", "url": "https://pkgs.tailscale.com/stable/#static"},
    ],
    "verify": "tailscale status on Betty shows logged in; verify script reports home peers reachable and Deluge WebUI listening.",
}

by_id["seed-05"] = {
    "id": "seed-05",
    "phase": 2,
    "title": "Connect Seerr to NAS Sonarr/Radarr/Lidarr (not the seedbox)",
    "host": "Ubuntu",
    "type": "sync",
    "depends_on": ["docker-03", "nas-22", "nas-28"],
    "estimate": "20-30 min",
    "steps": [
        "Open Seerr at http://<mac-mini>:5055 → Settings → Services.",
        "Add **Radarr**: Hostname = NAS IP or MagicDNS (192.168.10.4 / nas.<tailnet>), Port **7878**, API key from Radarr → Settings → General. Default root folder **/movies**; quality profile = TRaSH profile from nas-28.",
        "Add **Sonarr**: same host, Port **8989**, API key, root folder **/tv**, same quality profile.",
        "Add **Lidarr** (optional music requests): Port **8686**, root **/music**.",
        "Settings → Plex: link this NAS Plex server (URL http://<nas>:32400 + token from Plex account settings).",
        "Test each service → Save. A test request should appear in the NAS *arr, not on Betty.",
    ],
    "commands": [
        "curl -s http://192.168.10.4:7878/api/v3/system/status -H 'X-Api-Key: <RADARR_API_KEY>'",
        "curl -s http://192.168.10.4:8989/api/v3/system/status -H 'X-Api-Key: <SONARR_API_KEY>'",
    ],
    "files": ["configs/docker-stack/stacks/seerr/compose.yaml", "configs/nas/media-automation/README.md"],
    "docs": [{"title": "Seerr services setup", "url": "https://docs.seerr.dev/using-seerr/settings/services/"}],
    "verify": "Seerr Test passes for Radarr/Sonarr; a test request shows in the NAS *arr UI; Plex link succeeds.",
}

by_id["seed-07"] = {
    "id": "seed-07",
    "phase": 2,
    "title": "End-to-end pipeline verification (Seerr → Deluge → NAS import → Plex)",
    "host": "NAS",
    "type": "sync",
    "depends_on": ["seed-05", "nas-25", "nas-10"],
    "estimate": "30 min",
    "steps": [
        "Confirm prerequisites: rclone mount live (nas-20), *arr stack up (nas-21–22), Unpackerr running (nas-25), Plex libraries pointed at vol2/vol3/vol1 paths (nas-10), Seerr wired (seed-05).",
        "In Seerr, request one **small known title** (movie + TV episode if both wired).",
        "Watch Betty Deluge: torrent appears under the correct label folder in files/tv or files/movies.",
        "Watch NAS Sonarr/Radarr: grab → import from /seedbox via Remote Path Mapping → file lands in /volume3/tv or /volume2/movies with TRaSH naming.",
        "Trigger Plex library scan (or wait for automatic scan). Confirm the title plays.",
        "Confirm Seerr flips the request to **Available** and notifies the requester.",
    ],
    "commands": [
        "ls /volume1/mounts/seedbox-files/tv /volume1/mounts/seedbox-files/movies",
        'curl -s "http://localhost:32400/library/sections/<LIBRARY_ID>/refresh?X-Plex-Token=<PLEX_TOKEN>"',
        "docker logs --tail 50 sonarr",
        "docker logs --tail 50 radarr",
    ],
    "files": ["configs/nas/media-automation/README.md", "configs/nas/plex/README.md"],
    "docs": [{"title": "Seerr docs", "url": "https://docs.seerr.dev/"}],
    "verify": "A Seerr request results in a correctly named, playable title in Plex with zero manual steps; Seerr marks Available.",
}

by_id["seed-08"]["depends_on"] = ["seed-07"]
by_id["seed-08"]["steps"] = [
    "Only after seed-07 passes cleanly for ~1 week: back up UniFi config again (net-00).",
    "Stop/remove NAS qBittorrent + Gluetun containers; delete VPN credentials.",
    "Undo dual-LAN policy routing on the NAS (ip rule/route cleanup per decommission doc).",
    "Drop the 5 Mbps throttle; remove old torrent port-forwards and VPN firewall rules.",
    "Stop Plex + *arr containers on Ubuntu if still running (nas-10 + nas-21 own them now).",
    "Verify the NAS opens no P2P/VPN sockets: ss -tunp | grep -iE 'wireguard|openvpn|6881' should be empty.",
]
by_id["seed-08"]["files"] = ["configs/seedbox/decommission-old-nas-torrent.md"]
by_id["seed-08"]["commands"] = [
    "docker rm -f qbittorrent gluetun 2>/dev/null || true",
    "ip rule show",
    "sudo ss -tunp | grep -iE 'wireguard|openvpn|6881' || echo clean",
]

by_id["docker-03"] = {
    "id": "docker-03",
    "phase": 2,
    "title": "Deploy Seerr media request portal (home, Mac mini)",
    "host": "Ubuntu",
    "type": "sync",
    "depends_on": ["docker-02"],
    "estimate": "20 min",
    "steps": [
        "Copy the stack to /opt/stacks (docker-02) if not already: seerr lives at /opt/stacks/seerr/.",
        "cd /opt/stacks/seerr && cp -n .env.example .env — set TZ; init: true is mandatory (Seerr image has no init process).",
        "If migrating from Jellyseerr/Overseerr, mount old config at /app/config — Seerr migrates on first boot.",
        "docker compose up -d && docker compose ps — confirm healthy.",
        "Browse to http://<mac-mini>:5055, create admin, sign in with Plex. **Do not** add Sonarr/Radarr yet — that is seed-05 after the NAS *arr stack (nas-22) and Recyclarr (nas-28) are ready.",
    ],
    "commands": [
        "cd /opt/stacks/seerr && cp -n .env.example .env",
        "docker compose up -d",
        "docker compose ps",
        "curl -sf http://localhost:5055/api/v1/status || echo 'wait for health'",
    ],
    "files": [
        "configs/docker-stack/stacks/seerr/compose.yaml",
        "configs/docker-stack/stacks/seerr/.env.example",
    ],
    "docs": [
        {"title": "Seerr Docker", "url": "https://docs.seerr.dev/getting-started/docker/"},
        {"title": "Seerr migration guide", "url": "https://docs.seerr.dev/migration-guide/"},
    ],
    "verify": "Health check passes; Seerr web UI loads on :5055 and Plex sign-in works.",
}

by_id["nas-10"] = {
    "id": "nas-10",
    "phase": 2,
    "title": "Deploy Plex Media Server on the NAS (libraries + Quick Sync)",
    "host": "NAS",
    "type": "sync",
    "depends_on": ["nas-00d"],
    "estimate": "45-60 min",
    "steps": [
        "Prerequisite: three-volume shares exist (nas-00c) and NFS/SMB exports work (nas-00d). Paths: /volume2/movies, /volume3/tv, /volume1/music, /volume1/books.",
        "DSM → Package Center → **Plex Media Server** → Install (native package recommended for Intel Quick Sync on the J4125).",
        "Open http://<nas>:32400/web → sign in with Plex account (lifetime Plex Pass) → claim server.",
        "Settings → Manage → Libraries → Add: **Movies** → /volume2/movies; **TV Shows** → /volume3/tv; **Music** → /volume1/music. Optional: **Other Videos** → /volume1/youtube.",
        "Settings → Transcoder → enable **Use hardware acceleration when available** (Quick Sync).",
        "Enable automatic library scan. Run **Scan Library Files** on each library once.",
        "If migrating from Ubuntu Plex: stop the Mac mini container after confirming playback from NAS; clients may need to pin the new server.",
        "Add Plex appdata to Hyper Backup Tier 1 (see configs/nas/plex/README.md + backup-architecture.md).",
    ],
    "commands": [
        "ls -la /volume2/movies /volume3/tv /volume1/music",
        'curl -s "http://localhost:32400/identity?X-Plex-Token=<TOKEN>"',
    ],
    "files": ["configs/nas/plex/README.md", "configs/nas/backup-architecture.md"],
    "docs": [
        {"title": "Plex on Synology", "url": "https://support.plex.tv/articles/200288586-installation/"},
        {"title": "Plex hardware transcoding", "url": "https://support.plex.tv/articles/115002178853-using-hardware-accelerated-streaming/"},
    ],
    "verify": "Plex web UI loads; a client plays media with HW transcoding; libraries point at vol2/vol3/vol1 paths; config is in a backup job.",
}

by_id["nas-28"] = {
    "id": "nas-28",
    "phase": 2,
    "title": "Apply TRaSH quality profiles + naming via Recyclarr (Ubuntu → NAS *arrs)",
    "host": "Ubuntu",
    "type": "sync",
    "depends_on": ["nas-22"],
    "estimate": "30-45 min",
    "steps": [
        "Recyclarr runs on the Mac mini and pushes TRaSH Guides profiles + Plex-friendly naming to Sonarr/Radarr on the NAS.",
        "Copy configs/docker-stack/stacks/recyclarr/ to /opt/stacks/recyclarr/. Edit config/recyclarr.yml: set NAS base_url (http://192.168.10.4:8989 / :7878) and API keys from each *arr → Settings → General.",
        "Pick quality profile trash_ids (HD Bluray + WEB is a balanced default — see TRaSH guides).",
        "cd /opt/stacks/recyclarr && cp -n .env.example .env && docker compose run --rm recyclarr sync",
        "In Sonarr/Radarr UI confirm quality profiles and media naming updated. Schedule: cron or Diun-triggered weekly recyclarr sync.",
    ],
    "commands": [
        "sudo cp -r configs/docker-stack/stacks/recyclarr /opt/stacks/",
        "cd /opt/stacks/recyclarr && cp -n .env.example .env",
        "docker compose run --rm recyclarr sync",
    ],
    "files": [
        "configs/docker-stack/stacks/recyclarr/compose.yaml",
        "configs/docker-stack/stacks/recyclarr/config/recyclarr.yml",
        "configs/docker-stack/stacks/recyclarr/.env.example",
    ],
    "docs": [
        {"title": "Recyclarr getting started", "url": "https://recyclarr.dev/guide/getting-started/"},
        {"title": "TRaSH Sonarr naming", "url": "https://trash-guides.info/Sonarr/Sonarr-recommended-naming-scheme/"},
    ],
    "verify": "recyclarr sync exits 0; Sonarr/Radarr show TRaSH quality profiles and plex-tmdb naming enabled.",
}

# Fix nas-23 music — torrent path; Soulseek is seed-09 + nas-29
by_id["nas-23"]["steps"] = [
    "**Torrent path:** Lidarr imports into **/music** (host: /volume1/music). Download client = remote Deluge on 185.162.184.38, label **lidarr**.",
    "Remote Path Mapping: Host 185.162.184.38, Remote /home/hd34/btabaska/files/, Local /seedbox/. Import from /seedbox/music/.",
    "Root folder: /music. Enable **Rename Tracks**. Quality: FLAC-preferred with MP3 fallback.",
    "In Prowlarr add a music-capable indexer and sync to Lidarr (Settings → Apps → Full Sync).",
    "Soulseek (slskd on Betty + Soularr on NAS) is configured in **seed-09** and **nas-29** — after this task.",
    "Do NOT change /music naming without checking BOTH Plex Music and Rhythmbox/libgpod iPod sync.",
]
by_id["nas-23"]["verify"] = "Torrent album imports to /volume1/music and appears in Plex Music library."

by_id["nas-22"]["steps"] = [
    "Open each *arr web UI on the NAS (Sonarr :8989, Radarr :7878, Lidarr :8686, Readarr :8787).",
    "Settings → Download Clients → + **Deluge**: Host **185.162.184.38**, Port = Deluge daemon port, Password = daemon password. Label per app: sonarr / radarr / lidarr / readarr. **Remove Completed = OFF** (preserves seeding on Betty).",
    "Settings → Download Clients → Remote Path Mappings → Add: Host 185.162.184.38, Remote Path /home/hd34/btabaska/files/, Local Path /seedbox/ (repeat in each *arr).",
    "Set root folders: Sonarr **/tv**, Radarr **/movies**, Lidarr **/music**, Readarr **/cwa-book-ingest**.",
    "Prowlarr → Settings → Apps: add Sonarr, Radarr, Lidarr, Readarr with **Full Sync**. Add FlareSolverr proxy http://flaresolverr:8191 for Cloudflare indexers.",
    "Add indexers in Prowlarr (video + music + book capable as needed). Test a manual search in Sonarr.",
]
by_id["nas-22"]["commands"] = [
    "docker compose -f /volume1/docker/media-automation/docker-compose.yml ps",
    "curl -s http://localhost:9696/api/v1/applications -H 'X-Api-Key: <PROWLARR_API_KEY>'",
]

by_id["nas-21"]["steps"] = [
    "SSH to NAS. Copy repo folder configs/nas/media-automation/ → /volume1/docker/media-automation/ (or git clone the foss-setup repo and copy).",
    "cd /volume1/docker/media-automation && cp .env.example .env. Run id <user> on DSM — set PUID, PGID, TZ, RG_DB_PASSWORD (openssl rand -hex 24), and path vars: TV_LIBRARY=/volume3/tv, MOVIES_LIBRARY=/volume2/movies, MUSIC_LIBRARY=/volume1/music, DOCKER_ROOT=/volume1/docker, SEEDBOX_MOUNT=/volume1/mounts/seedbox-files, CWA_INGEST=/volume1/docker/calibre-web-automated/ingest.",
    "Prerequisite: nas-20 rclone mount must be live and listing files/ on the seedbox.",
    "**Phase A** (core TV/movies): docker compose up -d prowlarr flaresolverr sonarr radarr",
    "**Phase B** (music + books): docker compose up -d lidarr readarr rreading-glasses rreading-glasses-db",
    "**Phase C** (archives): docker compose up -d unpackerr — only after API keys filled in unpackerr.conf (nas-25).",
    "All images pinned in docker-compose.yml (never :latest). See README.md RAM-phased checklist.",
]
by_id["nas-21"]["commands"] = [
    "ssh nas 'id btabaska'",
    "cd /volume1/docker/media-automation && cp .env.example .env && nano .env",
    "docker compose up -d prowlarr flaresolverr sonarr radarr",
    "docker compose ps",
]

if "nas-00e" in by_id:
    by_id["nas-00e"]["steps"] = [
        "**Interim step** while Plex + Sonarr/Radarr/Lidarr still run on Ubuntu (before nas-10 / nas-21 migrate them to the NAS). Complete nas-00d (SMB/NFS exports) first.",
        "On Ubuntu, mount NFS exports at stable paths via /etc/fstab: /mnt/nas/tv → vol3/tv, /mnt/nas/movies → vol2/movies, /mnt/nas/music → vol1/music, /mnt/nas/books → vol1/books. Confirm docker PUID can read/write.",
        "Re-point Plex libraries (Ubuntu): TV → /mnt/nas/tv, Movies → /mnt/nas/movies, Music/Books → /mnt/nas/music + /mnt/nas/books. Trigger library scan.",
        "Update Sonarr/Radarr/Lidarr docker bind mounts and root folders to the same NAS paths.",
        "Play a known title in Plex; spot-check an *arr import path — only then delete old duplicate folders on vol1.",
        "After nas-10 + nas-21 land Plex/*arr on the NAS, retire the Ubuntu stacks (seed-08).",
    ]
    by_id["nas-00e"]["commands"] = [
        "sudo mkdir -p /mnt/nas/{tv,movies,music,books}",
        "sudo mount -a",
        "grep /mnt/nas /etc/fstab",
    ]

by_id["media-03"]["depends_on"] = ["nas-10", "seed-05"]
by_id["media-03"]["steps"] = [
    "Deploy Maintainerr at /opt/stacks/maintainerr (docker-02 layout). cp -n .env.example .env && docker compose up -d.",
    "Connect to **NAS Plex** (http://<nas>:32400 + token), **Seerr**, and **NAS Sonarr/Radarr** (192.168.10.4 — not the seedbox).",
    "Create rules (e.g. unwatched > 90 days and not in a collection) with a grace period.",
    "Run dry-run/notification mode first; review candidates; enable enforcement to cap Tier-2 growth.",
]

by_id["seed-08"]["verify"] = "No P2P/VPN sockets on NAS (slskd on Betty is expected)."

by_id["seed-09"] = {
    "id": "seed-09",
    "phase": 2,
    "title": "Deploy slskd on Betty (Soulseek P2P off-site)",
    "host": "Seedbox",
    "type": "async",
    "depends_on": ["seed-03", "betty-01"],
    "estimate": "45-60 min",
    "steps": [],
    "commands": [],
    "files": [
        "configs/seedbox/slskd-compose.example.yaml",
        "configs/seedbox/.env.example",
        "configs/seedbox/music-pipeline-soulseek.md",
    ],
    "docs": [
        {"title": "slskd", "url": "https://github.com/slskd/slskd"},
        {"title": "Soulseek", "url": "https://www.slsknet.org/"},
    ],
    "verify": "slskd running on Betty; downloads land in ~/files/slskd/; visible on NAS rclone mount.",
    "track": "media-pipeline",
}

by_id["nas-29"] = {
    "id": "nas-29",
    "phase": 2,
    "title": "Deploy Soularr on NAS (Lidarr ↔ remote slskd bridge)",
    "host": "NAS",
    "type": "sync",
    "depends_on": ["nas-23", "seed-09"],
    "estimate": "30-45 min",
    "steps": [],
    "commands": [],
    "files": [
        "configs/nas/media-automation/docker-compose.yml",
        "configs/nas/media-automation/soularr/config.ini.example",
        "configs/seedbox/music-pipeline-soulseek.md",
    ],
    "docs": [{"title": "Soularr", "url": "https://github.com/mrusse/soularr"}],
    "verify": "Soulseek album imports to /volume1/music via Soularr → slskd → Lidarr.",
    "track": "media-pipeline",
}

by_id["nas-30"] = {
    "id": "nas-30",
    "phase": 2,
    "title": "Deploy beets tag layer on NAS (optional, Lidarr owns layout)",
    "host": "NAS",
    "type": "async",
    "depends_on": ["nas-29"],
    "estimate": "20-30 min",
    "steps": [],
    "commands": [],
    "files": [
        "configs/nas/media-automation/beets/config.yaml.example",
        "configs/nas/media-automation/README.md",
    ],
    "docs": [{"title": "beets", "url": "https://beets.readthedocs.io/"}],
    "verify": "beet write refreshes tags in place without moving files under /volume1/music.",
    "track": "media-pipeline",
}

# Reorder: swap nas-00d/00e, net-11/12; phase-2 media block
ORDER = None  # computed below

tasks = [t for t in tasks if t["id"] not in REMOVE]

# swap helpers
def swap_ids(lst, a, b):
    ia, ib = lst.index(a), lst.index(b)
    lst[ia], lst[ib] = lst[ib], lst[ia]

ids = [t["id"] for t in tasks]
if "nas-00d" in ids and "nas-00e" in ids:
    swap_ids(ids, "nas-00d", "nas-00e")
if "net-11" in ids and "net-12" in ids:
    swap_ids(ids, "net-11", "net-12")

# Rebuild task list in new id order, inserting nas-28 after nas-27
PHASE2_MEDIA = [
    "seed-01", "betty-01", "seed-03",
    "nas-20", "nas-21", "nas-22", "nas-28", "nas-23", "nas-24", "nas-25", "nas-26", "nas-27",
    "nas-10",
    "docker-03", "seed-05", "seed-07", "seed-08",
    "seed-09", "nas-29", "nas-30",
]

def reorder_block(all_ids, block, after_id):
    """Move block items to sit contiguously right after after_id."""
    for tid in block:
        if tid in all_ids:
            all_ids.remove(tid)
    idx = all_ids.index(after_id) + 1 if after_id in all_ids else len(all_ids)
    for i, tid in enumerate(block):
        if tid in by_id or any(t["id"] == tid for t in tasks):
            all_ids.insert(idx + i, tid)

# insert nas-28 into by_id tasks list
if "nas-28" not in [t["id"] for t in tasks]:
    tasks.append(by_id["nas-28"])

# insert new tasks into by_id tasks list
for new_id in ("seed-09", "nas-29", "nas-30"):
    if new_id not in [t["id"] for t in tasks]:
        tasks.append(by_id[new_id])

# apply by_id updates to task objects
id_to_task = {t["id"]: t for t in tasks}
for k, v in by_id.items():
    if k in id_to_task and k not in REMOVE:
        if "track" in id_to_task[k]:
            v["track"] = id_to_task[k]["track"]
        id_to_task[k] = v
    elif k in ("nas-28", "seed-09", "nas-29", "nas-30"):
        id_to_task[k] = v

ids = list(id_to_task.keys())
# find anchor: after ha-11 or before seed-01
anchor = "ha-11"
if anchor in ids:
    for tid in PHASE2_MEDIA:
        if tid in ids:
            ids.remove(tid)
    pos = ids.index(anchor) + 1
    for i, tid in enumerate(PHASE2_MEDIA):
        if tid in id_to_task:
            ids.insert(pos + i, tid)

tasks = [id_to_task[i] for i in ids]

new_json = json.dumps(tasks, separators=(",", ":"))
HTML.write_text(text[: m.start(2)] + new_json + text[m.end(2) :])
print(f"Patched {HTML}: {len(tasks)} tasks (removed {len(REMOVE)} obsolete)")
