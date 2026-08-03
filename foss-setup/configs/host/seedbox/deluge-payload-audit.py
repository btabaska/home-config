#!/usr/bin/env python3
# Verification probe (fix-54, SH2/SH9/SM26): catch the two silent movie/TV
# import-stall shapes the 2026-08-02 sweep found, at the SOURCE (deluge/disk),
# BEFORE Sonarr/Radarr loop for days on them:
#
#   (1) PAYLOAD-DELETED-UNDER-SEED (SH2/SH9): a torrent deluge reports 100%
#       "Seeding" whose on-disk payload no longer exists. Deluge keeps claiming
#       Seeding from stale state until a recheck, so the arr polls the NAS mount
#       path forever getting "path does not exist / No files found eligible".
#       Root cause on 2026-08-02 was the user quota hitting EDQUOT ([Errno 122]
#       Disk quota exceeded in deluged.log) — payloads dropped under live
#       torrents while the arr had no idea. This is the regression tripwire.
#
#   (2) MOVE_COMPLETED-WEDGE (SM26): a torrent 100% complete but state=Downloading
#       (move_completed never fired) so its file is stranded in ~/files/ root
#       where the arr's /seedbox/tv|movies remote path never sees it — the arr
#       shows a plain "downloading" row invisible to the queue-stuck checks.
#
# Only *arr-labeled and unlabeled torrents are checked (the lanes that feed the
# NAS import). One stat() per completed torrent on the LOCAL seedbox disk (fast).
# Deploy: ssh seedbox 'cat > ~/scripts/deluge-payload-audit.py'
# Run:    ~/venvs/deluge/bin/python ~/scripts/deluge-payload-audit.py
# Output: PAYLOAD_OK checked=N | PAYLOAD_BAD missing=X wedged=Y: [label] name; ...
import os
import time
from deluge.ui.client import client
from twisted.internet import reactor, defer

# Scope is the IMPORT-PIPELINE population only — a torrent still in a PRE-IMPORT
# label (not yet <label>-imported) is one the arr is actively trying to import.
# The already-imported (`-imported`) torrents seed for ratio and are out of scope:
# many legitimately lose their seedbox copy to reaping/quota cleanup (a
# seeding-ratio concern tracked separately), which would swamp this signal.
PRE_IMPORT = {"sonarr", "tv-sonarr", "radarr", "lidarr", "bookshelf", "tv-whisparr", "mylar"}
# Empty label ("") is watched ONLY for the move_completed wedge — a lost-label
# grab (deluge could not persist label.conf under EDQUOT) strands at ~/files/ root.
WEDGE_LABELS = PRE_IMPORT | {""}
WEDGE_AFTER = 24 * 3600  # a 100%-but-Downloading torrent older than this is wedged
EXIT = [0]


def localauth():
    for line in open(os.path.expanduser("~/.config/deluge/auth")):
        p = line.strip().split(":")
        if len(p) >= 2 and p[0] == "btabaska":
            return p[0], p[1]
    raise SystemExit("no btabaska auth")


def payload_path(sp, files):
    """Absolute path of the torrent's top-level entry under its save_path."""
    if not sp or not files:
        return None
    top = (files[0].get("path") or "").split("/")[0]
    return os.path.join(sp, top) if top else None


@defer.inlineCallbacks
def main():
    try:
        u, p = localauth()
        yield client.connect("127.0.0.1", 3254, u, p)
        st = yield client.core.get_torrents_status(
            {}, ["name", "label", "progress", "state", "save_path",
                 "move_completed_path", "completed_time", "time_added", "files"])
        now = time.time()
        checked, missing, wedged = 0, [], []
        for h, v in st.items():
            lbl = v.get("label") or ""
            if lbl not in WEDGE_LABELS:
                continue
            if (v.get("progress") or 0) < 99.9:
                continue
            checked += 1
            name = (v.get("name") or "?")[:52]
            state = v.get("state") or ""
            age = now - (v.get("completed_time") or v.get("time_added") or now)
            # (1) payload deleted under a live Seeding torrent (SH2/SH9) —
            #     pre-import labels only; the arr is blocked polling for it.
            if state == "Seeding" and lbl in PRE_IMPORT:
                pp = payload_path(v.get("save_path"), v.get("files"))
                if pp and not os.path.exists(pp):
                    missing.append(f"[{lbl or '-'}] {name}")
                    continue
            # (2) 100% but never left Downloading -> move_completed wedge (SM26)
            if state in ("Downloading", "Paused") and age > WEDGE_AFTER:
                wedged.append(f"[{lbl or '-'}] {name}")
        if missing or wedged:
            det = "; ".join((missing + wedged)[:6])
            print(f"PAYLOAD_BAD missing={len(missing)} wedged={len(wedged)}: {det}")
            EXIT[0] = 1
        else:
            print(f"PAYLOAD_OK checked={checked}")
    except Exception as e:  # noqa: BLE001 — any RPC/config failure is a real break
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
