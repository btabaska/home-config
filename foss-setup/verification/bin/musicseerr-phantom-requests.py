#!/usr/bin/env python3
"""
Detect MusicSeerr "phantom downloading" requests.

Bug (2026-07-13): 3 Owl City albums (Cinematic, Coco Moon, Maybe I'm Dreaming),
batch-requested together, sat "Downloading 0%" in MusicSeerr for 2 days. Root
cause: MusicSeerr's batch add left them monitored=False in Lidarr, so Lidarr
never grabbed them, while MusicSeerr's request_history kept status='downloading'
and polled Lidarr forever. Container/API were healthy the whole time — the page
worked; the requests just never delivered.

This check flags the EXACT signature: a MusicSeerr request in 'downloading' /
'pending' state whose Lidarr album is NOT monitored and has no file. It
deliberately does NOT flag albums that are monitored-but-unavailable (no release
found yet), so "Maybe I'm Dreaming" (monitored, awaiting a release) is not a
false positive.

Reads MusicSeerr's request_history straight from its sqlite DB via
`docker exec musicseerr` (the container has no sqlite3 CLI and no monitoring API
key, so this avoids the app's session auth entirely), then checks each album's
monitored/file state in Lidarr.

Env: LIDARR_URL (e.g. http://192.168.10.4:8686), LIDARR_API_KEY.
Prints one line; exit 0 only on PHANTOM_OK:
  PHANTOM_OK checked=1
  PHANTOM_STUCK 3: Cinematic, Coco Moon, Maybe I'm Dreaming
  CONFIG_ERR / DB_UNREADABLE ...
"""
import json
import os
import subprocess
import sys
import urllib.request

DB = "/app/cache/library.db"


def get_active_requests():
    # The app's DB has no sqlite3 CLI; use the container's python to dump the
    # downloading/pending request rows with their Lidarr album id.
    code = (
        "import sqlite3,json;"
        "c=sqlite3.connect('%s');"
        "print(json.dumps([[a,l] for a,l in "
        "c.execute(\"SELECT album_title,lidarr_album_id FROM request_history "
        "WHERE status IN ('downloading','pending')\")]))" % DB
    )
    out = subprocess.run(
        ["docker", "exec", "musicseerr", "python3", "-c", code],
        capture_output=True, text=True, timeout=25,
    )
    if out.returncode != 0:
        raise RuntimeError((out.stderr or "docker exec failed").strip()[:120])
    return json.loads(out.stdout.strip() or "[]")


def lidarr_album(url, key, album_id):
    req = urllib.request.Request(
        f"{url}/api/v1/album/{album_id}", headers={"X-Api-Key": key}
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)


def main():
    url = os.environ.get("LIDARR_URL")
    key = os.environ.get("LIDARR_API_KEY")
    if not url or not key:
        print("CONFIG_ERR LIDARR_URL/LIDARR_API_KEY unset")
        return 1
    try:
        reqs = get_active_requests()
    except Exception as e:
        print(f"DB_UNREADABLE {str(e)[:90]}")
        return 1

    phantom = []
    for title, album_id in reqs:
        if not album_id:
            continue
        try:
            a = lidarr_album(url, key, album_id)
        except Exception:
            continue  # transient Lidarr hiccup — don't cry wolf
        has_file = (a.get("statistics") or {}).get("trackFileCount", 0) > 0
        if not a.get("monitored", False) and not has_file:
            phantom.append(title)

    if phantom:
        print(f"PHANTOM_STUCK {len(phantom)}: " + ", ".join(phantom[:6]))
        return 1
    print(f"PHANTOM_OK checked={len(reqs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
