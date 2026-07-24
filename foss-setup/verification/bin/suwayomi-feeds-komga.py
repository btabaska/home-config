#!/usr/bin/env python3
"""read-18 consumer probe: prove the MANGA ACQUISITION CHAIN is intact end to end, not
just that the Suwayomi container is up. Exercises the three links the household actually
depends on:

  1. Suwayomi (rig :4567) answers its GraphQL API           — the acquisition server is alive
  2. the rig's NAS output mount /mnt/nas-manga is WRITABLE   — where grabbed CBZ must land
     (the task pitfall: if this CIFS mount is down, downloads have nowhere to go while
      Suwayomi + Komga both still look green). Probed over `ssh rig` with a touch/rm.
  3. Komga's Manga library is available AND indexes >=1      — the chain reached the reader
     series (a manga that arrived via Suwayomi -> NAS -> Komga)

A green "container up" or even a 200 from Suwayomi tells you nothing about whether a
subscribed manga can actually flow to Komga; this walks the real path.

Emits one line:  SUWAYOMI_OK suwayomi=<ver> mount=rw komga_manga_series=<n>
             or  SUWAYOMI_FAIL <reason>
Exit 0 only on SUWAYOMI_OK.

Config from the environment (Komga creds are the same ones komga-serves.py uses):
  SUWAYOMI_URL  base            (default http://192.168.10.12:4567)
  KOMGA_URL     Komga base      (default http://192.168.10.4:25600)
  KOMGA_USER    admin email     (vault komga.admin_email)
  KOMGA_PASS    admin passwd    (vault komga.admin_password)
"""
import base64, json, os, sys, subprocess, urllib.request, urllib.error

SUW = os.environ.get("SUWAYOMI_URL", "http://192.168.10.12:4567").rstrip("/")
KOMGA = os.environ.get("KOMGA_URL", "http://192.168.10.4:25600").rstrip("/")
KUSER = os.environ.get("KOMGA_USER", "")
KPASS = os.environ.get("KOMGA_PASS", "")


def fail(msg):
    print("SUWAYOMI_FAIL %s" % msg)
    sys.exit(1)


def komga(path, timeout=15):
    auth = base64.b64encode(("%s:%s" % (KUSER, KPASS)).encode()).decode()
    r = urllib.request.Request(KOMGA + path, headers={"Authorization": "Basic " + auth})
    return json.load(urllib.request.urlopen(r, timeout=timeout))


def main():
    # 1. Suwayomi acquisition server answers GraphQL
    try:
        body = json.dumps({"query": "{aboutServer{version}}"}).encode()
        req = urllib.request.Request(SUW + "/api/graphql", data=body,
                                     headers={"content-type": "application/json"})
        ver = json.load(urllib.request.urlopen(req, timeout=10))["data"]["aboutServer"]["version"]
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, KeyError) as e:
        fail("suwayomi-api-unreachable %s" % e)

    # 2. rig NAS output mount is a live mountpoint AND writable (the transport pitfall)
    probe = ".verify-suwayomi-mount"
    remote = ("mountpoint -q /mnt/nas-manga "
              "&& touch /mnt/nas-manga/%s && rm -f /mnt/nas-manga/%s "
              "&& echo MOUNT_RW || echo MOUNT_BAD") % (probe, probe)
    try:
        out = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "rig", remote],
            capture_output=True, text=True, timeout=25).stdout.strip()
    except (subprocess.SubprocessError, OSError) as e:
        fail("rig-ssh %s" % e)
    if "MOUNT_RW" not in out:
        fail("nas-mount /mnt/nas-manga not writable from rig (%s)" % (out or "no-output"))

    # 3. Komga Manga library available AND has an indexed series (chain reached the reader)
    if not KUSER or not KPASS:
        fail("komga-credentials-missing")
    try:
        libs = komga("/api/v1/libraries")
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as e:
        fail("komga-libraries-unreachable %s" % e)
    manga = next((l for l in libs if l.get("name") == "Manga"), None)
    if manga is None:
        fail("komga-manga-library-missing")
    if manga.get("unavailable"):
        fail("komga-manga-library-unavailable (NAS folder gone?)")
    try:
        series = komga("/api/v1/series?library_id=%s&size=1" % manga["id"])
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as e:
        fail("komga-series-query-failed %s" % e)
    n = series.get("totalElements", 0)
    if n < 1:
        fail("komga-manga-empty series=0 (nothing has flowed Suwayomi->Komga)")

    print("SUWAYOMI_OK suwayomi=%s mount=rw komga_manga_series=%d" % (ver, n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
