#!/usr/bin/env python3
"""Detect the silent "grabbed -> never imported" class across every *arr (fix-25).

The 2026-07-16 quality gate found two shapes of this (H3, H5): a grab handed to
the download client that then VANISHES (hash absent from Deluge, queue empty,
no error anywhere), and a completed torrent that fell out of the arr's tracking
without importing. Both leave: a 'grabbed' history event with NO follow-up
event, an empty queue, and media with no file — while every liveness signal
stays green.

Modes:
  grabs         — for each arr, take recent 'grabbed' history events older than
                  48h (younger = in-flight); STUCK if the download id has no
                  follow-up event (imported/failed/deleted all count as "the
                  arr noticed"), is not in the queue, and the media still has
                  no file (a later re-grab that imported clears it).
  monitor-flags — the H6/H14 root-cause tripwire: monitored media that is
                  INVISIBLE to wanted/missing because its parent is unmonitored
                  (bookshelf book with unmonitored author, lidarr album with
                  unmonitored artist) is un-retryable: a failed first search is
                  permanent. Must always be zero.

Env: SONARR_API_KEY RADARR_API_KEY LIDARR_API_KEY BOOKSHELF_API_KEY WHISPARR_API_KEY.
(bookshelf replaced the retired readarr backend in bmig-06, 2026-07-20.)
Prints one line; expect-regex friendly:
  GRABS_OK checked=N   | GRABS_STUCK n: arr:title; ...
  FLAGS_OK checked=N   | FLAGS_HIDDEN n: arr:title; ...
  CONFIG_ERR ... (never a vacuous pass)
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

STUCK_AFTER_H = 48
LOOKBACK_D = 14

ARRS = {
    "sonarr": ("http://192.168.10.4:8989", "v3", "SONARR_API_KEY"),
    "radarr": ("http://192.168.10.4:7878", "v3", "RADARR_API_KEY"),
    "lidarr": ("http://192.168.10.4:8686", "v1", "LIDARR_API_KEY"),
    "bookshelf": ("http://192.168.10.4:8790", "v1", "BOOKSHELF_API_KEY"),
    "whisparr": ("http://192.168.10.4:6969", "v3", "WHISPARR_API_KEY"),
}


def api(base, ver, key, path):
    req = urllib.request.Request(f"{base}/api/{ver}{path}", headers={"X-Api-Key": key})
    return json.load(urllib.request.urlopen(req, timeout=20))


def age_hours(iso):
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - dt).total_seconds() / 3600


def media_has_file(arr, base, ver, key, rec):
    """Does the media item behind this history record have a file now?"""
    try:
        if arr == "radarr" and rec.get("movieId"):
            return api(base, ver, key, f"/movie/{rec['movieId']}").get("hasFile", False)
        if arr in ("sonarr", "whisparr") and rec.get("episodeId"):
            return api(base, ver, key, f"/episode/{rec['episodeId']}").get("hasFile", False)
        if arr == "lidarr" and rec.get("albumId"):
            st = api(base, ver, key, f"/album/{rec['albumId']}").get("statistics", {})
            return (st.get("sizeOnDisk") or 0) > 0
        if arr == "bookshelf" and rec.get("bookId"):
            st = api(base, ver, key, f"/book/{rec['bookId']}").get("statistics", {})
            return (st.get("bookFileCount") or 0) > 0
    except Exception:
        return False  # can't prove a file exists -> keep it flagged
    return False


def mode_grabs():
    stuck, checked = [], 0
    for arr, (base, ver, envk) in ARRS.items():
        key = os.environ.get(envk)
        if not key:
            print(f"CONFIG_ERR missing {envk}")
            sys.exit(1)
        hist = api(base, ver, key,
                   "/history?pageSize=200&sortKey=date&sortDirection=descending")
        queue = api(base, ver, key, "/queue?pageSize=200")
        in_queue = {(r.get("downloadId") or "").upper()
                    for r in queue.get("records", []) if r.get("downloadId")}
        seen = set()
        for rec in hist.get("records", []):
            if rec.get("eventType") != "grabbed":
                continue
            did = (rec.get("downloadId") or "").upper()
            if not did or did in seen:
                continue
            seen.add(did)
            h = age_hours(rec["date"])
            if h < STUCK_AFTER_H or h > LOOKBACK_D * 24:
                continue
            checked += 1
            if did in in_queue:
                continue
            try:
                # downloadId is not always a bare hash (slskd/soularr grabs use
                # free-text ids with spaces) — must be URL-encoded
                events = api(base, ver, key,
                             f"/history?downloadId={urllib.parse.quote(did, safe='')}&pageSize=100")
                evtypes = {e.get("eventType") for e in events.get("records", [])}
                if evtypes - {"grabbed"}:
                    continue  # the arr noticed (import/fail/delete) — not silent
            except Exception:
                pass  # can't read follow-up events -> fall through to the file probe
            if media_has_file(arr, base, ver, key, rec):
                continue  # recovered via another grab
            stuck.append(f"{arr}:{(rec.get('sourceTitle') or '?')[:50]}")
    if stuck:
        print(f"GRABS_STUCK {len(stuck)}: " + "; ".join(stuck[:6]))
        sys.exit(1)
    print(f"GRABS_OK checked={checked}")


def mode_monitor_flags():
    hidden, checked = [], 0
    key = os.environ.get("BOOKSHELF_API_KEY")
    if not key:
        print("CONFIG_ERR missing BOOKSHELF_API_KEY")
        sys.exit(1)
    # The bulk /book endpoint omits the nested author object entirely (verified
    # live 2026-07-17, fix-26) — resolving the embedded field made every
    # monitored+fileless book a false positive. Resolve parents via /author.
    authors = {a["id"]: a for a in api(*ARRS["bookshelf"][:2], key, "/author")}
    for b in api(*ARRS["bookshelf"][:2], key, "/book"):
        if not b.get("monitored"):
            continue
        checked += 1
        parent = authors.get(b.get("authorId")) or b.get("author") or {}
        if ((b.get("statistics", {}).get("bookFileCount") or 0) == 0
                and not parent.get("monitored")):
            hidden.append(f"bookshelf:{(b.get('title') or '?')[:40]}")
    key = os.environ.get("LIDARR_API_KEY")
    if not key:
        print("CONFIG_ERR missing LIDARR_API_KEY")
        sys.exit(1)
    artists = {a["id"]: a for a in api(*ARRS["lidarr"][:2], key, "/artist")}
    for a in api(*ARRS["lidarr"][:2], key, "/album"):
        if not a.get("monitored"):
            continue
        checked += 1
        parent = artists.get(a.get("artistId")) or a.get("artist") or {}
        if ((a.get("statistics", {}).get("sizeOnDisk") or 0) == 0
                and not parent.get("monitored")):
            hidden.append(f"lidarr:{(a.get('title') or '?')[:40]}")
    if hidden:
        print(f"FLAGS_HIDDEN {len(hidden)}: " + "; ".join(hidden[:6]))
        sys.exit(1)
    print(f"FLAGS_OK checked={checked}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "grabs":
        mode_grabs()
    elif mode == "monitor-flags":
        mode_monitor_flags()
    else:
        print("CONFIG_ERR usage: arr-grab-audit.py grabs|monitor-flags")
        sys.exit(1)
