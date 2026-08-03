#!/usr/bin/env python3
"""catalog-vhost-parity.py (fix-68 / SM49) — class check for catalog-vs-live drift.

The service catalog (configs/docker-stack/service-catalog.yaml) is the home-surface
source of truth, but on 2026-08-02 it lagged the live fleet: 6 user-facing services
(bookshelf, shelfmark, whisparr, syncthing, bgutil-pot, bug-triage-evidence) had live
Caddy vhosts / coverage entries with no catalog row, while retired readarr kept a
live-looking row whose vhost was gone (dead URL). Homepage tiles + coverage manifests
were current, so the catalog was the single lagging artifact — and gen-wiki-services
takes URL+category from it, so a missing row yields a wrong/Uncategorized wiki service
page and a stale row yields a dead wiki link.

This proves parity between the LIVE Caddy edge and the catalog, BOTH directions:
  VHOST-NOT-IN-CATALOG : a live <name>.<domain> vhost with no catalog row/url
  CATALOG-URL-DEAD     : a catalog url whose vhost no longer exists, and the row
                         is NOT annotated DECOMMISSIONED (the readarr class)

Runs on mini against the live Caddyfile + the fetched origin/main clone's catalog.

Usage: catalog-vhost-parity.py <caddyfile> <service-catalog.yaml>
Exit 0 + CATALOG-VHOST-PARITY-OK, or exit 1 with one line per violation, exit 2 tooling.
"""
import re
import sys

try:
    import yaml
except ImportError:
    print("catalog-vhost-parity: PyYAML missing", file=sys.stderr)
    sys.exit(2)

# Vhosts that intentionally have NO catalog row: internal forms / static guides /
# host aliases of an already-cataloged service (sunshine is the Apollo alias block).
ALLOW_VHOSTS = {"bug", "n8n", "retro-guide", "sunshine"}
# Suffixes marking a SECOND vhost of an already-cataloged service
# (booklogr-api -> booklogr, syncthing-rig -> syncthing).
VARIANT_SUFFIXES = ("-api", "-rig", "-nas")


def main():
    if len(sys.argv) != 3:
        print("usage: catalog-vhost-parity.py <caddyfile> <catalog.yaml>", file=sys.stderr)
        sys.exit(2)
    caddyfile, catalog = sys.argv[1], sys.argv[2]
    try:
        text = open(caddyfile).read()
        svcs = yaml.safe_load(open(catalog))["services"]
    except Exception as e:  # noqa: BLE001
        print(f"catalog-vhost-parity: cannot read inputs: {e}", file=sys.stderr)
        sys.exit(2)

    # Every '<sub>.{$DOMAIN}' or '<sub>.tabaska.us' that opens a site block,
    # including comma-separated multi-host blocks (apollo.{$DOMAIN}, sunshine...).
    vhosts = set(re.findall(
        r'(?m)(?:^|,\s*)([a-z0-9][a-z0-9-]*)\.(?:\{\$DOMAIN\}|tabaska\.us)', text))
    if not vhosts:
        print("catalog-vhost-parity: no vhosts parsed from Caddyfile (bad path?)",
              file=sys.stderr)
        sys.exit(2)

    names = {s["name"] for s in svcs}
    urlsub, dec = {}, set()
    for s in svcs:
        u = s.get("url")
        if u:
            m = re.match(r'https?://([a-z0-9-]+)\.', u)
            if m:
                urlsub[m.group(1)] = s["name"]
        if "DECOMMISSION" in (s.get("notes") or "").upper():
            dec.add(s["name"])

    def covered(v):
        if v in ALLOW_VHOSTS or v in urlsub or v in names:
            return True
        return any(v.endswith(suf) and v[:-len(suf)] in names for suf in VARIANT_SUFFIXES)

    missing = sorted(v for v in vhosts if not covered(v))
    dead = sorted(sub for sub, nm in urlsub.items()
                  if sub not in vhosts and nm not in dec)

    errs = []
    if missing:
        errs.append(f"VHOST-NOT-IN-CATALOG: {missing} "
                    "(live Caddy vhost, no catalog row/url — add it)")
    if dead:
        errs.append(f"CATALOG-URL-DEAD: {dead} "
                    "(catalog url has no live vhost — retire the row or annotate DECOMMISSIONED)")
    if errs:
        print(" | ".join(errs))
        sys.exit(1)
    print(f"CATALOG-VHOST-PARITY-OK ({len(vhosts)} live vhosts, {len(names)} catalog rows)")


if __name__ == "__main__":
    main()
