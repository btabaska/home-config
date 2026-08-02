#!/usr/bin/env python3
"""fix-50: grab-source sanity + Bitmagnet demotion guard.

The 2026-08-02 fleet sweep (SC2) caught the local Bitmagnet (DHT) Torznab indexer
AUTO-grabbing junk foreign-audio re-releases of already-owned titles ~hourly in
radarr and ~every 30 min in sonarr — 49/50 of radarr's recent grabs were Bitmagnet
— contaminating the movie library with Russian/Bulgarian dub rips (Aliens, Chinatown,
Hotel Transylvania 3, Last Christmas, ...). fix-50 DEMOTED Bitmagnet to
interactive-only (RSS + Automatic Search disabled) via a dedicated Prowlarr
"Interactive-Only (fix-50)" App Sync Profile, which Prowlarr propagates to every arr.

These two checks stop the storm from silently recurring. Liveness (container up,
Torznab 200) is exactly what missed it — these probe the GRAB stream.

modes:
  demoted  — REGRESSION guard for the exact bug: Bitmagnet's arr-side indexer MUST
             carry enableRss=false AND enableAutomaticSearch=false in BOTH radarr
             and sonarr. If a Prowlarr re-sync or an operator flips either back on,
             the auto-grab path reopens and this fails immediately. (An absent /
             removed indexer also cannot storm -> OK.)
  share    — CLASS tripwire for siblings: no single indexer may DOMINATE the recent
             grab stream WHILE it is still auto-grab-enabled (a live junk-grab
             storm, from Bitmagnet or any future runaway indexer). A demoted
             indexer whose OLD storm grabs still sit in history is benign — its
             auto-grab path is closed — so it does not flap this red forever.

env: RADARR_API_KEY SONARR_API_KEY (loaded from /etc/verification/env by the runner).
Prints one line; expect-regex friendly.
"""
import json
import os
import sys
import urllib.request
from collections import Counter

ARRS = {
    "radarr": ("http://192.168.10.4:7878", "v3", "RADARR_API_KEY"),
    "sonarr": ("http://192.168.10.4:8989", "v3", "SONARR_API_KEY"),
}
BITMAGNET = "Bitmagnet (DHT)"
DOMINATE_SHARE = 0.60   # a single indexer at >=60% of recent grabs = dominating
MIN_GRABS = 10          # need a real sample before judging a "storm"


def api(base, ver, key, path):
    req = urllib.request.Request(f"{base}/api/{ver}{path}", headers={"X-Api-Key": key})
    return json.load(urllib.request.urlopen(req, timeout=20))


def _key(envk):
    k = os.environ.get(envk)
    if not k:
        print(f"CONFIG_ERR missing {envk}")
        sys.exit(1)
    return k


def mode_demoted():
    bad, state = [], []
    for arr, (base, ver, envk) in ARRS.items():
        key = _key(envk)
        found = next((i for i in api(base, ver, key, "/indexer")
                      if BITMAGNET in i.get("name", "")), None)
        if not found:
            state.append(f"{arr}:absent")
            continue
        rss, auto = found.get("enableRss"), found.get("enableAutomaticSearch")
        state.append(f"{arr}=rss:{'T' if rss else 'F'}/auto:{'T' if auto else 'F'}")
        if rss or auto:
            bad.append(arr)
    if bad:
        print(f"DEMOTED_FAIL bitmagnet auto-grab ENABLED in {','.join(bad)} | " + " ".join(state))
        sys.exit(1)
    print("DEMOTED_OK " + " ".join(state))


def mode_share():
    grabs = []
    enabled = {}  # indexer name -> auto-grab enabled anywhere
    for arr, (base, ver, envk) in ARRS.items():
        key = _key(envk)
        for i in api(base, ver, key, "/indexer"):
            nm = i.get("name", "")
            enabled[nm] = enabled.get(nm, False) or bool(
                i.get("enableRss") or i.get("enableAutomaticSearch"))
        hist = api(base, ver, key,
                   "/history?pageSize=40&sortKey=date&sortDirection=descending&eventType=1")
        for r in hist.get("records", []):
            grabs.append(r.get("data", {}).get("indexer", "?"))
    n = len(grabs)
    if n < MIN_GRABS:
        print(f"SHARE_OK n={n} (too few recent grabs to judge)")
        return
    top, cnt = Counter(grabs).most_common(1)[0]
    share = cnt / n
    top_live = enabled.get(top, False)
    if share >= DOMINATE_SHARE and top_live:
        print(f"SHARE_STORM top='{top}' share={share:.0%} n={n} auto_enabled=YES "
              "— a live indexer is dominating grabs (junk-grab storm)")
        sys.exit(1)
    print(f"SHARE_OK top='{top}' share={share:.0%} n={n} "
          f"auto_enabled={'YES' if top_live else 'no(demoted/benign)'}")


if __name__ == "__main__":
    m = sys.argv[1] if len(sys.argv) > 1 else ""
    if m == "demoted":
        mode_demoted()
    elif m == "share":
        mode_share()
    else:
        print("CONFIG_ERR usage: arr-grab-indexer-share.py demoted|share")
        sys.exit(1)
