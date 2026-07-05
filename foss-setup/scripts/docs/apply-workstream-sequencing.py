#!/usr/bin/env python3
"""Apply workstream sequencing to docs/index.html (task ids unchanged — preserves progress)."""
import json
from pathlib import Path

HTML = Path(__file__).resolve().parents[2] / "docs" / "index.html"

TIER_META = {
    "backbone": {
        "title": "Backbone — do this first",
        "sub": "Critical path: operator prep → network → NAS layout → Docker host. "
        "If backbone is mostly done, finish the remaining gates (nas-01 snapshots, glue-01 UPS) "
        "before Immich, Paperless, or off-site backup.",
    },
    "workstreams": {
        "title": "Parallel workstreams",
        "sub": "Independent feature tracks — run side by side after backbone. "
        "Suggested order: finish media verification → smart home or life apps → reading → "
        "photos (needs nas-01) → off-site backup. None block each other except where deps say SYNC.",
    },
    "operations": {
        "title": "Operations & rebuildability",
        "sub": "Glue layer in three waves: (1) AdGuard, Dockge, ntfy, Beszel, Forgejo — "
        "(2) Caddy + Uptime Kuma + Homepage — (3) Git the stack, Ansible fleet, SBOM inventory. "
        "Security hardening follows once backups and Caddy exist.",
    },
    "enhancements": {
        "title": "Enhancements",
        "sub": "Optional polish — Plex analytics, game servers, Sunshine streaming, local AI. "
        "Gaming Phase 1 (WoL + Sunshine) can start anytime; Tdarr and GPU policy wait on WoL / HA voice.",
    },
}

# Global track order within each tier (lower = earlier in guide).
TRACK_ORDER = {
    # backbone
    "desktop": 0,
    "network": 1,
    "nas-foundation": 2,
    "docker-host": 3,
    # workstreams (logical progression for remaining work)
    "media-pipeline": 1,
    "smart-home": 2,
    "apps": 3,
    "reading": 4,
    "photos": 5,
    "backups-offsite": 6,
    # operations
    "ops": 1,
    "security": 2,
    # enhancements
    "media-polish": 1,
    "gaming": 2,
}

TRACK_META_PATCH = {
    "nas-foundation": {
        "sub": "Three-volume split, share exports, Container Manager — then nas-01 Btrfs snapshots "
        "(unlocks Immich + off-site backup) and glue-01 UPS/NUT.",
    },
    "desktop": {
        "sub": "prep-01 first, then glue-03/04 anytime. Remaining: glue-02 browser baseline, glue-04b fleet dotfiles.",
    },
    "media-pipeline": {
        "sub": "Core stack is live. Close out: seed-07 end-to-end verify → optional Soulseek branch "
        "(seed-09 → nas-29 → nas-30 beets).",
    },
    "smart-home": {
        "sub": "Fully parallel — network backbone already unlocks this. "
        "Phase: HA Green → HACS + Hue/Nest → Midea/Zigbee → voice/cameras → LiteLLM fallback.",
    },
    "apps": {
        "sub": "Light Docker on Mac mini — deploy Miniflux + Navidrome + Wallabag + Mealie together; "
        "Paperless after nas-01.",
    },
    "reading": {
        "sub": "Three entry points: (A) CWA + Calibre + Kobo, (B) iPod/podcasts on CachyOS, "
        "(C) Obsidian + Pinchflat anytime.",
    },
    "photos": {
        "sub": "Immich on NAS — blocked only on nas-01 Btrfs snapshots.",
    },
    "backups-offsite": {
        "sub": "Recommended after nas-01: B2 Hyper Backup → restic/Borg → full restore drill (nas-07).",
    },
    "ops": {
        "sub": "Wave 1: AdGuard, Dockge, ntfy, Beszel, Forgejo. Wave 2: Caddy → Uptime Kuma → Homepage. "
        "Wave 3: Git stack, Ansible, SBOM, restore runbooks.",
    },
    "security": {
        "sub": "MFA + patches + Docker log caps anytime. Immutable backups (sec-03) after off-site chain; "
        "CrowdSec (sec-04) after Caddy.",
    },
    "media-polish": {
        "sub": "All async — Tautulli, Kometa, Maintainerr anytime; Tdarr after game-08 WoL.",
    },
    "gaming": {
        "sub": "Phase 1: WoL + Sunshine + Moonlight. Phase 2: LinuxGSM servers. "
        "Phase 3: Ludusavi, RomM, GPU policy (needs ha-17).",
    },
}

WITHIN_TRACK_ORDER = {
    "desktop": ["prep-01", "glue-02", "glue-03", "glue-04", "glue-04b"],
    "network": [
        "net-00", "net-01", "net-02", "net-03", "net-04", "net-05", "net-06",
        "net-07", "net-08", "net-11", "net-09", "net-10", "net-12", "net-13", "net-14",
    ],
    "nas-foundation": [
        "nas-00a", "nas-00b", "nas-00c", "nas-prep-01", "nas-00d", "nas-01", "glue-01",
    ],
    "docker-host": ["docker-01", "docker-02"],
    "media-pipeline": [
        "seed-01", "betty-01", "seed-03", "nas-20", "nas-21", "nas-22", "nas-28",
        "nas-23", "nas-24", "nas-25", "nas-26", "nas-27", "nas-10", "docker-03",
        "seed-05", "seed-07", "seed-08", "seed-09", "nas-29", "nas-30",
    ],
    "smart-home": [
        "ha-01", "ha-02", "ha-03", "ha-04", "ha-05", "ha-06", "ha-07", "ha-08",
        "ha-09", "ha-10", "ha-11", "ha-12", "ha-13", "ha-14", "ha-15", "ha-16", "ha-17",
    ],
    "photos": ["nas-08", "nas-08b"],
    "reading": [
        "nas-09", "read-01", "read-02", "read-03", "read-04", "read-05", "read-06",
        "read-08", "read-09", "read-10", "read-11", "read-12", "read-13", "read-14",
    ],
    "apps": ["docker-04", "docker-05", "read-07", "doc-02", "doc-01"],
    "backups-offsite": ["nas-02", "nas-03", "nas-04", "nas-05", "nas-06", "nas-07"],
    "ops": [
        "docker-07", "docker-08", "docker-09", "docker-10", "glue-05",
        "docker-06", "docker-11", "docker-12", "docker-14", "docker-15",
        "docker-13", "glue-06", "glue-07", "glue-08",
        "sbom-01", "sbom-02", "sbom-03", "sbom-04", "sbom-05",
        "dns-01", "dns-02", "dns-03", "dns-04", "dns-05",
    ],
    "security": ["sec-01", "sec-02", "sec-05", "sec-03", "sec-04"],
    "media-polish": ["media-01", "media-02", "media-03", "media-04"],
    "gaming": [
        "game-08", "game-10", "game-05", "game-11", "game-06", "game-07", "game-09",
        "game-01", "game-04", "game-02", "game-03", "game-12", "game-14", "game-13", "ai-01",
    ],
}

TIER_ORDER = ["backbone", "workstreams", "operations", "enhancements"]


def load_json_block(html: str, element_id: str):
    marker = f'id="{element_id}">'
    pos = html.index(marker) + len(marker)
    while pos < len(html) and html[pos] in " \t\n\r":
        pos += 1
    data, end = json.JSONDecoder().raw_decode(html, pos)
    return data, (pos, end)


def replace_json_block(html: str, element_id: str, data) -> str:
    blob = json.dumps(data, separators=(",", ":"))
    _, (start, end) = load_json_block(html, element_id)
    return html[:start] + blob + html[end:]


def _reorder_with_meta(tasks, by_track, track_meta):
    def track_sort_key(track: str):
        tm = track_meta[track]
        return (TIER_ORDER.index(tm["tier"]), TRACK_ORDER.get(track, 99))

    out: list[dict] = []
    for track in sorted(by_track.keys(), key=track_sort_key):
        lst = by_track[track]
        order = WITHIN_TRACK_ORDER.get(track)
        if not order:
            out.extend(lst)
            continue
        rank = {tid: i for i, tid in enumerate(order)}
        unknown = [t for t in lst if t["id"] not in rank]
        if unknown:
            raise SystemExit(f"Tasks missing from WITHIN_TRACK_ORDER[{track}]: {[t['id'] for t in unknown]}")
        out.extend(sorted(lst, key=lambda t: rank[t["id"]]))
    return out


def main():
    html = HTML.read_text(encoding="utf-8")
    track_meta, _ = load_json_block(html, "trackMeta")
    tasks, _ = load_json_block(html, "taskData")

    for track, order in TRACK_ORDER.items():
        if track in track_meta:
            track_meta[track]["order"] = order
    for track, patch in TRACK_META_PATCH.items():
        if track in track_meta:
            track_meta[track].update(patch)

    by_track: dict[str, list[dict]] = {}
    for task in tasks:
        by_track.setdefault(task["track"], []).append(task)
    reordered = _reorder_with_meta(tasks, by_track, track_meta)

    before = [t["id"] for t in tasks]
    after = [t["id"] for t in reordered]
    print(f"Tasks: {len(tasks)}")
    print(f"Order changed: {before != after}")

    html = replace_json_block(html, "tierMeta", TIER_META)
    html = replace_json_block(html, "trackMeta", track_meta)
    html = replace_json_block(html, "taskData", reordered)
    HTML.write_text(html, encoding="utf-8")
    print(f"Updated {HTML}")


if __name__ == "__main__":
    main()
