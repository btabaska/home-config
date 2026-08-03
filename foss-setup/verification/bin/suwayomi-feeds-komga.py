#!/usr/bin/env python3
"""read-18 consumer probe: prove the MANGA ACQUISITION CHAIN is intact end to end, not
just that the Suwayomi container is up. Exercises the links the household depends on:

  1. Suwayomi (rig :4567) answers its GraphQL API           — the acquisition server is alive
  2. the rig's NAS output mount /mnt/nas-manga is WRITABLE   — where grabbed CBZ must land
     (the task pitfall: if this CIFS mount is down, downloads have nowhere to go while
      Suwayomi + Komga both still look green). Probed over `ssh rig` with a touch/rm.
  3. the CONTAINER's downloads view is the REAL mount, not an empty pre-mount underlay
     (fix-58 SH13: the 08-01 boot started suwayomi before mnt-nas-manga.mount, so its
      rprivate bind captured the empty dir → 279 downloaded chapters + every thumbnail
      invisible while the HOST mount looked healthy). Probed `docker exec suwayomi ls`.
  4. a real in-library manga THUMBNAIL serves HTTP 200       — fix-58 SM21/SL16: when the
     container can't see the thumbnails dir it 500s on `<id>.tmp (No such file)`.
  5. Komga's Manga library is available AND indexes >=2      — the chain reached the reader
     series (>=2, not >=1: a single stale pre-read-18 book satisfied >=1 forever while the
     periodic scan was silently dead — fix-58 SH12/SM34).

A green "container up" or even a 200 from Suwayomi tells you nothing about whether a
subscribed manga can actually flow to Komga; this walks the real path.

Emits: SUWAYOMI_OK suwayomi=<ver> mount=rw cview=ok thumb=200 komga_manga_series=<n>
   or  SUWAYOMI_FAIL <reason>          (exit 0 only on SUWAYOMI_OK)

Config from the environment (Komga creds are the same ones komga-serves.py uses):
  SUWAYOMI_URL  base            (default http://192.168.10.12:4567)
  KOMGA_URL     Komga base      (default http://192.168.10.4:25600)
  KOMGA_USER    admin email     (vault komga.admin_email / homepage_widgets.komga_user)
  KOMGA_PASS    admin passwd    (vault komga.admin_password / homepage_widgets.komga_pass)
"""
import base64, json, os, sys, subprocess, urllib.request, urllib.error

SUW = os.environ.get("SUWAYOMI_URL", "http://192.168.10.12:4567").rstrip("/")
KOMGA = os.environ.get("KOMGA_URL", "http://192.168.10.4:25600").rstrip("/")
KUSER = os.environ.get("KOMGA_USER", "")
KPASS = os.environ.get("KOMGA_PASS", "")
CONTAINER_DL = "/home/suwayomi/.local/share/Tachidesk/downloads"


def fail(msg):
    print("SUWAYOMI_FAIL %s" % msg)
    sys.exit(1)


def komga(path, timeout=15):
    auth = base64.b64encode(("%s:%s" % (KUSER, KPASS)).encode()).decode()
    r = urllib.request.Request(KOMGA + path, headers={"Authorization": "Basic " + auth})
    return json.load(urllib.request.urlopen(r, timeout=timeout))


def graphql(query, timeout=10):
    body = json.dumps({"query": query}).encode()
    req = urllib.request.Request(SUW + "/api/graphql", data=body,
                                 headers={"content-type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=timeout))["data"]


def ssh_rig(remote, timeout=25):
    return subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "rig", remote],
        capture_output=True, text=True, timeout=timeout).stdout.strip()


def main():
    # 1. Suwayomi acquisition server answers GraphQL
    try:
        ver = graphql("{aboutServer{version}}")["aboutServer"]["version"]
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, KeyError) as e:
        fail("suwayomi-api-unreachable %s" % e)

    # 2+3. rig NAS output mount live+writable (host) AND the CONTAINER sees the real mount
    #      (not the empty pre-mount underlay). One ssh does both.
    probe = ".verify-suwayomi-mount"
    remote = ("mountpoint -q /mnt/nas-manga "
              "&& touch /mnt/nas-manga/%s && rm -f /mnt/nas-manga/%s && echo MOUNT_RW || echo MOUNT_BAD; "
              "docker exec suwayomi ls %s/ 2>/dev/null | tr '\\n' ',' ; echo") % (probe, probe, CONTAINER_DL)
    try:
        out = ssh_rig(remote)
    except (subprocess.SubprocessError, OSError) as e:
        fail("rig-ssh %s" % e)
    lines = out.splitlines()
    if not lines or "MOUNT_RW" not in lines[0]:
        fail("nas-mount /mnt/nas-manga not writable from rig (%s)" % (out or "no-output"))
    cview = lines[1] if len(lines) > 1 else ""
    entries = {e for e in cview.split(",") if e}
    if not ({"mangas", "thumbnails"} <= entries):
        fail("container-downloads-view empty/underlay entries=%s "
             "(SH13: suwayomi started before the CIFS mount — restart it)" % (sorted(entries) or "none"))

    # 4. a real in-library manga thumbnail serves 200 (SM21/SL16 thumbnail-500 class)
    try:
        nodes = graphql("{mangas(condition:{inLibrary:true},order:{by:ID}){nodes{id}}}")["mangas"]["nodes"]
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, KeyError) as e:
        fail("suwayomi-library-query-failed %s" % e)
    thumb_code = None
    if nodes:
        mid = nodes[0]["id"]
        try:
            resp = urllib.request.urlopen(SUW + "/api/v1/manga/%s/thumbnail" % mid, timeout=15)
            thumb_code = resp.status
            _ = resp.read(512)
        except urllib.error.HTTPError as e:
            thumb_code = e.code
        except urllib.error.URLError as e:
            fail("suwayomi-thumbnail-unreachable %s" % e)
        if thumb_code != 200:
            fail("suwayomi-thumbnail manga=%s code=%s (SM21/SL16 thumbnail cache broken)" % (mid, thumb_code))

    # 5. Komga Manga library available AND indexes >=2 series (chain reached the reader;
    #    >=2 so a single stale pre-read-18 book can't satisfy it forever — SH12/SM34)
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
    if n < 2:
        fail("komga-manga-series=%d (<2: scan dead or library near-empty — SH12)" % n)

    print("SUWAYOMI_OK suwayomi=%s mount=rw cview=ok thumb=%s komga_manga_series=%d"
          % (ver, thumb_code if thumb_code is not None else "n/a", n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
