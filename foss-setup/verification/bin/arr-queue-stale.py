#!/usr/bin/env python3
"""fix-54 backstop: flag Sonarr/Radarr import-queue records stuck in a 'warning'
state longer than STALE_HOURS (default 96h).

The arr-queue-reconcile timer (mini, every 4h) auto-drops satisfied/dead-end
records once they pass 72h, so in steady state nothing should survive to 96h.
A survivor means one of:
  * the reconciler died / has been failing (also caught by
    arr-queue-reconcile-timer-healthy), or
  * a record the reconciler deliberately leaves for a human — a still-fileless
    wrong-series/wrong-movie map ("matched ... by ID") that needs a manual
    import decision, aged past the point where it should have been resolved.
Either way, look. Probes the arr's live queue (the consumer end), by AGE — the
count-based sonarr/radarr-queue-stuck checks miss a small-but-ancient pile.

Env: SONARR_API_KEY, RADARR_API_KEY (+ optional *_URL). STALE_HOURS override.
Output: STALEQ_OK stale=0 checked=N | STALEQ_BAD stale=X: [arr] title (age d); ...
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

STALE = float(os.environ.get("STALE_HOURS", "96")) * 3600
ARRS = [
    ("sonarr", os.environ.get("SONARR_URL", "http://192.168.10.4:8989"),
     os.environ.get("SONARR_API_KEY")),
    ("radarr", os.environ.get("RADARR_URL", "http://192.168.10.4:7878"),
     os.environ.get("RADARR_API_KEY")),
]


def queue(base, key):
    url = (base.rstrip("/") + "/api/v3/queue?pageSize=500"
           "&includeUnknownSeriesItems=true&includeUnknownMovieItems=true")
    req = urllib.request.Request(url, headers={"X-Api-Key": key})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read()).get("records", [])


def age_s(added, now):
    try:
        return (now - datetime.fromisoformat(added.replace("Z", "+00:00"))).total_seconds()
    except Exception:
        return 0.0


def main():
    now = datetime.now(timezone.utc)
    checked, stale = 0, []
    for name, base, key in ARRS:
        if not key:
            print(f"STALEQ_ERR missing {name.upper()}_API_KEY")
            sys.exit(1)
        try:
            recs = queue(base, key)
        except Exception as e:  # noqa: BLE001 — an API failure is a real break
            print(f"STALEQ_ERR {name} {type(e).__name__}: {e}")
            sys.exit(1)
        for r in recs:
            if r.get("trackedDownloadStatus") != "warning":
                continue
            checked += 1
            a = age_s(r.get("added", ""), now)
            if a > STALE:
                stale.append(f"[{name}] {(r.get('title') or '?')[:45]} ({a/86400:.1f}d)")
    if stale:
        print(f"STALEQ_BAD stale={len(stale)}: " + "; ".join(stale[:6]))
        sys.exit(1)
    print(f"STALEQ_OK stale=0 checked={checked}")


if __name__ == "__main__":
    main()
