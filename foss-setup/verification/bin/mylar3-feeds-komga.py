#!/usr/bin/env python3
"""read-24 consumer probe: prove the WESTERN-COMICS ACQUISITION CHAIN is intact end to
end, not just that the Mylar3 container is up. Exercises the three links the household
actually depends on:

  1. Mylar3 (NAS :8090) answers its API (getVersion, success=true)  — the *arr grabber is alive
  2. at least one CBZ exists under /volume1/comics/Comics             — a comic actually landed
     on disk where Komga scans (probed via `ssh nas find` from the mini runner)
  3. Komga's Comics library is available AND indexes >= baseline      — the chain reached the
     series (a comic that arrived Mylar3 -> GetComics DDL -> /comics/Comics -> Komga is readable)

A green "container up" or even a 200 from Mylar3 tells you nothing about whether a grabbed
comic can actually flow to Komga; this walks the real path (mirrors suwayomi-feeds-komga.py
for the manga side). Best-effort acquisition => the check is registered `warn`, and if the
Comics library is legitimately empty the reason names that plainly rather than crashing.

Emits one line:  MYLAR3_OK mylar3=<ver> cbz=<n> komga_comics_series=<n>
             or  MYLAR3_FAIL <reason>
Exit 0 only on MYLAR3_OK.

Config from the environment (Komga creds are the same ones komga-serves.py uses):
  MYLAR3_URL       base            (default http://192.168.10.4:8090)
  MYLAR3_API_KEY   Mylar3 API key  (vault mylar3.api_key — in /etc/verification/env)
  MYLAR3_COMICS_DIR NAS comics dir (default /volume1/comics/Comics)
  MYLAR3_KOMGA_MIN baseline series (default 1 — the read-22 grab must stay readable)
  KOMGA_URL        Komga base      (default http://192.168.10.4:25600)
  KOMGA_USER       admin email     (vault komga.admin_email)
  KOMGA_PASS       admin passwd    (vault komga.admin_password)
"""
import base64, json, os, sys, subprocess, urllib.parse, urllib.request, urllib.error

MYLAR = os.environ.get("MYLAR3_URL", "http://192.168.10.4:8090").rstrip("/")
MKEY = os.environ.get("MYLAR3_API_KEY", "")
COMICS_DIR = os.environ.get("MYLAR3_COMICS_DIR", "/volume1/comics/Comics")
KOMGA_MIN = int(os.environ.get("MYLAR3_KOMGA_MIN", "1"))
KOMGA = os.environ.get("KOMGA_URL", "http://192.168.10.4:25600").rstrip("/")
KUSER = os.environ.get("KOMGA_USER", "")
KPASS = os.environ.get("KOMGA_PASS", "")


def fail(msg):
    print("MYLAR3_FAIL %s" % msg)
    sys.exit(1)


def komga(path, timeout=15):
    auth = base64.b64encode(("%s:%s" % (KUSER, KPASS)).encode()).decode()
    r = urllib.request.Request(KOMGA + path, headers={"Authorization": "Basic " + auth})
    return json.load(urllib.request.urlopen(r, timeout=timeout))


def main():
    # 1. Mylar3 grabber answers its API (key never hits argv/ps — it's in the query string
    #    of a urllib call from this process, not a shelled-out curl).
    if not MKEY:
        fail("mylar3-api-key-missing (set MYLAR3_API_KEY in /etc/verification/env)")
    try:
        q = urllib.parse.urlencode({"apikey": MKEY, "cmd": "getVersion"})
        data = json.load(urllib.request.urlopen("%s/api?%s" % (MYLAR, q), timeout=15))
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as e:
        fail("mylar3-api-unreachable %s" % e)
    if not data.get("success"):
        fail("mylar3-api-not-success (%s)" % json.dumps(data)[:120])
    ver = (data.get("data") or {}).get("current_version") or "unknown"
    ver = ver[:12]

    # 2. at least one CBZ has landed on disk where Komga scans (probed via ssh nas — the
    #    runner is on the mini; mini->nas ssh works since fix-21). A live-but-empty comics
    #    tree means nothing has flowed even if both servers look green.
    remote = "find '%s' -type f -name '*.cbz' 2>/dev/null | head -50 | wc -l" % (
        COMICS_DIR.replace("'", "'\\''"))
    try:
        out = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "nas", remote],
            capture_output=True, text=True, timeout=30)
    except (subprocess.SubprocessError, OSError) as e:
        fail("nas-ssh %s" % e)
    try:
        cbz = int((out.stdout or "0").strip().splitlines()[-1])
    except (ValueError, IndexError):
        fail("cbz-count-unparseable (%s)" % ((out.stdout or "")[:80] or "no-output"))
    if cbz < 1:
        fail("no-cbz-under %s (nothing has flowed Mylar3->disk)" % COMICS_DIR)

    # 3. Komga Comics library available AND has >= baseline indexed series (chain reached
    #    the reader — the read-22 grab is really readable).
    if not KUSER or not KPASS:
        fail("komga-credentials-missing")
    try:
        libs = komga("/api/v1/libraries")
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as e:
        fail("komga-libraries-unreachable %s" % e)
    comics = next((l for l in libs if l.get("name") == "Comics"), None)
    if comics is None:
        fail("komga-comics-library-missing")
    if comics.get("unavailable"):
        fail("komga-comics-library-unavailable (NAS folder gone?)")
    try:
        series = komga("/api/v1/series?library_id=%s&size=1" % comics["id"])
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as e:
        fail("komga-series-query-failed %s" % e)
    n = series.get("totalElements", 0)
    if n < KOMGA_MIN:
        fail("komga-comics-below-baseline series=%d < %d (Mylar3->Komga chain broken)"
             % (n, KOMGA_MIN))

    print("MYLAR3_OK mylar3=%s cbz=%d komga_comics_series=%d" % (ver, cbz, n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
