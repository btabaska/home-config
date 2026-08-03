# `seed-status-page.sh`

> publish a REAL Uptime Kuma status page (fix-63 / SL23).

**Path:** `foss-setup/scripts/uptime-kuma/seed-status-page.sh` · **Category:** [Uptime Kuma](index.md) · **Type:** Bash

## What it does

```text
 seed-status-page.sh — publish a REAL Uptime Kuma status page (fix-63 / SL23).

 Kuma's only published page was 'test' (0 groups, 0 monitors) — an empty
 placeholder, and per memory the Homepage Kuma widget cannot be added until a
 real page exists. This seeds a curated, grouped, PUBLISHED status page at
 https://uptime.tabaska.us/status/<slug> and (by default) removes the empty
 'test' page. Idempotent: re-running rebuilds the groups deterministically.

 Kuma stores ALL config in its embedded MariaDB (no config files), so this seed
 script IS the repo-codified source of truth for the status page — same pattern
 as seed-monitors.sh. Run on the mini (where the uptime-kuma container lives):
   bash seed-status-page.sh
```

## Environment / variables referenced

`CONTAINER`, `DESC`, `DROP_TEST`, `KUMA_CONTAINER`, `SLUG`, `SOCKET`, `STATUS_PAGE_SLUG`, `STATUS_PAGE_TITLE`, `TITLE`

## See also

- [`add-functional-monitors.sh`](add-functional-monitors-sh.md)
- [`bootstrap-nas-monitors.sh`](bootstrap-nas-monitors-sh.md)
- [`seed-monitors.sh`](seed-monitors-sh.md)
- [Uptime Kuma scripts](index.md) · [All scripts](../index.md)
