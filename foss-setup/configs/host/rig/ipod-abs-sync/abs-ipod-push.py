#!/usr/bin/env python3
"""
abs-ipod-push.py — push staged Audiobookshelf content onto a mounted iPod Classic.

Reads ~/.ipod-abs-manifest.json (produced by abs-ipod-stage.py) and writes each
audiobook / podcast episode into the iPod's iTunesDB with the correct mediatype so
they land in the native Audiobooks and Podcasts menus (NOT dumped into Music), with
resume-position memory. Idempotent: tracks already on the device (matched by
mediatype+album+title) are skipped, so it is safe to re-run.

This is the ONLY step that writes to the iPod. Music stays owned by Rhythmbox; run
this after (or before) a Rhythmbox music sync — never concurrently.

Usage:
  abs-ipod-push.py --list              # show what is currently on the iPod
  abs-ipod-push.py --dry-run           # show what WOULD be added, write nothing
  abs-ipod-push.py                     # add missing items, write the DB
  abs-ipod-push.py --eject             # ...then sync + unmount for safe unplug
"""
import argparse, json, os, subprocess, sys, glob
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import libgpod_abs as g

HOME = Path.home()
MANIFEST = Path(os.environ.get("MANIFEST", HOME / ".ipod-abs-manifest.json"))
MT_NAME = {g.ITDB_MEDIATYPE_AUDIO: "music", g.ITDB_MEDIATYPE_PODCAST: "podcast",
           g.ITDB_MEDIATYPE_AUDIOBOOK: "audiobook"}


def find_ipod(explicit=None):
    if explicit:
        return explicit
    if os.environ.get("IPOD_MOUNT"):
        return os.environ["IPOD_MOUNT"]
    user = os.environ.get("USER", "btabaska")
    for ctrl in glob.glob(f"/run/media/{user}/*/iPod_Control") + glob.glob("/media/*/iPod_Control") + glob.glob("/mnt/ipod/iPod_Control"):
        return str(Path(ctrl).parent)
    return None


def block_device(mount):
    r = subprocess.run(["findmnt", "-n", "-o", "SOURCE", "--target", mount],
                       capture_output=True, text=True)
    return r.stdout.strip() or None


def do_list(db):
    counts = {}
    for (mt, alb, tit, _t) in db.all_tracks():
        counts[mt] = counts.get(mt, 0) + 1
    print("On the iPod now:")
    for mt, n in sorted(counts.items()):
        print(f"  {MT_NAME.get(mt, 'mediatype '+str(mt)):>10}: {n}")
    print("\nAudiobooks + podcasts on device:")
    for (mt, alb, tit, _t) in db.all_tracks():
        if mt in (g.ITDB_MEDIATYPE_AUDIOBOOK, g.ITDB_MEDIATYPE_PODCAST):
            print(f"  [{MT_NAME[mt]}] {alb} — {tit[:60]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mount", help="iPod mount point (else auto-detect)")
    ap.add_argument("--dry-run", action="store_true", help="show what would change, write nothing")
    ap.add_argument("--list", action="store_true", help="list current iPod contents and exit")
    ap.add_argument("--eject", action="store_true", help="sync + unmount after a successful write")
    args = ap.parse_args()

    mount = find_ipod(args.mount)
    if not mount or not Path(mount, "iPod_Control").is_dir():
        sys.exit(f"ERROR: no mounted iPod found (looked for */iPod_Control). "
                 f"Plug in + mount the iPod, or pass --mount. Got: {mount!r}")
    print(f"iPod mount: {mount}")

    db = g.iPodDatabase(mount)
    try:
        if args.list:
            do_list(db)
            return

        if not MANIFEST.exists():
            sys.exit(f"ERROR: manifest {MANIFEST} not found — run abs-ipod-stage.py first.")
        man = json.loads(MANIFEST.read_text())
        existing = db.existing_keys()

        planned = []   # (kind, entry, key)
        for a in man.get("audiobooks", []):
            key = (g.ITDB_MEDIATYPE_AUDIOBOOK, a["album"], a["title"])
            if key not in existing and Path(a["path"]).exists():
                planned.append(("audiobook", a, key))
        for p in man.get("podcasts", []):
            key = (g.ITDB_MEDIATYPE_PODCAST, p["podcast_title"], p["episode_title"])
            if key not in existing and Path(p["path"]).exists():
                planned.append(("podcast", p, key))

        n_ab = sum(1 for k, *_ in planned if k == "audiobook")
        n_pc = sum(1 for k, *_ in planned if k == "podcast")
        print(f"\nManifest: {len(man.get('audiobooks', []))} audiobooks, "
              f"{len(man.get('podcasts', []))} podcast episodes.")
        print(f"Already on device (skip): {len(man.get('audiobooks', [])) + len(man.get('podcasts', [])) - len(planned)}")
        print(f"To add: {n_ab} audiobook(s), {n_pc} podcast episode(s):")
        for kind, e, _key in planned:
            label = e["title"] if kind == "audiobook" else f"{e['podcast_title']} — {e['episode_title']}"
            print(f"  + [{kind}] {label[:70]}")

        if args.dry_run:
            print("\n(dry-run: nothing written)")
            return

        for kind, e, _key in planned:
            if kind == "audiobook":
                db.add_audiobook_track(e["path"], title=e["title"], album=e["album"],
                                       author=e.get("author", "Unknown Author"),
                                       tracklen_ms=e["tracklen_ms"], description=e.get("description", ""),
                                       filetype="m4b")
                print(f"  wrote audiobook: {e['title']}")
            else:
                db.add_podcast_track(e["path"], episode_title=e["episode_title"],
                                     podcast_title=e["podcast_title"], description=e.get("description", ""),
                                     podcast_url=e.get("podcast_url", ""), podcast_rss=e.get("podcast_rss", ""),
                                     published_timestamp=e.get("published", 0), tracklen_ms=e["tracklen_ms"],
                                     filetype=e.get("filetype", "mp3"))
                print(f"  wrote podcast: {e['podcast_title']} — {e['episode_title'][:50]}")

        fixed = db.reconcile_podcasts()   # self-heal podcast->Podcasts-playlist membership
        if fixed:
            print(f"reconciled {fixed} podcast track(s) into the Podcasts playlist")

        if not db.modified:
            print("\nNothing to change — iPod already up to date.")
            return
        print("\nWriting iTunesDB...")
        db.close(write=True)
        print("iTunesDB written OK.")
    finally:
        try:
            db.close(write=False)
        except Exception:
            pass

    if args.eject:
        subprocess.run(["sync"])
        dev = block_device(mount)
        if dev:
            r = subprocess.run(["udisksctl", "unmount", "-b", dev], capture_output=True, text=True)
            print((r.stdout + r.stderr).strip() or f"unmounted {dev}")
            print("Safe to unplug the iPod.")
    else:
        print("\nNOW EJECT before unplugging: `udisksctl unmount -b $(findmnt -no SOURCE --target " + mount +
              ")` or eject in your file manager, so the DB flushes.")


if __name__ == "__main__":
    main()
