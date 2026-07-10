#!/usr/bin/env python3
"""music-dupes: fail when two album folders in the music library normalize to
the same (artist, album) — the duplicate-library tripwire.

Born 2026-07-10: pre-Lidarr manual copies ("GUTS") coexisted with the
Lidarr-managed folders ("GUTS (2023)") — 3 duplicate pairs, mirrored
faithfully onto the rig and the iPod, invisible to everything. Lidarr can't
create duplicates itself (one canonical folder per album), so any collision
means something wrote into the share around Lidarr — flag it within the hour.

Normalization (deliberately conservative — "(Deluxe Edition)" is a DIFFERENT
release, not a duplicate; only year-suffix/casing/unicode variants collide):
  NFC unicode normalize -> strip one trailing " (YYYY)"/" [YYYY]" -> casefold.

Runs on mini against the read-only CIFS mount (no ssh, no sudo):
  music-dupes.py [/mnt/nas/music]
Prints "DUPES_OK albums=N" (exit 0) or the collision list (exit 1).
Wired as sweep check `music-library-dupes` (checks.d/media.yaml), hourly via
verification-quick.service.
"""
import os
import re
import sys
import unicodedata

ROOT = sys.argv[1] if len(sys.argv) > 1 else "/mnt/nas/music"
SKIP = {"#recycle", "@eaDir", "YouTube"}  # Synology cruft + beets' flat YT rips


def norm(name: str) -> str:
    name = unicodedata.normalize("NFC", name)
    name = re.sub(r"\s*[\(\[](19|20)\d{2}[\)\]]\s*$", "", name)
    return name.strip().casefold()


def main() -> int:
    if not os.path.isdir(ROOT) or not os.listdir(ROOT):
        # empty/unmounted share must FAIL loudly, not pass vacuously
        print(f"ERROR: {ROOT} missing or empty (mount down?)")
        return 1
    seen = {}
    dupes = []
    n = 0
    for artist in sorted(os.listdir(ROOT)):
        apath = os.path.join(ROOT, artist)
        if artist in SKIP or artist.startswith(".") or not os.path.isdir(apath):
            continue
        for album in sorted(os.listdir(apath)):
            if album in SKIP or album.startswith(".") or \
                    not os.path.isdir(os.path.join(apath, album)):
                continue
            n += 1
            key = (norm(artist), norm(album))
            if key in seen:
                dupes.append(f"{artist}: '{seen[key]}' <-> '{album}'")
            else:
                seen[key] = album
    if dupes:
        print(f"DUPLICATE ALBUM FOLDERS ({len(dupes)}):")
        for d in dupes:
            print("  " + d)
        return 1
    print(f"DUPES_OK albums={n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
