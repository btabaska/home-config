#!/usr/bin/env python3
"""Migrate foss-setup/docs/index.html from linear phases to tiered parallel tracks."""
import json
import re
from pathlib import Path

HTML = Path(__file__).resolve().parents[2] / "docs" / "index.html"

TIER_META = {
    "backbone": {
        "title": "Backbone — do this first",
        "sub": "The critical path: network segmentation, remote access, NAS layout, and a Docker host. Finish this tier before trusting the fleet with primary data. Tasks inside each track still run in order where marked SYNC.",
    },
    "workstreams": {
        "title": "Parallel workstreams",
        "sub": "Independent tracks — pick what matters to you and run them side by side. Smart home, media, photos, reading, and desktop are unrelated; none blocks the others. Off-site backup is here too (recommended, not a gate).",
    },
    "operations": {
        "title": "Operations & rebuildability",
        "sub": "The glue layer: reverse proxy, DNS filtering, monitoring, config-as-code, fleet maintenance, and security hardening. Start once docker-host is up; many ops tasks parallelize after Caddy + ntfy exist.",
    },
    "enhancements": {
        "title": "Enhancements",
        "sub": "Optional polish — Plex analytics, game servers, Sunshine streaming, local AI extras. Safe to skip entirely or tackle years later.",
    },
}

TRACK_META = {
    "network": {
        "tier": "backbone",
        "order": 1,
        "title": "Network & remote access",
        "sub": "UniFi VLANs + zone firewall (one-way door), Tailscale mesh, SSH fallbacks, and security extras.",
    },
    "nas-foundation": {
        "tier": "backbone",
        "order": 2,
        "title": "NAS storage layout",
        "sub": "Three-volume split, share exports, local Btrfs snapshots, and UPS graceful shutdown.",
    },
    "docker-host": {
        "tier": "backbone",
        "order": 3,
        "title": "Docker host bootstrap",
        "sub": "Docker Engine + /opt/stacks layout on the Mac mini — prerequisite for every Compose app.",
    },
    "desktop": {
        "tier": "backbone",
        "order": 4,
        "title": "Operator & desktop baseline",
        "sub": "Clone foss-setup on your MacBook first, then optional browser/Kagi/dotfiles anytime.",
    },
    "smart-home": {
        "tier": "workstreams",
        "order": 1,
        "title": "Smart home (Home Assistant)",
        "sub": "HA Green, integrations (Hue, Nest, Midea), Zigbee, cameras, voice, and Apple Home bridge.",
    },
    "media-pipeline": {
        "tier": "workstreams",
        "order": 2,
        "title": "Media pipeline (seedbox → Plex)",
        "sub": "Betty seedbox, NAS *arr import stack, Plex on the NAS, and Seerr requests — no P2P at home.",
    },
    "photos": {
        "tier": "workstreams",
        "order": 3,
        "title": "Photos (Immich)",
        "sub": "Self-hosted photo library with Quick Sync ML — replaces iCloud Photos.",
    },
    "reading": {
        "tier": "workstreams",
        "order": 4,
        "title": "Reading & portable media",
        "sub": "Calibre/CWA, KOReader, Syncthing, iPod sync, podcasts, Obsidian, and Pinchflat.",
    },
    "apps": {
        "tier": "workstreams",
        "order": 5,
        "title": "Life apps (Docker)",
        "sub": "Miniflux, Navidrome, Wallabag, Mealie, and Paperless — lightweight always-on services.",
    },
    "backups-offsite": {
        "tier": "workstreams",
        "order": 6,
        "title": "Off-site backup (recommended)",
        "sub": "Backblaze B2, rotated HDD, restic, and Borg — plus a tested restore. Valuable but not a prerequisite for Immich, media, or HA.",
    },
    "ops": {
        "tier": "operations",
        "order": 1,
        "title": "Reverse proxy, monitoring & Git",
        "sub": "Caddy, AdGuard, Dockge, Beszel, Uptime Kuma, ntfy, Homepage, Forgejo, Ansible, and SBOM inventory.",
    },
    "security": {
        "tier": "operations",
        "order": 2,
        "title": "Security hardening",
        "sub": "MFA, patches, immutable backups, CrowdSec, and encrypted DNS.",
    },
    "media-polish": {
        "tier": "enhancements",
        "order": 1,
        "title": "Plex polish",
        "sub": "Tautulli analytics, Kometa collections, Maintainerr pruning, and Tdarr transcoding.",
    },
    "gaming": {
        "tier": "enhancements",
        "order": 2,
        "title": "Gaming & streaming",
        "sub": "LinuxGSM/Pelican servers, Sunshine/Moonlight, Wake-on-LAN, and GPU tuning.",
    },
}

TRACK_BY_ID = {
    # network
    "net-00": "network", "net-01": "network", "net-02": "network", "net-03": "network",
    "net-04": "network", "net-05": "network", "net-06": "network", "net-07": "network",
    "net-08": "network", "net-09": "network", "net-10": "network", "net-11": "network",
    "net-12": "network", "net-13": "network", "net-14": "network",
    # nas-foundation
    "nas-00a": "nas-foundation", "nas-00b": "nas-foundation", "nas-00c": "nas-foundation",
    "nas-00d": "nas-foundation", "nas-00e": "nas-foundation", "nas-prep-01": "nas-foundation",
    "nas-01": "nas-foundation",
    "glue-01": "nas-foundation",
    # docker-host
    "docker-01": "docker-host", "docker-02": "docker-host",
    # desktop
    "glue-02": "desktop", "glue-03": "desktop", "glue-04": "desktop", "glue-04b": "desktop",
    "prep-01": "desktop",
    # backups-offsite
    "nas-02": "backups-offsite", "nas-03": "backups-offsite", "nas-04": "backups-offsite",
    "nas-05": "backups-offsite", "nas-06": "backups-offsite", "nas-07": "backups-offsite",
    # smart-home
    "ha-01": "smart-home", "ha-02": "smart-home", "ha-03": "smart-home", "ha-04": "smart-home",
    "ha-05": "smart-home", "ha-06": "smart-home", "ha-07": "smart-home", "ha-08": "smart-home",
    "ha-09": "smart-home", "ha-10": "smart-home", "ha-11": "smart-home", "ha-12": "smart-home",
    "ha-13": "smart-home", "ha-14": "smart-home", "ha-15": "smart-home", "ha-16": "smart-home",
    "ha-17": "smart-home",
    # media-pipeline
    "seed-01": "media-pipeline", "betty-01": "media-pipeline", "seed-03": "media-pipeline",
    "nas-20": "media-pipeline", "nas-21": "media-pipeline", "nas-22": "media-pipeline",
    "nas-28": "media-pipeline",
    "nas-23": "media-pipeline", "nas-24": "media-pipeline",
    "nas-25": "media-pipeline", "nas-26": "media-pipeline", "nas-27": "media-pipeline",
    "nas-10": "media-pipeline", "docker-03": "media-pipeline", "seed-05": "media-pipeline",
    "seed-07": "media-pipeline", "seed-08": "media-pipeline",
    # photos
    "nas-08": "photos", "nas-08b": "photos",
    # reading
    "nas-09": "reading", "read-01": "reading", "read-02": "reading", "read-03": "reading",
    "read-04": "reading", "read-05": "reading", "read-06": "reading", "read-08": "reading",
    "read-09": "reading", "read-10": "reading", "read-11": "reading", "read-12": "reading",
    "read-13": "reading", "read-14": "reading",
    # apps
    "docker-04": "apps", "docker-05": "apps", "read-07": "apps", "doc-01": "apps", "doc-02": "apps",
    # ops
    "docker-06": "ops", "docker-07": "ops", "docker-08": "ops", "docker-09": "ops",
    "docker-10": "ops", "docker-11": "ops", "docker-12": "ops", "docker-14": "ops",
    "docker-15": "ops", "glue-05": "ops", "docker-13": "ops", "glue-06": "ops",
    "glue-07": "ops", "glue-08": "ops", "sbom-01": "ops", "sbom-02": "ops", "sbom-03": "ops",
    "sbom-04": "ops", "sbom-05": "ops", "dns-01": "ops",
    # security
    "sec-01": "security", "sec-02": "security", "sec-03": "security", "sec-04": "security",
    "sec-05": "security",
    # media-polish
    "media-01": "media-polish", "media-02": "media-polish", "media-03": "media-polish",
    "media-04": "media-polish",
    # gaming
    "game-01": "gaming", "game-02": "gaming", "game-03": "gaming", "game-04": "gaming",
    "game-05": "gaming", "game-06": "gaming", "game-07": "gaming", "game-08": "gaming",
    "game-09": "gaming", "game-10": "gaming", "game-11": "gaming", "game-12": "gaming",
    "game-13": "gaming", "game-14": "gaming", "ai-01": "gaming",
}

# Relax off-site backup as a hard gate for other workstreams
DEP_FIXES = {
    "nas-08": ["nas-01"],
    "nas-09": ["nas-00c"],
    "nas-24": ["nas-22"],  # was nas-22,nas-09 — CWA can be wired later
}

REMOVE = {"seed-02", "seed-04", "seed-06", "seed-09", "seed-10"}

TIER_ORDER = ["backbone", "workstreams", "operations", "enhancements"]

TRACK_ORDER = sorted(
    TRACK_META.keys(),
    key=lambda t: (TIER_ORDER.index(TRACK_META[t]["tier"]), TRACK_META[t]["order"]),
)


def main():
    text = HTML.read_text()

    m = re.search(
        r'(<script type="application/json" id="taskData">\s*)(\[.*?\])(\s*</script>)',
        text,
        re.S,
    )
    if not m:
        raise SystemExit("taskData block not found")

    tasks = json.loads(m.group(2))
    tasks = [t for t in tasks if t["id"] not in REMOVE]
    migrated = []
    missing = []

    for t in tasks:
        tid = t["id"]
        track = TRACK_BY_ID.get(tid)
        if not track:
            missing.append(tid)
            continue
        nt = dict(t)
        nt.pop("phase", None)
        nt["track"] = track
        if tid in DEP_FIXES:
            nt["depends_on"] = DEP_FIXES[tid]
        migrated.append(nt)

    if missing:
        raise SystemExit(f"Unmapped task IDs: {missing}")

    # Sort: tier → track → original order within track
    orig_idx = {t["id"]: i for i, t in enumerate(tasks)}

    def sort_key(t):
        tr = t["track"]
        return (
            TIER_ORDER.index(TRACK_META[tr]["tier"]),
            TRACK_META[tr]["order"],
            orig_idx[t["id"]],
        )

    migrated.sort(key=sort_key)

    new_task_json = json.dumps(migrated, separators=(",", ":"))
    tier_meta_json = json.dumps(TIER_META, indent=2)
    track_meta_json = json.dumps(TRACK_META, indent=2)

    # Replace taskData first (positions still valid), then swap phaseMeta → tier/track meta
    text = text[: m.start(2)] + new_task_json + text[m.end(2) :]

    replacement = (
        f'<script type="application/json" id="tierMeta">\n{tier_meta_json}\n</script>\n'
        f'<script type="application/json" id="trackMeta">\n{track_meta_json}\n</script>\n'
    )
    text = re.sub(
        r'<script type="application/json" id="phaseMeta">.*?</script>\s*',
        lambda _m: replacement,
        text,
        count=1,
        flags=re.S,
    )

    HTML.write_text(text)
    print(f"Migrated {len(migrated)} tasks into {len(TRACK_META)} tracks across {len(TIER_META)} tiers")


if __name__ == "__main__":
    main()
