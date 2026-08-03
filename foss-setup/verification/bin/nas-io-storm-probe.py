#!/usr/bin/env python3
"""fix-55 NAS I/O-storm probes — the consumer-end signal that was missing.

Runs on the mini (the verification runner). Two modes:

  io     Assert the NAS is not I/O-saturated. Synology's patched `uptime` splits
         the load average into a CPU component and an I/O component:
             load average: 3.1, 3.0, 2.8 [IO: 2.9, 2.8, 2.7 CPU: 0.2, 0.2, 0.1]
         We read the 15-MINUTE I/O component (the sustained figure — a momentary
         spike from a Plex transcode or a probe must NOT page) and require it below
         NAS_IO_LOAD_THRESHOLD. During the fix-55 storm this sat at 17-22 while the
         chronic-quiet baseline is ~2.8; the threshold (default 12) fires on real,
         sustained pressure BEFORE it starves the arrs' SQLite into 'database is
         locked' 500s. This is the class-level tripwire.

  locks  Assert the NAS arrs are not in a SQLite 'database is locked' storm — the
         exact regression (SH1/SH10). For each arr whose API key is in the runner
         env, pull the most recent error-log records and count 'database is locked'
         entries within the last LOCK_WINDOW_MIN minutes; require the fleet total at
         or below LOCK_MAX. A time window (not "N most-recent records") so lingering
         old lock records age out and the check greens once the storm actually stops.

Always exits 0; PASS/FAIL is decided by the runner's `expect` regex on stdout
(`status=OK`). Deployed to /opt/verification/bin via scripts/verification/deploy.sh.
"""
import datetime
import json
import os
import re
import subprocess
import sys
import urllib.request

IO_THRESHOLD = float(os.environ.get("NAS_IO_LOAD_THRESHOLD", "12"))
NAS = os.environ.get("NAS_SSH_HOST", "nas")
LOCK_WINDOW_MIN = 15
LOCK_MAX = int(os.environ.get("ARR_LOCK_MAX", "5"))

# arrs that keep SQLite DBs and showed the lock storm (SH1). sonarr is deliberately
# omitted — it never locked (own-DB layout differs), so it is a control, not a signal.
ARRS = [
    ("lidarr", "8686", "v1"),
    ("radarr", "7878", "v3"),
    ("whisparr", "6969", "v3"),
]


def probe_io():
    try:
        out = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", NAS, "uptime"],
            capture_output=True, text=True, timeout=25).stdout
    except Exception as e:  # noqa: BLE001
        print(f"nas_io_load15=NA status=ERR probe_failed={type(e).__name__}")
        return
    m = re.search(r"IO:\s*[0-9.]+,\s*[0-9.]+,\s*([0-9.]+)", out)
    if not m:
        # Non-Synology uptime (no [IO:] field) — fall back to the plain 15-min
        # load average so the check still means something rather than silently ERR.
        m = re.search(r"load average:\s*[0-9.]+,\s*[0-9.]+,\s*([0-9.]+)", out)
        if not m:
            print("nas_io_load15=NA status=ERR no_load_field")
            return
    v = float(m.group(1))
    status = "OK" if v < IO_THRESHOLD else "HIGH"
    print(f"nas_io_load15={v:.2f} threshold={IO_THRESHOLD:.0f} status={status}")


def probe_locks():
    now = datetime.datetime.now(datetime.timezone.utc)
    total = 0
    parts = []
    for name, port, ver in ARRS:
        key = os.environ.get(f"{name.upper()}_API_KEY")
        if not key:
            parts.append(f"{name}=nokey")
            continue
        url = (f"http://192.168.10.4:{port}/api/{ver}/log"
               f"?page=1&pageSize=40&sortKey=time&sortDirection=descending&level=error")
        try:
            req = urllib.request.Request(url, headers={"X-Api-Key": key})
            with urllib.request.urlopen(req, timeout=15) as r:
                d = json.loads(r.read())
        except Exception:  # noqa: BLE001
            parts.append(f"{name}=err")
            continue
        cnt = 0
        for rec in d.get("records", []):
            blob = (str(rec.get("exception", "")) + str(rec.get("message", ""))).lower()
            if "database is locked" not in blob:
                continue
            try:
                ts = datetime.datetime.fromisoformat(
                    rec.get("time", "").replace("Z", "+00:00"))
                age_min = (now - ts).total_seconds() / 60.0
            except Exception:  # noqa: BLE001 — unparseable ts -> treat as old, don't count
                age_min = 1e9
            if age_min <= LOCK_WINDOW_MIN:
                cnt += 1
        total += cnt
        parts.append(f"{name}={cnt}")
    status = "OK" if total <= LOCK_MAX else "STORM"
    print(f"arr_locked_last{LOCK_WINDOW_MIN}m={total} max={LOCK_MAX} "
          f"status={status} [{' '.join(parts)}]")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "io"
    if mode == "io":
        probe_io()
    elif mode == "locks":
        probe_locks()
    else:
        print(f"status=ERR unknown_mode={mode}")
