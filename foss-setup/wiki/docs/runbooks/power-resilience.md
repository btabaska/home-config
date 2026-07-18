# Power resilience — UPS monitoring (retired) & journal caps

**Status (2026-07-17): no UPS is attached to the fleet.** UPS-triggered clean
shutdown is **not** in place. This is an accepted state, folding into the deferred
tracker item **glue-01** ("UPS/NUT power resilience — no budget for a UPS right
now"). This page documents the retired NUT client, the journald size cap that
stops runaway logging, and exactly how to bring UPS monitoring **back** when a UPS
is purchased.

Origin: quality-gate fix-31 (findings **H1, H29, M59**), recorded in
`foss-setup/docs/quality-gate-2026-07-16.md`.

## What was broken

The Mac mini had been configured as a NUT **netclient** (`nut-monitor` / `upsmon`)
that monitors a UPS attached to the Synology NAS over TCP 3493:

```
UPS --USB--> DS920+ (DSM = NUT server)  <--net 3493--  mini (upsmon netclient)
```

But the NAS end never existed at runtime:

- **No UPS hardware** on the NAS — no `/dev/ups*`, no `/sys/class/power_supply/`,
  only Synology's internal boot device on USB.
- **DSM UPS support is OFF** (`SYNO.Core.ExternalDevice.UPS` → `enable=false`,
  `ACL_enable=false`, empty permitted-DiskStation list), so `upsd` never starts
  and port 3493 refuses connections.

So mini's `upsmon` retried every ~5 s **for 7+ days** — ~120 k "Connection
refused" errors — filling the persistent journal to **4.1 G** while providing
**zero** power-loss protection. Liveness looked fine (the unit was `active`); the
consumer end (a reachable UPS) never existed.

## What fix-31 did

Operator decision: **retire the dead client** (no UPS budget now), and cap the
journal so no chatty service can eat the disk again.

1. **Retired `nut-monitor` on mini** — `scripts/setup/nut-client-retire.sh`:
   stop + `disable` + **`mask`** the unit, set `MODE=none` in `/etc/nut/nut.conf`,
   and comment the managed `MONITOR` block in `/etc/nut/upsmon.conf`. A masked
   unit cannot be started by a dependency, an accidental `systemctl start`, or a
   stray re-run — the every-5 s spam cannot recur.
2. **Guarded the setup script** — `scripts/setup/nut-client-ubuntu.sh` now refuses
   to run unless `NUT_REENABLE=1` is set, so re-provisioning cannot silently
   revive the doomed client.
3. **Capped journald on mini + rig** — `configs/host/common/journald/10-size-cap.conf`
   (`SystemMaxUse=1G`, `SystemMaxFileSize=128M`), applied by
   `apply-journald-cap.sh`, which also vacuums existing bloat. mini's journal went
   **4.1 G → 1.0 G**. The NAS runs DSM (its own log rotation) and is excluded.

## Monitoring (consumer-end, not liveness)

`verification/checks.d/power-journal.yaml` — deploy with
`scripts/verification/deploy.sh`; failures page ntfy topic `verification`:

| check | host | asserts |
|---|---|---|
| `nut-monitor-retired` | mini | unit masked + inactive **and** zero `connect failed` in the last 2 min (regression: the dead client stays silent) |
| `journal-not-bloated-mini` | mini | journal usage < 2 G (class: any runaway logger, not just upsmon) |
| `journal-not-bloated-rig` | rig | journal usage < 2 G |

## Re-enabling UPS monitoring (when a UPS is bought)

This is fully reversible. Once a UPS is physically wired to the NAS:

1. **On the NAS (DSM):** Control Panel → Hardware & Power → UPS → enable UPS
   support (USB UPS) **and** "Enable network UPS server", then add mini's IP
   `192.168.10.2` to "Permitted DiskStation Devices". Confirm `upsd` is listening:
   `ssh nas 'ss -ltn | grep 3493'`.
2. **On mini:** re-run the (now guarded) setup script — it unmasks the unit,
   restores `MODE=netclient`, and rewrites the `MONITOR` block:
   ```
   sudo NUT_REENABLE=1 NAS_IP=192.168.10.4 foss-setup/scripts/setup/nut-client-ubuntu.sh
   ```
3. Verify end-to-end: `upsc ups@192.168.10.4` returns battery/status, then update
   `power-journal.yaml` (the `nut-monitor-retired` check should be replaced with a
   reachability/consumer check) and re-run `deploy.sh`.

## See also

- Scripts: [nut-client-retire.sh](../reference/scripts/setup/nut-client-retire-sh.md),
  [nut-client-ubuntu.sh](../reference/scripts/setup/nut-client-ubuntu-sh.md)
- [Verification framework](verification-self.md) · [Monitoring coverage](monitoring-coverage.md)
