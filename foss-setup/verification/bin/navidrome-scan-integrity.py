#!/usr/bin/env python3
# navidrome-scan-integrity.py  (fix-49 · class-level consumer probe)
#
# The 2026-08-01 whole-library outage (SC1) was GREEN everywhere — container
# healthy, /ping 200 — while every track was greyed out. Root cause: the music
# root .ndignore held the single line "#recycle", which is a gitignore COMMENT,
# so the file was effectively EMPTY, which Navidrome treats as "skip this whole
# folder and everything below". At the library root that greys out the entire
# library. This probes the CONSUMER end for that whole class, none of which move
# liveness:
#   (1) .ndignore sanity — if a music-root .ndignore exists it MUST carry at
#       least one real (non-blank, non-comment) pattern; a comment-only/empty
#       one is the exact trap.
#   (2) library not empty and not mass-flagged missing (reads Navidrome's DB).
#   (3) the library-root folder row is present and not flagged missing.
# Emits a single line; exit 0 always (the runner keys on the ^INTEGRITY_OK regex).
import os
import subprocess
import sys

MP = os.environ.get("MUSIC_MP", "/mnt/nas/music")
NDIGNORE = os.path.join(MP, ".ndignore")
DB = "/data/navidrome.db"


def out(status):
    print(status)
    sys.exit(0)


def q(sql):
    r = subprocess.run(
        ["docker", "exec", "navidrome", "sqlite3", "-readonly", DB, sql],
        capture_output=True, text=True, timeout=30,
    )
    if r.returncode != 0:
        out("INTEGRITY_BAD db-unreachable " + (r.stderr.strip()[:120] or "?"))
    return r.stdout.strip()


# (1) .ndignore sanity
try:
    with open(NDIGNORE) as f:
        lines = f.read().splitlines()
    real = [l for l in lines if l.strip() and not l.lstrip().startswith("#")]
    if not real:
        out("INTEGRITY_BAD ndignore-comment-only-or-empty "
            "(skips whole music root) file=%s content=%r" % (NDIGNORE, lines))
except FileNotFoundError:
    pass  # absent = no skip, fine
except Exception as e:  # noqa: BLE001
    out("INTEGRITY_BAD ndignore-read-error %s" % e)

# (2) library present and not mass-flagged missing
try:
    total, missing = (int(x) for x in
                      q("select count(*)||'|'||coalesce(sum(missing),0) "
                        "from media_file;").split("|"))
except Exception as e:  # noqa: BLE001
    out("INTEGRITY_BAD db-parse-error %s" % e)

if total == 0:
    out("INTEGRITY_BAD library-empty total_songs=0")
if missing * 5 > total:  # >20% missing == mass-flag / mount-gone / .ndignore skip
    out("INTEGRITY_BAD mass-missing missing=%d/%d" % (missing, total))

# (3) library-root folder present and not flagged missing
root_missing = q("select coalesce(max(missing),9) from folder where parent_id='';")
if root_missing != "0":
    out("INTEGRITY_BAD library-root-missing flag=%s" % root_missing)

out("INTEGRITY_OK missing=%d/%d ndignore=sane root=present" % (missing, total))
