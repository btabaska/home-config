#!/usr/bin/env python3
"""fix-50: de-flapped consumer probe for Bitmagnet's Torznab indexer via Prowlarr.

Bitmagnet is DEMOTED to interactive-only (fix-50) — its Torznab endpoint now serves
ONLY manual/interactive searches. A real DHT keyword search runs a big Postgres scan
that floats ~8-25s and, under NAS I/O load (arr re-grabs + the fix-55 I/O storm), can
exceed any sane budget. A demoted, manual-only fallback whose search is merely SLOW
must NOT page — a warn that flaps on transient NAS latency is exactly the alert-fatigue
the sweep calls out (SM23/SM38). Only a fallback that is truly DEAD or unregistered
should warn.

TRUE-STATE ladder (never flaps on transient search latency):
  OK    — the scoped Prowlarr search returned real hits (the whole chain works).
  SLOW  — the search returned no hits / timed out BUT Bitmagnet's Torznab endpoint
          answers a `t=caps` query. caps is a STATIC capabilities response (no DB
          scan), so it stays sub-second even while the search DB is under load =>
          the endpoint is ALIVE, just load-degraded. Acceptable for a manual-only
          fallback => PASS. (The crawler's freshness is separately guarded by
          bitmagnet-dht-ingesting.)
  FAIL  — the indexer is not registered in Prowlarr, Prowlarr is unreachable, OR the
          Torznab endpoint itself is unreachable (caps also fails) => genuinely dead.

Self-sources the Prowlarr API key from the NAS config.xml (no new secret in the env).
Prints one line; expect: ^BITMAGNET_PROWLARR_(OK|SLOW)
"""
import json
import re
import subprocess
import sys
import urllib.request

PROWLARR = "http://192.168.10.4:9696"
BITMAGNET_CAPS = "http://192.168.10.4:3333/torznab/api?t=caps"
CAPS_TIMEOUT = 10       # static response — sub-second even under DB load
INDEXER_TIMEOUT = 15
SEARCH_TIMEOUT = 30     # inner-curl timebox: one scoped search, no unbounded hang


def _get(url, key=None, timeout=30):
    req = urllib.request.Request(url, headers={"X-Api-Key": key} if key else {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _prowlarr_key():
    raw = subprocess.check_output(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "nas",
         "grep -oE '<ApiKey>[a-f0-9]+</ApiKey>' /volume1/docker/prowlarr/config/config.xml"],
        timeout=20).decode()
    return re.sub(r"<[^>]*>", "", raw).strip()


def _caps_alive():
    try:
        return len(_get(BITMAGNET_CAPS, timeout=CAPS_TIMEOUT)) > 0
    except Exception:
        return False


def main():
    try:
        key = _prowlarr_key()
    except Exception as e:
        print(f"BITMAGNET_PROWLARR_FAIL no_prowlarr_key ({type(e).__name__})")
        sys.exit(1)
    if not key:
        print("BITMAGNET_PROWLARR_FAIL no_prowlarr_key")
        sys.exit(1)

    try:
        idx = json.loads(_get(f"{PROWLARR}/api/v1/indexer", key, timeout=INDEXER_TIMEOUT))
    except Exception as e:
        print(f"BITMAGNET_PROWLARR_FAIL prowlarr_unreachable ({type(e).__name__})")
        sys.exit(1)
    iid = next((i["id"] for i in idx if i.get("name") == "Bitmagnet (DHT)"), None)
    if iid is None:
        print("BITMAGNET_NOT_REGISTERED")
        sys.exit(1)

    # one scoped search; slow-but-alive is acceptable for a manual-only fallback
    try:
        res = json.loads(_get(
            f"{PROWLARR}/api/v1/search?query=1080p&indexerIds={iid}&limit=5",
            key, timeout=SEARCH_TIMEOUT))
        n = len(res)
    except Exception:
        n = None  # timed out / errored under load

    if n and n > 0:
        print(f"BITMAGNET_PROWLARR_OK indexer={iid} hits={n}")
        return

    why = "search=timeout" if n is None else "hits=0"
    if _caps_alive():
        print(f"BITMAGNET_PROWLARR_SLOW indexer={iid} {why} endpoint=alive "
              "(manual-only fallback, load-degraded — not paging)")
        return
    print(f"BITMAGNET_PROWLARR_FAIL indexer={iid} {why} endpoint=DEAD")
    sys.exit(1)


if __name__ == "__main__":
    main()
