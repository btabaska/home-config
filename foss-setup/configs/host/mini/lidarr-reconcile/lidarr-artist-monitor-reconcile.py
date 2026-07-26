#!/usr/bin/env python3
"""Close the musicseerr "unmonitored-artist request" generator (media-07).

Background (fix-25, 2026-07-17 / H14/M13): musicseerr v1.4.2 adds a Lidarr
artist with monitored=false when a user requests a single album, then monitors
only that album. Lidarr excludes a monitored album from wanted/missing when its
PARENT artist is unmonitored, so a failed first search is never retried and the
album is silently invisible (the "3OH!3 phantom"). fix-25 fixed the one instance
and added the arr-orphan-monitor-flags tripwire, but the GENERATOR remained:
musicseerr is an upstream image with no bind-mounted code and no monitor-artist
config knob (verified live: config.json exposes only quality/metadata profile +
root folder), so it can keep minting these requests.

This reconciler is the generator-closer. It enforces the invariant every album
depends on: **if any album is monitored, its artist must be monitored too.** It
is source-agnostic (fixes an orphan however it arose) and idempotent.

Action: for every album that is monitored AND has zero bytes on disk AND whose
artist is unmonitored (exactly the arr-orphan-monitor-flags condition), set that
artist monitored=true via PUT /api/v1/artist/{id}. This does NOT change any
album's monitored flag and does NOT trigger a search — Lidarr has no automatic
missing-album search here, so no surprise grabs; it only makes the already-
requested album visible/retryable in wanted/missing, which is the whole point.

Env: LIDARR_API_KEY (required), LIDARR_URL (default http://192.168.10.4:8686),
HEALTHCHECKS_PING_URL (optional dead-man ping).

Prints one line; exit 0 on success (whether or not it flipped anything), non-zero
only on an API/config error (so OnFailure=ntfy fires on a real break, not on the
steady state of "nothing to do").
"""
import json
import os
import sys
import urllib.request

BASE = os.environ.get("LIDARR_URL", "http://192.168.10.4:8686").rstrip("/") + "/api/v1"
KEY = os.environ.get("LIDARR_API_KEY")


def api(path, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE + path, data=data, method=method,
        headers={"X-Api-Key": KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


def main():
    if not KEY:
        print("CONFIG_ERR missing LIDARR_API_KEY")
        sys.exit(1)
    try:
        artists = {a["id"]: a for a in api("/artist")}
        albums = api("/album")
    except Exception as e:  # noqa: BLE001 — any API failure is a real break
        print(f"API_ERR {type(e).__name__}: {e}")
        sys.exit(1)

    # Which artists own a monitored + fileless album while being unmonitored?
    to_fix = {}
    for al in albums:
        if not al.get("monitored"):
            continue
        if (al.get("statistics", {}).get("sizeOnDisk") or 0) > 0:
            continue
        art = artists.get(al.get("artistId"))
        if art and not art.get("monitored"):
            to_fix.setdefault(art["id"], art)

    if not to_fix:
        print(f"RECONCILE_OK flipped=0 artists={len(artists)} albums={len(albums)}")
        _ping()
        return

    flipped = []
    for aid, art in to_fix.items():
        try:
            full = api(f"/artist/{aid}")   # PUT wants the full resource
            full["monitored"] = True
            api(f"/artist/{aid}", method="PUT", body=full)
            flipped.append(full.get("artistName", str(aid)))
        except Exception as e:  # noqa: BLE001
            print(f"API_ERR flipping artist {aid}: {type(e).__name__}: {e}")
            sys.exit(1)

    print(f"RECONCILE_OK flipped={len(flipped)}: " + "; ".join(flipped))
    _ping()


def _ping():
    url = os.environ.get("HEALTHCHECKS_PING_URL")
    if not url:
        return
    try:
        urllib.request.urlopen(url, timeout=10).read()
    except Exception:  # noqa: BLE001 — ping failure only; grace window will alert
        print("WARN: healthchecks ping failed")


if __name__ == "__main__":
    main()
