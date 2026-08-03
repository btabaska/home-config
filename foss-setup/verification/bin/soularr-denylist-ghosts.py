#!/usr/bin/env python3
"""fix-56 (SM29) class+regression check: soularr's failed-import denylist holds
NO ghost — i.e. no entry whose album is, per live Lidarr, already COMPLETE,
UNMONITORED, or DELETED.

soularr (ghcr.io/mrusse/soularr:1.2.2) appends to
nas:/volume1/docker/soularr/failed_imports.json on every failed import and never
removes an entry (upstream add-only, verified in /app/soularr.py), so the file
rots into a dead-letter of albums that completed elsewhere or were unmonitored.
The soularr-denylist-reconcile mini timer (every 6h) prunes exactly those; this
check is its OUTCOME probe — it catches ghost re-accumulation LONG before the
3-day nas-soularr-failed-imports-fresh staleness tripwire would, and it probes
the consumer invariant (denylist == genuinely-stuck monitored+incomplete albums
only), not liveness.

Runs on the mini: reads the NAS denylist over ssh (btabaska key-based) and
queries Lidarr (v1) for each entry. Reads only — never mutates.

Env: LIDARR_API_KEY (required), LIDARR_URL (default http://192.168.10.4:8686),
NAS_SSH (default "nas"), DENYLIST_PATH (default the NAS soularr path).
Output one line:
  DENYLIST_OK entries=N ghosts=0
  DENYLIST_BAD ghosts=X: 'Title'(complete|unmonitored|deleted) ...
  DENYLIST_ERR <reason>
"""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("LIDARR_URL", "http://192.168.10.4:8686").rstrip("/") + "/api/v1"
KEY = os.environ.get("LIDARR_API_KEY")
NAS = os.environ.get("NAS_SSH", "nas")
DENYLIST = os.environ.get("DENYLIST_PATH", "/volume1/docker/soularr/failed_imports.json")


def album(aid):
    req = urllib.request.Request(f"{BASE}/album/{aid}", headers={"X-Api-Key": KEY,
                                                                 "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def ghost_reason(aid):
    a = album(aid)
    if a is None:
        return "deleted"
    if not a.get("monitored"):
        return "unmonitored"
    st = a.get("statistics", {}) or {}
    tot = st.get("totalTrackCount") or st.get("trackCount") or 0
    if tot > 0 and st.get("trackFileCount", 0) >= tot:
        return "complete"
    return None


def main():
    if not KEY:
        print("DENYLIST_ERR missing LIDARR_API_KEY"); return 2
    try:
        out = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
                              NAS, "cat", DENYLIST],
                             capture_output=True, text=True, timeout=30)
    except Exception as e:  # noqa: BLE001
        print(f"DENYLIST_ERR ssh {type(e).__name__}: {e}"); return 2
    if out.returncode != 0:
        if "No such file" in out.stderr:
            print("DENYLIST_OK entries=0 ghosts=0"); return 0
        print(f"DENYLIST_ERR ssh rc={out.returncode}: {out.stderr.strip()[:80]}"); return 2
    txt = out.stdout.strip()
    denylist = json.loads(txt) if txt else {}
    if not denylist:
        print("DENYLIST_OK entries=0 ghosts=0"); return 0

    ghosts = []
    try:
        for k, v in denylist.items():
            reason = ghost_reason(k)
            if reason:
                ghosts.append(f"{v.get('title', k)!r}({reason})")
    except Exception as e:  # noqa: BLE001 — a Lidarr failure is a real break
        print(f"DENYLIST_ERR lidarr {type(e).__name__}: {e}"); return 2

    if ghosts:
        print(f"DENYLIST_BAD ghosts={len(ghosts)}: " + " ".join(ghosts[:15]))
        return 1
    print(f"DENYLIST_OK entries={len(denylist)} ghosts=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
