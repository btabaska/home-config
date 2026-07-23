#!/usr/bin/env python3
"""
abs-ipod-verify.py — consumer-end verification for the Audiobookshelf->iPod sync.
Runs on the rig (host: rig in the verification runner).

PRODUCER side (always, hard-fail): the staging manifest exists, is non-empty, and
every staged file it references is present on disk. Catches a silently-broken
staging run even when the iPod is nowhere near the rig.

CONSUMER side (best-effort, only when an iPod is mounted): confirm the iTunesDB
actually holds the staged audiobook + podcast tracks. A plugged-in-but-not-yet-
synced iPod is a normal state, so it PASSES (never pages on transient device state).

Prints exactly one token (first word is what the check matches):
  IPOD_SYNC_OK          iPod mounted and all staged items present in its DB   -> pass
  IPOD_MOUNTED_UNSYNCED iPod mounted but staged items not pushed yet          -> pass
  IPOD_ABSENT           iPod not mounted (the usual case), stage healthy      -> pass
  STAGE_MISSING / STAGE_MISSING_FILES                                         -> FAIL (exit 1)
"""
import glob, json, os, sys, time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
HOME = Path.home()
MANIFEST = Path(os.environ.get("MANIFEST", HOME / ".ipod-abs-manifest.json"))


def fail(tok, *a):
    print(tok, *[str(x) for x in a]); sys.exit(1)


def main():
    if not MANIFEST.exists():
        fail("STAGE_MISSING", "no manifest at", MANIFEST, "(has abs-ipod-stage run?)")
    man = json.loads(MANIFEST.read_text())
    abs_items = man.get("audiobooks", [])
    pc_items = man.get("podcasts", [])
    abs_n, pc_n = len(abs_items), len(pc_items)

    missing = [e["path"] for e in abs_items + pc_items if not Path(e["path"]).exists()]
    if missing:
        fail("STAGE_MISSING_FILES", len(missing), "staged files missing e.g.", missing[0])
    age_h = (time.time() - man.get("generated", 0)) / 3600.0

    mount = None
    for ctrl in glob.glob("/run/media/*/*/iPod_Control") + glob.glob("/media/*/*/iPod_Control") + glob.glob("/mnt/ipod/iPod_Control"):
        mount = str(Path(ctrl).parent)
        break
    if not mount:
        print(f"IPOD_ABSENT stage_ok audiobooks={abs_n} podcasts={pc_n} manifest_age_h={age_h:.0f}")
        return

    import libgpod_abs as g
    db = g.iPodDatabase(mount)
    try:
        keys = db.existing_keys()
    finally:
        db.close(write=False)

    unsynced = []
    for a in abs_items:
        if (g.ITDB_MEDIATYPE_AUDIOBOOK, a["album"], a["title"]) not in keys:
            unsynced.append("AB:" + a["title"])
    for p in pc_items:
        if (g.ITDB_MEDIATYPE_PODCAST, p["podcast_title"], p["episode_title"]) not in keys:
            unsynced.append("PC:" + p["episode_title"][:30])
    if unsynced:
        # normal (staged newer than last push) — informational pass, not a failure
        print(f"IPOD_MOUNTED_UNSYNCED pending={len(unsynced)} e.g. {unsynced[0]} (run abs-ipod-sync)")
        return
    print(f"IPOD_SYNC_OK audiobooks={abs_n} podcasts={pc_n} all_present_on_ipod")


if __name__ == "__main__":
    main()
