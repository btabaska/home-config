# `catalog-vhost-parity.py`

> catalog-vhost-parity.py (fix-68 / SM49) — class check for catalog-vs-live drift.

**Path:** `foss-setup/scripts/verification/catalog-vhost-parity.py` · **Category:** [verification](index.md) · **Type:** Python

## Synopsis

```
catalog-vhost-parity.py <caddyfile> <service-catalog.yaml>
```

## What it does

```text
catalog-vhost-parity.py (fix-68 / SM49) — class check for catalog-vs-live drift.

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
```

## Environment / variables referenced

`DOMAIN`

## See also

- [`deploy.sh`](deploy-sh.md)
- [`reopen-report.py`](reopen-report-py.md)
- [`repo-secret-scan.py`](repo-secret-scan-py.md)
- [`stack-mirror-check.sh`](stack-mirror-check-sh.md)
- [`tracker-count-check.py`](tracker-count-check-py.md)
- [`tracker-integrity.py`](tracker-integrity-py.md)
- [`unit-drift-check.sh`](unit-drift-check-sh.md)
- [verification scripts](index.md) · [All scripts](../index.md)
