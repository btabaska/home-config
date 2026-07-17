#!/usr/bin/env python3
"""
lidarr-incomplete-albums.py — fix-28 (M34) regression + class check.

M34: 'The Marshall Mathers LP' sat at 17/18 tracks on disk — Lidarr green (album
monitored, auto-searching) but Plex/Navidrome served an incomplete album silently
because the source download was missing track 1. Liveness never noticed: Lidarr
was up and the album "had files".

This is the CONSUMER invariant: a monitored album must not be served PARTIAL. Flags
albums that have SOME but not ALL tracks on disk (0 < trackFileCount < total) and
are monitored — i.e. silently incomplete. Albums that are fully missing (0 files,
not yet acquired) are NOT flagged (that is normal backlog, not a served-incomplete
album), and albums with an active download in the Lidarr queue are excluded to
avoid tripping on in-flight grabs.

Fails LOUDLY if Lidarr is unreachable. One line:
  ALBUMS_OK   partial=0 checked=A
  ALBUMS_BAD  partial=N  e.g. 'Artist - Album'(17/18) ...
  ALBUMS_ERR  <reason>
"""
import os, sys, json, urllib.request

LID = (os.environ.get("LIDARR_URL", "http://192.168.10.4:8686").rstrip("/"), os.environ.get("LIDARR_API_KEY"))

def lid(path):
    r = urllib.request.Request(LID[0] + path, headers={"X-Api-Key": LID[1], "Accept": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=90))

def main():
    if not LID[1]:
        print("ALBUMS_ERR missing LIDARR_API_KEY in env"); return 2
    try:
        recs = lid("/api/v1/wanted/missing?pageSize=1000&includeArtist=true").get("records", [])
        queue = lid("/api/v1/queue?pageSize=500")
    except Exception as e:
        print(f"ALBUMS_ERR lidarr unreachable: {e}"); return 2
    downloading = {q.get("albumId") for q in queue.get("records", [])}
    partial = []
    for a in recs:
        if not a.get("monitored"):
            continue
        st = a.get("statistics", {})
        tfc = st.get("trackFileCount", 0)
        tot = st.get("totalTrackCount", 0) or st.get("trackCount", 0)
        if 0 < tfc < tot and a.get("id") not in downloading:
            art = (a.get("artist") or {}).get("artistName", "?")
            partial.append(f"{art} - {a.get('title')}({tfc}/{tot})")
    if partial:
        print(f"ALBUMS_BAD partial={len(partial)} :: " + " ".join(repr(p) for p in partial[:25]))
        return 1
    print(f"ALBUMS_OK partial=0 checked={len(recs)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
