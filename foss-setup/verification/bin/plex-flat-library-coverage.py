#!/usr/bin/env python3
"""
Acceptance check: a FLAT personal-media Plex library (one media file == one Plex
item, e.g. Pinchflat YouTube archives) actually SHOWS the media that exists on
disk.

Why this exists (2026-07-13): Pinchflat was "Up" (container-healthy) and had
downloaded 1363 real videos to the NAS `youtube` share, yet the Plex "YouTube"
library showed 0 items. Root cause: the `youtube` shared folder was missing the
`user:PlexMediaServer` ACL entry that every working Plex library folder has, so
the Plex service account could not traverse/read it. Every liveness/health check
stayed green throughout. This probes the OUTCOME the user experiences (is the
archived media visible in Plex) rather than the health of the boxes around it.

Catches the whole class: missing/failed scan, wrong path, permission/ACL loss,
deleted or repointed library — anything that makes archived media invisible.

Only valid for FLAT 1:1 libraries (personal-media / agent=none, one file == one
item). Do NOT use for movie/TV libraries where item count != file count.

Env: PLEX_URL (e.g. http://192.168.10.4:32400), PLEX_TOKEN.
Usage:
  plex-flat-library-coverage.py --disk /mnt/nas-youtube/pinchflat --section 4 [--min-ratio 0.8]
Prints exactly one line; exits 0 only on COVERAGE_OK:
  COVERAGE_OK disk=1363 plex=1363 ratio=1.00
  COVERAGE_BAD disk=1363 plex=0 ratio=0.00 need>=0.8
  MOUNT_DOWN / PLEX_UNREACHABLE / CONFIG_ERR ...
"""
import argparse
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET

VIDEO_EXT = {".mp4", ".mkv", ".webm", ".avi", ".mov", ".m4v", ".ts", ".flv"}
SKIP_DIRS = ("@eaDir", "#recycle")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--disk", required=True, help="root dir holding the media on disk")
    ap.add_argument("--section", required=True, help="Plex library section id")
    ap.add_argument("--min-ratio", type=float, default=0.8,
                    help="plex_items must be >= disk_media * this (default 0.8)")
    a = ap.parse_args()

    # 1) The mount/dir must be listable. A DOWN mount must FAIL loudly, never
    #    vacuously pass (0 files on disk + 0 in Plex would otherwise look 'OK').
    if not os.path.isdir(a.disk):
        print(f"MOUNT_DOWN disk={a.disk} not-a-directory")
        return 1
    try:
        os.listdir(a.disk)
    except OSError as e:
        print(f"MOUNT_DOWN disk={a.disk} err={e.__class__.__name__}")
        return 1

    # 2) Count media files on disk.
    disk = 0
    for root, dirs, files in os.walk(a.disk):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if os.path.splitext(f)[1].lower() in VIDEO_EXT:
                disk += 1

    # 3) Ask Plex how many items the library reports.
    url = os.environ.get("PLEX_URL")
    tok = os.environ.get("PLEX_TOKEN")
    if not url or not tok:
        print("CONFIG_ERR PLEX_URL/PLEX_TOKEN unset")
        return 1
    try:
        with urllib.request.urlopen(
            f"{url}/library/sections/{a.section}/all?X-Plex-Token={tok}", timeout=20
        ) as r:
            plex = int(ET.fromstring(r.read()).get("size", "0"))
    except Exception as e:
        print(f"PLEX_UNREACHABLE section={a.section} err={type(e).__name__}")
        return 1

    # 4) Verdict.
    if disk == 0:
        print(f"COVERAGE_OK disk=0 plex={plex} nothing-archived-yet")
        return 0
    ratio = plex / disk
    if plex >= disk * a.min_ratio:
        print(f"COVERAGE_OK disk={disk} plex={plex} ratio={ratio:.2f}")
        return 0
    print(f"COVERAGE_BAD disk={disk} plex={plex} ratio={ratio:.2f} need>={a.min_ratio}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
