#!/usr/bin/env python3
"""homepage-unifi-tile — home-08 consumer-end guard for the UniFi Network tile.

The UniFi Network Homepage widget is backed by a DEDICATED local read-only UniFi
Network account (vault unifi_network.*). If that account is deleted, disabled, or
its password rotated, Homepage's `unifi` widget silently falls back to blank "-"
placeholders — no dead tile, no DNS error, so the fix-29 homepage-dead-tiles /
homepage-widget-errors guards do NOT catch it. This is the exact liveness-vs-
reality gap (mandate 1): the tile renders, but shows nothing real.

This probes the SAME server-side path the browser's widget uses: it asks Homepage
to proxy the unifi `stat/sites` call (login + site resolution + health, done by
homepage's unifi proxyHandler using the injected HOMEPAGE_VAR_UNIFI_* creds) and
requires a real UniFi site-health payload back (meta.rc == ok with a populated
health[] carrying the wan subsystem). It does NOT assert wan == "ok", so a genuine
internet outage does not flap this — only a broken credential / widget path does.

Prints  UNIFI_TILE=OK  (green) or  UNIFI_TILE=FAIL:<reason>  (fail).
"""
import json
import sys
import urllib.parse
import urllib.request

# Homepage on the mini publishes host port 3010 (container :3000). localhost:3010
# is an allowed host (HOMEPAGE_ALLOWED_HOSTS), so the default Host header is fine.
BASE = "http://localhost:3010/api/services/proxy"
PARAMS = {
    "group": "Infrastructure",
    "service": "UniFi Network",
    "endpoint": "stat/sites",  # the exact endpoint the unifi widget requests
}
URL = BASE + "?" + urllib.parse.urlencode(PARAMS, quote_via=urllib.parse.quote)


def main():
    try:
        with urllib.request.urlopen(URL, timeout=12) as r:
            body = r.read()
    except Exception as e:  # noqa: BLE001 — any transport failure is a real fail
        print("UNIFI_TILE=FAIL:request_%s" % type(e).__name__)
        return 1
    try:
        d = json.loads(body)
    except ValueError:
        print("UNIFI_TILE=FAIL:non_json_response")
        return 1
    if not isinstance(d, dict) or "error" in d:
        # homepage proxy returns {"error": {...}} when the upstream/auth fails
        print("UNIFI_TILE=FAIL:proxy_error")
        return 1
    if d.get("meta", {}).get("rc") != "ok":
        print("UNIFI_TILE=FAIL:rc_%s" % d.get("meta", {}).get("rc"))
        return 1
    data = d.get("data") or []
    health = (data[0].get("health") if data and isinstance(data[0], dict) else None) or []
    subs = {h.get("subsystem") for h in health if isinstance(h, dict)}
    if "wan" not in subs:
        print("UNIFI_TILE=FAIL:no_wan_health(subs=%s)" % ",".join(sorted(s for s in subs if s)))
        return 1
    print("UNIFI_TILE=OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
