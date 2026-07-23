#!/usr/bin/env python3
"""read-17 consumer probe: prove Komga actually SERVES a readable comics/manga library,
not just that the JVM container is up. Authenticates with the admin username/password
(the same credentials the Homepage widget uses), asserts BOTH the Comics and Manga
libraries exist, that at least one series is indexed, that a real page streams (HTTP 200
image bytes), and that the OPDS catalog responds — a green /actuator/health tells you
nothing about whether a comic will open in a reader or over OPDS.

Emits one line:  KOMGA_OK libraries=<n> series=<n> books=<n> page=<code> opds=<code>
             or  KOMGA_FAIL <reason>
Exit 0 only on KOMGA_OK.

Credentials come from the environment (never argv, so the password can't leak into ps):
  KOMGA_URL   Komga base   (default http://192.168.10.4:25600)
  KOMGA_USER  admin email  (vault homepage_widgets.komga_user / komga.admin_email)
  KOMGA_PASS  admin passwd  (vault homepage_widgets.komga_pass / komga.admin_password)
"""
import base64, json, os, sys, urllib.request, urllib.error

BASE = os.environ.get("KOMGA_URL", "http://192.168.10.4:25600").rstrip("/")
USER = os.environ.get("KOMGA_USER", "")
PASS = os.environ.get("KOMGA_PASS", "")
# libraries we require to exist (Manga is fed by read-18 Suwayomi; may be empty but must exist)
REQUIRED_LIBS = {"Comics", "Manga"}


def _req(path, timeout=25, raw=False):
    auth = base64.b64encode(("%s:%s" % (USER, PASS)).encode()).decode()
    r = urllib.request.Request(BASE + path, headers={"Authorization": "Basic " + auth})
    resp = urllib.request.urlopen(r, timeout=timeout)
    return resp if raw else json.load(resp)


def main():
    if not USER or not PASS:
        print("KOMGA_FAIL no-credentials (set KOMGA_USER/KOMGA_PASS)"); return 1

    # 1. libraries — auth works AND both expected libraries exist
    try:
        libs = _req("/api/v1/libraries")
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as e:
        print("KOMGA_FAIL libraries-unreachable %s" % e); return 1
    names = {l.get("name") for l in libs}
    missing = REQUIRED_LIBS - names
    if missing:
        print("KOMGA_FAIL missing-libraries=%s have=%s" % (sorted(missing), sorted(names))); return 1

    # 2. series count — proves at least one library actually indexed content
    try:
        series = _req("/api/v1/series?size=1")
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as e:
        print("KOMGA_FAIL series-query-failed %s" % e); return 1
    n_series = series.get("totalElements", 0)
    if n_series < 1:
        print("KOMGA_FAIL series=0 (no indexed content; scan broken or library empty)"); return 1

    # 3. pick a book and stream page 1 — proves the reader path serves real image bytes
    try:
        books = _req("/api/v1/books?size=1")
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as e:
        print("KOMGA_FAIL books-query-failed %s" % e); return 1
    n_books = books.get("totalElements", 0)
    content = books.get("content") or []
    if not content:
        print("KOMGA_FAIL no-books (series indexed but no readable book)"); return 1
    bid = content[0].get("id")
    try:
        resp = _req("/api/v1/books/%s/pages/1" % bid, raw=True)
        page_code = resp.status
        chunk = resp.read(2048)
    except urllib.error.HTTPError as e:
        page_code, chunk = e.code, b""
    except urllib.error.URLError as e:
        print("KOMGA_FAIL page-unreachable %s" % e); return 1
    if page_code != 200 or len(chunk) == 0:
        print("KOMGA_FAIL page code=%s bytes=%d (page streaming broken)" % (page_code, len(chunk))); return 1

    # 4. OPDS catalog — the client-download surface (Mihon/Panels/KOReader) responds
    try:
        opds = _req("/opds/v1.2/catalog", raw=True)
        opds_code = opds.status
    except urllib.error.HTTPError as e:
        opds_code = e.code
    except urllib.error.URLError as e:
        print("KOMGA_FAIL opds-unreachable %s" % e); return 1
    if opds_code != 200:
        print("KOMGA_FAIL opds code=%s" % opds_code); return 1

    print("KOMGA_OK libraries=%d series=%d books=%d page=%d opds=%d"
          % (len(names), n_series, n_books, page_code, opds_code))
    return 0


if __name__ == "__main__":
    sys.exit(main())
