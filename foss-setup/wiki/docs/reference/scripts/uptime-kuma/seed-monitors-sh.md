# `seed-monitors.sh`

> Seed Uptime Kuma (v2.x, embedded MariaDB) with the full fleet monitor set

**Path:** `foss-setup/scripts/uptime-kuma/seed-monitors.sh` · **Category:** [Uptime Kuma](index.md) · **Type:** Bash

## What it does

```text
 Seed Uptime Kuma (v2.x, embedded MariaDB) with the full fleet monitor set
 + a default ntfy notification channel wired to every monitor.

 Run on the Mac mini (where the uptime-kuma container lives):
   NTFY_TOKEN=tk_... bash seed-monitors.sh

 - Idempotent: monitors/notification matched by name; links deduped.
 - Direct host:port probes (no Caddy/DNS dependency) + 3 full-chain https
   vhost checks + DNS + ping monitors.
 - v2 loads monitors at startup only -> restarts the container at the end.

 Status-code choices were probed live 2026-07-09 (documented in the wiki
 monitoring-coverage runbook; the old handoff docs are retired):
   *arr/login-redirect apps 3xx, mcpo 404 on /, apollo https 307 self-signed.
```

## Environment / variables referenced

`A_3XX`, `A_404`, `A_OK`, `CONTAINER`, `INTERVAL`, `KUMA_CONTAINER`, `MINI`, `NAS`, `NOTIF_NAME`, `NTFY_TOKEN`, `NTFY_TOPIC`, `NTFY_URL`, `PALWORLD_ADMIN_PW`, `RETRY`

## See also

- [`add-functional-monitors.sh`](add-functional-monitors-sh.md)
- [`bootstrap-nas-monitors.sh`](bootstrap-nas-monitors-sh.md)
- [Uptime Kuma scripts](index.md) · [All scripts](../index.md)
