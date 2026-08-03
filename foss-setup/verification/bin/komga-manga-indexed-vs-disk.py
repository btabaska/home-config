#!/usr/bin/env python3
"""fix-58 SH12/SM34 consumer-truth check: Komga's Manga library must actually INDEX the
CBZ that Suwayomi has written to /volume1/manga — not merely "have >=1 series".

The 2026-08-02 outage: Komga's LibraryScanScheduler kept firing the DELETED pre-read-18
library id every 6h ("Library does not exist") and NEVER scanned the real Manga library,
so 279 downloaded chapters sat on disk invisible to readers for 6 days while both servers
looked green and suwayomi-feeds-komga passed on series>=1 (a single stale book).

This is the CONSUMER-END lag catch that the shallow checks missed: whenever the scheduler
stops scanning the real library (a re-home leaving stale scheduler state, a wrong id, a
scan wedge), new CBZ pile up on disk while Komga's indexed count stays flat — so the gap
between on-disk CBZ and Komga-indexed books GROWS. We fail when Komga is more than TOL
books behind disk (TOL absorbs the normal window between a Suwayomi download and the next
scan), or when the Manga library indexes <2 series.

Emits: KOMGA_MANGA_OK disk_cbz=<n> indexed=<n> series=<n> lag=<n>
   or  KOMGA_MANGA_FAIL <reason>      (exit 0 only on KOMGA_MANGA_OK)

Env: KOMGA_URL (default http://192.168.10.4:25600), KOMGA_USER, KOMGA_PASS.
Reads the on-disk CBZ count over `ssh nas` as the service user (btabaska, no sudo needed —
/volume1/manga is btabaska-owned). MANGA_DISK_TOL overrides the tolerance (default 10).
"""
import base64, json, os, sys, subprocess, urllib.request, urllib.error

KOMGA = os.environ.get("KOMGA_URL", "http://192.168.10.4:25600").rstrip("/")
KUSER = os.environ.get("KOMGA_USER", "")
KPASS = os.environ.get("KOMGA_PASS", "")
TOL = int(os.environ.get("MANGA_DISK_TOL", "10"))
MANGA_ROOT = "/volume1/manga"


def fail(msg):
    print("KOMGA_MANGA_FAIL %s" % msg)
    sys.exit(1)


def komga(path, timeout=25):
    if not KUSER or not KPASS:
        fail("komga-credentials-missing")
    auth = base64.b64encode(("%s:%s" % (KUSER, KPASS)).encode()).decode()
    r = urllib.request.Request(KOMGA + path, headers={"Authorization": "Basic " + auth})
    return json.load(urllib.request.urlopen(r, timeout=timeout))


def main():
    # on-disk CBZ under the Manga root (ground truth of what Suwayomi delivered)
    try:
        out = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "nas",
             "find %s -name '*.cbz' 2>/dev/null | wc -l" % MANGA_ROOT],
            capture_output=True, text=True, timeout=40)
        disk = int((out.stdout or "").strip() or "-1")
    except (subprocess.SubprocessError, OSError, ValueError) as e:
        fail("nas-disk-count-failed %s" % e)
    if disk < 0:
        fail("nas-disk-count-unreadable")

    # Komga's Manga library, indexed book + series counts
    try:
        libs = komga("/api/v1/libraries")
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as e:
        fail("komga-libraries-unreachable %s" % e)
    manga = next((l for l in libs if l.get("name") == "Manga"), None)
    if manga is None:
        fail("komga-manga-library-missing")
    if manga.get("unavailable"):
        fail("komga-manga-library-unavailable")
    lid = manga["id"]
    try:
        indexed = komga("/api/v1/books?library_id=%s&size=1" % lid).get("totalElements", 0)
        series = komga("/api/v1/series?library_id=%s&size=1" % lid).get("totalElements", 0)
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as e:
        fail("komga-count-query-failed %s" % e)

    lag = disk - indexed
    if series < 2:
        fail("manga-series=%d (<2: periodic scan dead or library near-empty) disk_cbz=%d indexed=%d"
             % (series, disk, indexed))
    if lag > TOL:
        fail("manga-index-lag=%d disk_cbz=%d indexed=%d (Komga is not scanning the real Manga "
             "library — stale scheduler id / re-home needs a Komga restart)" % (lag, disk, indexed))

    print("KOMGA_MANGA_OK disk_cbz=%d indexed=%d series=%d lag=%d" % (disk, indexed, series, lag))
    return 0


if __name__ == "__main__":
    sys.exit(main())
