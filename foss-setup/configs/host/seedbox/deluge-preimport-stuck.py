#!/usr/bin/env python3
# Verification probe (fix-25, L42/M23 class): a torrent that is 100% complete
# but still in a PRE-import label >48h after finishing means the arr's
# Post-Import Category relabel never happened — i.e. the download completed but
# the import path is broken/stalled (or the label config regressed). This is
# the alarm that guards the reaper: nothing may age toward the 14d reap while
# stuck pre-import without a warning first.
# Deploy: scp configs/host/seedbox/deluge-preimport-stuck.py seedbox:scripts/
# Run:    ~/venvs/deluge/bin/python ~/scripts/deluge-preimport-stuck.py
# Output: PREIMPORT_OK checked=N | PREIMPORT_STUCK n: [label] name; ...
import os, time
from deluge.ui.client import client
from twisted.internet import reactor, defer

PRE_IMPORT = {"sonarr", "tv-sonarr", "radarr", "lidarr", "readarr", "tv-whisparr"}
STUCK_AFTER = 48 * 3600
EXIT = [0]

def localauth():
    for line in open(os.path.expanduser("~/.config/deluge/auth")):
        p = line.strip().split(":")
        if len(p) >= 2 and p[0] == "btabaska":
            return p[0], p[1]
    raise SystemExit("no btabaska auth")

@defer.inlineCallbacks
def main():
    try:
        u, p = localauth()
        yield client.connect("127.0.0.1", 3254, u, p)
        st = yield client.core.get_torrents_status(
            {}, ["name", "label", "progress", "completed_time", "time_added"])
        now = time.time()
        checked, stuck = 0, []
        for h, v in st.items():
            if (v.get("label") or "") not in PRE_IMPORT:
                continue
            if (v.get("progress") or 0) < 99.9:
                continue
            checked += 1
            done_at = v.get("completed_time") or v.get("time_added") or now
            if now - done_at > STUCK_AFTER:
                stuck.append(f"[{v.get('label')}] {(v.get('name') or '?')[:55]}")
        if stuck:
            print(f"PREIMPORT_STUCK {len(stuck)}: " + "; ".join(stuck[:5]))
            EXIT[0] = 1
        else:
            print(f"PREIMPORT_OK checked={checked}")
    except Exception as e:
        print("CONFIG_ERR " + repr(e))
        EXIT[0] = 1
    finally:
        try:
            client.disconnect()
        except Exception:
            pass
        reactor.stop()

main()
reactor.run()
raise SystemExit(EXIT[0])
