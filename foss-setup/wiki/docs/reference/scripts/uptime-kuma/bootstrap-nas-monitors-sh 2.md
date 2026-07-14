# `bootstrap-nas-monitors.sh`

> Seed Uptime Kuma with HTTP monitors for all NAS services.

**Path:** `foss-setup/scripts/uptime-kuma/bootstrap-nas-monitors.sh` · **Category:** [Uptime Kuma](index.md) · **Type:** Bash

## What it does

```text
 Seed Uptime Kuma with HTTP monitors for all NAS services.
 Run on the Mac mini (where uptime-kuma container lives):
   bash /opt/stacks/uptime-kuma/bootstrap-nas-monitors.sh

 Idempotent: skips monitors whose name already exists.
```

## Environment / variables referenced

`ACCEPT_ARR`, `ACCEPT_OK`, `ACCEPT_PLEX`, `CONTAINER`, `INTERVAL`, `KUMA_CONTAINER`, `MONITORS`, `NAS_IP`, `RETRY`, `RETRY_INTERVAL`, `SOCKET`, `USER_ID`

## See also

- [`add-functional-monitors.sh`](add-functional-monitors-sh.md)
- [`seed-monitors.sh`](seed-monitors-sh.md)
- [Uptime Kuma scripts](index.md) · [All scripts](../index.md)
