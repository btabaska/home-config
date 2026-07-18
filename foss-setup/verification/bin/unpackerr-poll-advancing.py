#!/usr/bin/env python3
"""unpackerr-poll-advancing — fix-29 / L94 consumer-end wedge detector.

The docker healthcheck only proves unpackerr's webserver still answers. The
failure that bit this stack on 2026-07-10 was different: the process was "Up" and
answering, but the poll loop had WEDGED — it did nothing for two days, invisible
to liveness monitoring. This probes the *consumer* function directly via the
now-published metrics port (L94):

  1. unpackerr is reaching every configured Starr app
     (>= MIN_APPS `unpackerr_app_queue_fetch_total` series present), and
  2. the total poll counter is ADVANCING — i.e. the loop is alive.

Advancement is judged against a saved (timestamp, sum) sample so it never
false-alarms when two sweeps fire closer together than the poll interval: it only
declares WEDGED if the counter is frozen for > STALL_S (> two 2-minute cycles).

Prints  UNPACKERR_OK ...  (green) or  UNPACKERR_WEDGED/UNREACHABLE ...  (fail).
"""
import os
import re
import sys
import time
import urllib.request

URL = os.environ.get("UNPACKERR_METRICS_URL", "http://192.168.10.4:5656/metrics")
STATE = "/var/lib/verification/unpackerr-fetch.state"
MIN_APPS = 5          # Sonarr, Radarr, Lidarr, Readarr, Whisparr
STALL_S = 300         # frozen counter for > 5 min (> 2 poll cycles) = wedged


def main():
    try:
        body = urllib.request.urlopen(URL, timeout=8).read().decode()
    except Exception as e:  # noqa: BLE001
        print(f"UNPACKERR_UNREACHABLE ({e})")
        return 1

    fetches = re.findall(
        r"^unpackerr_app_queue_fetch_total\{[^}]*\}\s+([0-9.eE+]+)", body, re.M
    )
    apps = len(fetches)
    cur = int(sum(float(x) for x in fetches))
    now = time.time()

    prev_ts = prev_sum = None
    try:
        with open(STATE) as f:
            parts = f.read().split()
            prev_ts, prev_sum = float(parts[0]), int(parts[1])
    except Exception:  # noqa: BLE001  (first run / unreadable → bootstrap)
        pass

    # Advance the saved sample only when the counter moves (or first run), so the
    # stall clock measures time-since-last-progress, not time-since-last-check.
    if prev_sum is None or cur > prev_sum:
        try:
            os.makedirs(os.path.dirname(STATE), exist_ok=True)
            with open(STATE, "w") as f:
                f.write(f"{now:.0f} {cur}")
        except Exception:  # noqa: BLE001
            pass

    if apps < MIN_APPS:
        print(f"UNPACKERR_WEDGED apps={apps}<{MIN_APPS} polls={cur} "
              "(not reaching every Starr app)")
        return 1
    if prev_sum is None:
        print(f"UNPACKERR_OK apps={apps} polls={cur} (bootstrap sample)")
        return 0
    if cur > prev_sum:
        print(f"UNPACKERR_OK apps={apps} polls={cur} (advanced from {prev_sum})")
        return 0
    frozen_for = now - prev_ts if prev_ts else 0
    if frozen_for > STALL_S:
        print(f"UNPACKERR_WEDGED apps={apps} polls={cur} frozen {frozen_for:.0f}s "
              f"(> {STALL_S}s) — poll loop stalled")
        return 1
    print(f"UNPACKERR_OK apps={apps} polls={cur} (steady, {frozen_for:.0f}s since "
          "last advance — within poll interval)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
