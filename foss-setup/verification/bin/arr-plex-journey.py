#!/usr/bin/env python3
"""
arr-plex-journey.py — #6 acceptance check (quality-hardening workstream).

Probes the USER-JOURNEY OUTCOME of the movie/TV pipeline, not container liveness:
"did the media Radarr/Sonarr imported actually become visible/playable in Plex?"

It matches the PRODUCER (Radarr movies with a file / Sonarr series with episode
files) to the CONSUMER (items served in the matching Plex library) by EXTERNAL ID
— tmdb:// for movies, tvdb:// for shows — so it is immune to the item-count-vs-
file-count problem (a show = many episodes; a raw file/count ratio is wrong).

Pass condition is a COVERAGE RATIO (present-in-Plex / checkable-arr-items) >=
--min-ratio, which tolerates the handful of items Plex's agent may not have
matched to an external id, while still catching the real failure class this
workstream exists for: a whole library invisible because of an ACL / path /
dead-scan seam break (exactly the Pinchflat->Plex incident, but for movies/TV).

Fails LOUDLY (non-zero, no COVERAGE_OK) if either API is unreachable or returns
nothing — never a vacuous pass on a down service. Recently-imported movies
(< --settle-hours old, by Radarr movieFile.dateAdded) are excluded so Plex scan
lag is not a false positive.

Prints one line:
  COVERAGE_OK   kind=... checkable=N in_plex=M ratio=R min=... excluded_recent=E
  COVERAGE_LOW  kind=... ... missing=<ids>
  COVERAGE_ERR  <reason>
"""
import argparse
import datetime
import json
import re
import sys
import urllib.parse
import urllib.request


def http_get(url, headers=None, timeout=30):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def arr_items(kind, base, key, timeout):
    """Return (list of (external_id:str, date_added:str|None), guid_scheme)."""
    hdr = {"X-Api-Key": key}
    base = base.rstrip("/")
    if kind == "radarr":
        data = json.loads(http_get(base + "/api/v3/movie", hdr, timeout))
        out = []
        for m in data:
            if m.get("hasFile") and m.get("tmdbId"):
                da = (m.get("movieFile") or {}).get("dateAdded")
                out.append((str(m["tmdbId"]), da))
        return out, "tmdb"
    # sonarr
    data = json.loads(http_get(base + "/api/v3/series", hdr, timeout))
    out = []
    for s in data:
        stats = s.get("statistics") or {}
        if stats.get("episodeFileCount", 0) > 0 and s.get("tvdbId"):
            out.append((str(s["tvdbId"]), None))
    return out, "tvdb"


def plex_guids(plex_url, token, section, scheme, timeout):
    url = plex_url.rstrip("/") + "/library/sections/%s/all?" % section + urllib.parse.urlencode({
        "X-Plex-Token": token,
        "includeGuids": "1",
        "X-Plex-Container-Start": "0",
        "X-Plex-Container-Size": "20000",
    })
    body = http_get(url, timeout=timeout).decode("utf-8", "replace")
    return set(re.findall(scheme + r"://(\d+)", body))


def is_recent(da, cutoff):
    if not da or cutoff is None:
        return False
    try:
        t = datetime.datetime.fromisoformat(da.replace("Z", "+00:00"))
        if t.tzinfo is None:
            t = t.replace(tzinfo=datetime.timezone.utc)
        return t > cutoff
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", required=True, choices=["radarr", "sonarr"])
    ap.add_argument("--arr-url", required=True)
    ap.add_argument("--arr-key", required=True)
    ap.add_argument("--plex-url", required=True)
    ap.add_argument("--plex-token", required=True)
    ap.add_argument("--section", required=True)
    ap.add_argument("--min-ratio", type=float, default=0.9)
    ap.add_argument("--settle-hours", type=float, default=6.0)
    ap.add_argument("--timeout", type=float, default=30.0)
    a = ap.parse_args()

    try:
        items, scheme = arr_items(a.kind, a.arr_url, a.arr_key, a.timeout)
    except Exception as e:  # noqa: BLE001 — any failure must fail loudly
        print("COVERAGE_ERR arr_api %s: %s" % (a.kind, e))
        return 1
    if not items:
        print("COVERAGE_ERR arr_zero_items_with_files kind=%s (down or empty?)" % a.kind)
        return 1

    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=a.settle_hours)
    checkable = [i for (i, da) in items if not is_recent(da, cutoff)]
    excluded = len(items) - len(checkable)
    if not checkable:
        print("COVERAGE_ERR all_items_within_settle_window kind=%s excluded=%d" % (a.kind, excluded))
        return 1

    try:
        pg = plex_guids(a.plex_url, a.plex_token, a.section, scheme, a.timeout)
    except Exception as e:  # noqa: BLE001
        print("COVERAGE_ERR plex_api: %s" % e)
        return 1
    if not pg:
        print("COVERAGE_ERR plex_zero_guids section=%s (unreachable or wrong section?)" % a.section)
        return 1

    present = [i for i in checkable if i in pg]
    ratio = len(present) / len(checkable)
    if ratio >= a.min_ratio:
        print("COVERAGE_OK kind=%s checkable=%d in_plex=%d ratio=%.3f min=%.2f excluded_recent=%d"
              % (a.kind, len(checkable), len(present), ratio, a.min_ratio, excluded))
        return 0
    missing = sorted(set(checkable) - pg)
    print("COVERAGE_LOW kind=%s checkable=%d in_plex=%d ratio=%.3f min=%.2f excluded_recent=%d missing=%s"
          % (a.kind, len(checkable), len(present), ratio, a.min_ratio, excluded, ",".join(missing[:15])))
    return 1


if __name__ == "__main__":
    sys.exit(main())
