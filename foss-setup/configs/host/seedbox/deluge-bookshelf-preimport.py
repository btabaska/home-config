#!/usr/bin/env python3
# Verification probe (fix-57 SH11 class): a books grab that finished 100% but is
# STILL in the PRE-import 'bookshelf' label >24h has never been imported. The
# Bookshelf relabel-imported job only moves VERIFIED-imported torrents to
# 'bookshelf-imported' (it asks Bookshelf history whether the grab imported), so
# anything left in the plain 'bookshelf' label this long did NOT reach the
# library — the consumer never got the book.
#
# 'Adrift - K. T. Konkoly.epub' sat here ~306h: an orphaned readarr-era grab whose
# indie author has no Hardcover metadata, so the Hardcover-backed Bookshelf could
# never create a record for it. It was therefore invisible to
# books-pipeline-lost-imports (which only compares Bookshelf-records-WITH-files
# vs Calibre — a book with no Bookshelf record vanishes from both sides) and only
# noise in the generic all-labels deluge-preimport-stuck (48h). This probe is
# books-only + 24h so a lost book surfaces within a day and is not drowned out by
# tv/movie migration churn — it would have caught Adrift on day one.
#
# Deploy: scp configs/host/seedbox/deluge-bookshelf-preimport.py seedbox:scripts/
# Run:    ~/venvs/deluge/bin/python ~/scripts/deluge-bookshelf-preimport.py
# Output: BOOKS_PREIMPORT_OK checked=N
#      |  BOOKS_PREIMPORT_STUCK n: name (age h); ...   (exit 1)
import os, time
from deluge.ui.client import client
from twisted.internet import reactor, defer

PRE_IMPORT_LABEL = "bookshelf"          # NOT 'bookshelf-imported' (that = done)
STUCK_AFTER = 24 * 3600
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
            if (v.get("label") or "") != PRE_IMPORT_LABEL:
                continue
            if (v.get("progress") or 0) < 99.9:
                continue
            checked += 1
            done_at = v.get("completed_time") or v.get("time_added") or now
            if now - done_at > STUCK_AFTER:
                age_h = (now - done_at) / 3600.0
                stuck.append(f"{(v.get('name') or '?')[:55]} ({age_h:.0f}h)")
        if stuck:
            print(f"BOOKS_PREIMPORT_STUCK {len(stuck)}: " + "; ".join(stuck[:5]))
            EXIT[0] = 1
        else:
            print(f"BOOKS_PREIMPORT_OK checked={checked}")
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
