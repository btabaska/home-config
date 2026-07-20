#!/usr/bin/env python3
"""Detect request-layer rot: dashboards lying about what the backend will deliver (fix-26).

The 2026-07-16 quality gate found four shapes of this (H4, H15, M12, M36) — all
with every liveness signal green:
  - a seerr request PROCESSING forever because its Sonarr series was deleted
    after the request (dangling externalServiceId, H4)
  - a seerr movie request PROCESSING for 10+ days with ZERO Radarr history —
    no release exists, and nothing ever tells the user (M12)
  - a libreseerr request "completed 100%" whose Bookshelf book has no file
    (imported into a junk duplicate edition record, H15)
  - a libreseerr request "processing 0%" days after a successful import,
    because statuses only refreshed on a UI POST (M36 — now fixed by an
    in-app background reconciler; this check is the tripwire if that dies)

Modes:
  seerr       — for every seerr request whose media is PROCESSING: the linked
                sonarr/radarr entry must exist (else DANGLING), and a movie
                that is available+monitored with zero grab history after
                NEVER_GRABBED_D days is NEVER_GRABBED (no release found and
                nobody was told).
  libreseerr  — for every stored libreseerr request: 'completed' requires the
                backend book to exist with >=1 file (else FALSE_COMPLETE);
                'processing'/'downloading' older than STALE_AFTER_H hours
                requires the book to exist (DANGLING), be monitored or have a
                file (DEAD), and NOT already have a file (STALE_STATUS = the
                background reconciler is broken). The backend URL/key come
                from libreseerr's own data/config.json (bmig-04: Bookshelf);
                requests created before the bmig-04 backend cutover carry OLD
                readarr book ids and are skipped (bmig-05 re-drives them).

Env: SONARR_API_KEY RADARR_API_KEY. The seerr API key is read
from /opt/stacks/seerr/config/settings.json (runs on mini, world-readable);
libreseerr state from /opt/stacks/libreseerr/data/requests.json.
Prints one line; expect-regex friendly:
  SEERR_OK checked=N       | SEERR_ROT n: kind:title; ...
  LIBRESEERR_OK checked=N  | LIBRESEERR_ROT n: kind:title; ...
  CONFIG_ERR ... (never a vacuous pass)
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

SEERR_URL = "http://192.168.10.2:5055"
SEERR_SETTINGS = "/opt/stacks/seerr/config/settings.json"
LIBRESEERR_REQUESTS = "/opt/stacks/libreseerr/data/requests.json"
LIBRESEERR_CONFIG = "/opt/stacks/libreseerr/data/config.json"
SONARR_URL = "http://192.168.10.4:8989"
RADARR_URL = "http://192.168.10.4:7878"
# bmig-04 backend cutover (readarr :8787 -> bookshelf :8790, 2026-07-20).
# Stored requests older than this reference book ids in the OLD readarr;
# bmig-05 re-drives/cleans them. Compared as ISO strings (created_at is
# naive-UTC isoformat).
BACKEND_CUTOVER = "2026-07-20T19:30:00"

MEDIA_PROCESSING = 3          # seerr media status enum
NEVER_GRABBED_D = 7           # movie available+monitored, no history after this = rot
STALE_AFTER_H = 48            # libreseerr non-terminal request younger than this = in-flight


def api(base, ver, key, path):
    req = urllib.request.Request(f"{base}/api/{ver}{path}", headers={"X-Api-Key": key})
    return json.load(urllib.request.urlopen(req, timeout=20))


def api_or_404(base, ver, key, path):
    try:
        return api(base, ver, key, path)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def age_days(iso):
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).total_seconds() / 86400


def check_seerr():
    sonarr_key = os.environ.get("SONARR_API_KEY")
    radarr_key = os.environ.get("RADARR_API_KEY")
    if not (sonarr_key and radarr_key):
        print("CONFIG_ERR missing SONARR_API_KEY/RADARR_API_KEY")
        return 2
    try:
        seerr_key = json.load(open(SEERR_SETTINGS))["main"]["apiKey"]
    except Exception as e:
        print(f"CONFIG_ERR cannot read seerr apiKey: {e}")
        return 2

    reqs = api(SEERR_URL, "v1", seerr_key, "/request?take=200").get("results", [])
    rot, checked = [], 0
    for r in reqs:
        media = r.get("media") or {}
        if media.get("status") != MEDIA_PROCESSING:
            continue
        checked += 1
        ext_id = media.get("externalServiceId")
        title = f"{r.get('type')}#{media.get('tmdbId')}"
        if ext_id is None:
            rot.append(f"dangling:{title}(no externalServiceId)")
            continue
        if r.get("type") == "tv":
            if api_or_404(SONARR_URL, "v3", sonarr_key, f"/series/{ext_id}") is None:
                rot.append(f"dangling:{title}(sonarr {ext_id} gone)")
        else:
            movie = api_or_404(RADARR_URL, "v3", radarr_key, f"/movie/{ext_id}")
            if movie is None:
                rot.append(f"dangling:{title}(radarr {ext_id} gone)")
                continue
            hist = api(RADARR_URL, "v3", radarr_key, f"/history/movie?movieId={ext_id}")
            if (
                movie.get("isAvailable")
                and movie.get("monitored")
                and not movie.get("hasFile")
                and not hist
                and age_days(r.get("createdAt", "1970-01-01T00:00:00Z")) > NEVER_GRABBED_D
            ):
                rot.append(f"never-grabbed:{title}({int(age_days(r['createdAt']))}d, 0 history)")
    if rot:
        print(f"SEERR_ROT {len(rot)}: " + "; ".join(rot))
        return 1
    print(f"SEERR_OK checked={checked}")
    return 0


def check_libreseerr():
    try:
        cfg = json.load(open(LIBRESEERR_CONFIG)).get("ebook") or {}
        backend_url, backend_key = cfg.get("url"), cfg.get("api_key")
    except Exception as e:
        print(f"CONFIG_ERR cannot read libreseerr backend config: {e}")
        return 2
    if not (backend_url and backend_key):
        print("CONFIG_ERR libreseerr ebook backend not configured")
        return 2
    try:
        reqs = json.load(open(LIBRESEERR_REQUESTS))
    except Exception as e:
        print(f"CONFIG_ERR cannot read libreseerr requests: {e}")
        return 2

    rot, checked, legacy = [], 0, 0
    for r in reqs:
        status = r.get("status")
        book_id = r.get("readarr_book_id")
        title = r.get("title", "?")
        if not book_id or status == "error":  # errors are already surfaced to the user
            continue
        if (r.get("created_at") or "") < BACKEND_CUTOVER:
            legacy += 1  # old-readarr book id; bmig-05 re-drives these
            continue
        checked += 1
        book = api_or_404(backend_url, "v1", backend_key, f"/book/{book_id}")
        files = ((book or {}).get("statistics") or {}).get("bookFileCount", 0)
        if status == "completed":
            if book is None:
                rot.append(f"false-complete:{title}(book {book_id} gone)")
            elif files == 0:
                rot.append(f"false-complete:{title}(book {book_id} has no file)")
        elif status in ("processing", "downloading"):
            if age_days(r.get("created_at", "1970-01-01T00:00:00Z")) * 24 < STALE_AFTER_H:
                continue  # in-flight
            if book is None:
                rot.append(f"dangling:{title}(book {book_id} gone)")
            elif files > 0:
                rot.append(f"stale-status:{title}(imported but still '{status}' — reconciler dead?)")
            elif not book.get("monitored"):
                rot.append(f"dead:{title}(book {book_id} unmonitored, nothing searching)")
    if rot:
        print(f"LIBRESEERR_ROT {len(rot)}: " + "; ".join(rot))
        return 1
    print(f"LIBRESEERR_OK checked={checked} legacy_skipped={legacy}")
    return 0


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "seerr":
        return check_seerr()
    if mode == "libreseerr":
        return check_libreseerr()
    print("CONFIG_ERR usage: request-layer-audit.py seerr|libreseerr")
    return 2


if __name__ == "__main__":
    sys.exit(main())
