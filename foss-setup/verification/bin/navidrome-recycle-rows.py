#!/usr/bin/env python3
"""
navidrome-recycle-rows.py — fix-28 (M-hygiene) regression check. Runs on `mini`.

The NAS music share is mounted into Navidrome and exposes Synology's `#recycle`
bin; Navidrome had indexed 2 user-deleted tracks from `#recycle` as live, playable
library rows (visible/searchable in every Subsonic client). The guard is an empty
`.ndignore` marker at /volume1/music/#recycle/.ndignore (the 0.62 new scanner does
NOT honor ND_IGNOREDPATTERNS). This check asserts the guard holds by reading
Navidrome's own DB and requiring ZERO media_file rows whose path is under `#recycle`
— catching both a removed/ineffective marker and any future junk-dir indexing.

Fails LOUDLY if the DB is absent/unreadable (never a vacuous pass). One line:
  RECYCLE_OK   junk=0 total=N
  RECYCLE_BAD  junk=K  e.g. '#recycle/YouTube/x.mp3' ...
  RECYCLE_ERR  <reason>
"""
import os, sys, sqlite3

DB = os.environ.get("NAVIDROME_DB", "/opt/stacks/navidrome/data/navidrome.db")

def main():
    if not os.path.exists(DB):
        print(f"RECYCLE_ERR navidrome db not found at {DB}"); return 2
    try:
        c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        total = c.execute("select count(*) from media_file").fetchone()[0]
        rows = c.execute("select path from media_file where path like '#recycle%' or path like '%/#recycle/%'").fetchall()
        c.close()
    except Exception as e:
        print(f"RECYCLE_ERR reading navidrome db: {e}"); return 2
    if total == 0:
        print("RECYCLE_ERR navidrome db has 0 media_file rows (scanner broken?)"); return 2
    if rows:
        print(f"RECYCLE_BAD junk={len(rows)} total={total} :: " + " ".join(repr(r[0]) for r in rows[:10]))
        return 1
    print(f"RECYCLE_OK junk=0 total={total}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
