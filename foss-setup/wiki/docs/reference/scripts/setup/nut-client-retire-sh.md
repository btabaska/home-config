# `nut-client-retire.sh`

> nut-client-retire.sh

**Path:** `foss-setup/scripts/setup/nut-client-retire.sh` · **Category:** [Host setup](index.md) · **Type:** Bash

## What it does

```text
 nut-client-retire.sh
 Retire the NUT *netclient* (upsmon) on this box and stop the dead-poll spam.

 WHY THIS EXISTS (quality-gate fix-31 / findings H1, H29, M59)
 ------------------------------------------------------------
 nut-client-ubuntu.sh configured the Mac mini as a NUT netclient that monitors a
 UPS attached to the Synology NAS (upsd@192.168.10.4:3493). But:
   * no UPS is physically attached to the NAS (no /dev/ups*, no power_supply),
   * DSM UPS support + "network UPS server" are OFF, so the NAS never runs upsd.
 mini's upsmon therefore retried every ~5s for 7+ days — ~120k "Connection
 refused" journal errors and 4G+ of journal bloat — while providing ZERO
 power-loss protection. It only *looked* like protection was "degraded".

 Operator decision (2026-07-17): no UPS budget right now — this folds into the
 deferred glue-01 (UPS/NUT power resilience). Retire the dead client rather than
 pretend it protects anything, and stop the journal spam.

 REVERSIBLE. To bring UPS monitoring back once a UPS is wired to the NAS and DSM
 UPS support + network UPS server are enabled (with this box's IP permitted):
     sudo NUT_REENABLE=1 NAS_IP=192.168.10.4 ./nut-client-ubuntu.sh
 That path unmasks the unit, restores MODE=netclient, and rewrites the MONITOR
 block. This retire script and that re-enable path are exact inverses.

 Idempotent: re-running leaves an already-retired client retired. Run with sudo.
```

## Environment / variables referenced

`BEGIN`, `END`, `EUID`, `NUT_CONF`, `UNIT`, `UPSMON_CONF`

## See also

- [`cachyos-desktop-baseline.sh`](cachyos-desktop-baseline-sh.md)
- [`install-docker-ubuntu.sh`](install-docker-ubuntu-sh.md)
- [`install-haos-vm.sh`](install-haos-vm-sh.md)
- [`nut-client-ubuntu.sh`](nut-client-ubuntu-sh.md)
- [Host setup scripts](index.md) · [All scripts](../index.md)
