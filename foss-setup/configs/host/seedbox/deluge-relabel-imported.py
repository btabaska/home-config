#!/usr/bin/env python3
"""Verify-then-relabel: move confirmed-imported Deluge torrents to <label>-imported.

One-time/maintenance tool for the L42 class (fix-25): torrents that finished
BEFORE the *arr Post-Import Category existed stay in their pre-import label
forever, so the reaper never ages them out. This script:

  1. pulls every 100%-complete torrent in a pre-import label from Deluge
     (over `ssh seedbox`, RPC on 127.0.0.1:3254 — see deluge-queue-hygiene wiki page),
  2. asks the OWNING *arr's history (by downloadId=hash) whether the grab was
     actually imported — only an import event counts, presence on disk is not
     checked here,
  3. relabels VERIFIED torrents to <label>-imported; anything unverified is
     left alone (the deluge-preimport-stuck verification check will flag it).

Run FROM a workstation with LAN access to the NAS arrs + `ssh seedbox` alias
(the seedbox itself cannot reach the arrs). Default DRY-RUN; pass --live.

    python3 deluge-relabel-imported.py --secrets ../../.handoff-secrets.yaml [--live]
"""
import argparse
import json
import subprocess
import sys
import urllib.request

import yaml

# pre-import label -> (arr base url, api version, secrets key under arr_api_keys)
LABEL_MAP = {
    "sonarr": ("http://192.168.10.4:8989", "v3", "sonarr"),
    "tv-sonarr": ("http://192.168.10.4:8989", "v3", "sonarr"),
    "radarr": ("http://192.168.10.4:7878", "v3", "radarr"),
    "lidarr": ("http://192.168.10.4:8686", "v1", "lidarr"),
    "readarr": ("http://192.168.10.4:8787", "v1", "readarr"),
    "tv-whisparr": ("http://192.168.10.4:6969", "v3", "whisparr"),
}

DELUGE_DUMP = r"""
import json, os
from deluge.ui.client import client
from twisted.internet import reactor, defer

def localauth():
    for line in open(os.path.expanduser("~/.config/deluge/auth")):
        p = line.strip().split(":")
        if len(p) >= 2 and p[0] == "btabaska":
            return p[0], p[1]
    raise SystemExit("no auth")

@defer.inlineCallbacks
def main():
    try:
        u, p = localauth()
        yield client.connect("127.0.0.1", 3254, u, p)
        st = yield client.core.get_torrents_status({}, ["name", "label", "progress"])
        out = [
            {"hash": h, "name": v.get("name"), "label": v.get("label") or ""}
            for h, v in st.items()
            if (v.get("progress") or 0) >= 99.9
        ]
        print(json.dumps(out))
    finally:
        try:
            client.disconnect()
        except Exception:
            pass
        reactor.stop()

main()
reactor.run()
"""

# __MOVES__ is replaced with the JSON list before the script is sent
DELUGE_RELABEL = r"""
import json, os
from deluge.ui.client import client
from twisted.internet import reactor, defer

moves = json.loads('''__MOVES__''')  # [{"hash":..., "to":...}]

def localauth():
    for line in open(os.path.expanduser("~/.config/deluge/auth")):
        p = line.strip().split(":")
        if len(p) >= 2 and p[0] == "btabaska":
            return p[0], p[1]
    raise SystemExit("no auth")

@defer.inlineCallbacks
def main():
    try:
        u, p = localauth()
        yield client.connect("127.0.0.1", 3254, u, p)
        for m in moves:
            yield client.label.set_torrent(m["hash"], m["to"])
        print("relabeled %d" % len(moves))
    finally:
        try:
            client.disconnect()
        except Exception:
            pass
        reactor.stop()

main()
reactor.run()
"""


def arr_imported(base: str, ver: str, key: str, torrent_hash: str) -> bool:
    """True iff the arr's history shows an import event for this download id."""
    url = f"{base}/api/{ver}/history?downloadId={torrent_hash.upper()}&pageSize=100"
    req = urllib.request.Request(url, headers={"X-Api-Key": key})
    try:
        data = json.load(urllib.request.urlopen(req, timeout=30))
    except Exception as e:
        print(f"    WARN history query failed for {torrent_hash[:12]}: {e}", file=sys.stderr)
        return False
    records = data.get("records", data if isinstance(data, list) else [])
    return any("imported" in (r.get("eventType") or "").lower() for r in records)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--secrets", required=True, help="path to .handoff-secrets.yaml")
    ap.add_argument("--live", action="store_true", help="actually relabel (default dry-run)")
    ap.add_argument("--ssh-alias", default="seedbox")
    args = ap.parse_args()

    keys = yaml.safe_load(open(args.secrets))["arr_api_keys"]
    remote_py = "~/venvs/deluge/bin/python"

    dump = subprocess.run(
        ["ssh", args.ssh_alias, f"{remote_py} -"],
        input=DELUGE_DUMP, capture_output=True, text=True, check=True,
    )
    torrents = json.loads(dump.stdout.strip().splitlines()[-1])
    pre = [t for t in torrents if t["label"] in LABEL_MAP]
    print(f"{len(torrents)} complete torrents, {len(pre)} in pre-import labels")

    moves, unverified = [], []
    for t in pre:
        base, ver, kname = LABEL_MAP[t["label"]]
        if arr_imported(base, ver, keys[kname], t["hash"]):
            to = ("sonarr-imported" if t["label"] == "tv-sonarr"
                  else t["label"] + "-imported")
            moves.append({"hash": t["hash"], "to": to})
        else:
            unverified.append(t)

    print(f"verified imported: {len(moves)} | unverified (left alone): {len(unverified)}")
    for t in unverified:
        print(f"  UNVERIFIED [{t['label']}] {t['name'][:70]}")

    if not moves:
        return
    if not args.live:
        print("DRY-RUN: no labels changed (pass --live to relabel)")
        return
    res = subprocess.run(
        ["ssh", args.ssh_alias, f"{remote_py} -"],
        input=DELUGE_RELABEL.replace("__MOVES__", json.dumps(moves)),
        capture_output=True, text=True, check=True,
    )
    print(res.stdout.strip())


if __name__ == "__main__":
    main()
