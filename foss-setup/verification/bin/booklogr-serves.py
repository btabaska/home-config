#!/usr/bin/env python3
"""BookLogr consumer-end probe (read-26).

Not liveness — walks the whole browser->API chain the way a real user's browser
does, so a broken BL_API_ENDPOINT wiring or a dead API fails LOUD even while both
containers report "up":

  1. The web SPA is served at https://booklogr.tabaska.us/ (HTTP 200, app shell).
  2. The SPA's JS bundle carries the API URL it will call from the browser
     (https://booklogr-api.tabaska.us) — catches a BL_API_ENDPOINT regression
     that would silently break every action for users.
  3. That API URL answers cross-origin: GET / returns the {"name":"booklogr-api"}
     version JSON AND an Access-Control-Allow-Origin header (so the browser's
     cross-subdomain fetch would actually succeed, not be blocked by CORS).

Prints 'BOOKLOGR_OK ...' on success, 'BOOKLOGR_FAIL ...' otherwise (exit 0 either
way — the runner matches on the ^BOOKLOGR_OK regex).
"""
import re
import sys
import urllib.request

WEB = "https://booklogr.tabaska.us"
API = "https://booklogr-api.tabaska.us"
TIMEOUT = 20


def fail(msg):
    print("BOOKLOGR_FAIL " + msg)
    sys.exit(0)


def get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    return urllib.request.urlopen(req, timeout=TIMEOUT)


try:
    # 1. SPA shell
    shell = get(WEB + "/").read().decode("utf-8", "replace")
    m = re.search(r"/assets/index-[A-Za-z0-9_-]+\.js", shell)
    if not m:
        fail("web shell served but no /assets/index-*.js bundle found")
    bundle_path = m.group(0)

    # 2. Bundle carries the API endpoint the browser will call
    bundle = get(WEB + bundle_path).read().decode("utf-8", "replace")
    if "booklogr-api.tabaska.us" not in bundle:
        fail("BL_API_ENDPOINT missing from SPA bundle (browser->API wiring broken)")

    # 3. That API URL answers cross-origin with version JSON + CORS header
    resp = get(API + "/", headers={"Origin": WEB})
    body = resp.read().decode("utf-8", "replace")
    acao = resp.headers.get("Access-Control-Allow-Origin")
    if '"name"' not in body or "booklogr-api" not in body:
        fail("API root did not return version JSON: " + body[:120])
    if not acao:
        fail("API missing Access-Control-Allow-Origin (browser calls would be CORS-blocked)")

    ver = re.search(r'"version"\s*:\s*"([^"]+)"', body)
    print("BOOKLOGR_OK web=200 bundle=%s api_version=%s cors=%s"
          % (bundle_path.rsplit("/", 1)[-1], ver.group(1) if ver else "?", acao))
except Exception as e:  # noqa: BLE001 — any failure is a real red
    fail("%s: %s" % (type(e).__name__, e))
