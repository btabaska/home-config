# NAS host hygiene — timezone, DNS attribution, soularr parking, single-disk risk

Outcome of **fix-40** (quality-gate 2026-07-16 findings M4, M5, M6, M24, M28,
resolved 2026-07-19). The theme: host-level drift on the DS920+ that made NAS
observability lie or rot silently — a clock 3 hours off the fleet, a DNS
querylog attributing every client to one NAT address, a failed import re-skipped
every 5 minutes for days with no alert, and data volumes with no redundancy and
no tripwire. The checks in `verification/checks.d/nas-host.yaml` guard each.

## Timezone: the fleet speaks Eastern (M5)

The NAS host ran **US/Pacific** while every container set
`TZ=America/New_York` — DSM scheduled tasks fired at face-value times in
Pacific (3h later than intended), and host vs container log stamps disagreed.
The fix (2026-07-19) touched all three places DSM derives local time from,
because DSM's `SYNO.Core.Region.NTP set` webapi rejects scripted calls:

```
sudo synosetkeyvalue /etc/synoinfo.conf timezone Eastern
sudo synosetkeyvalue /etc.defaults/synoinfo.conf timezone Eastern
sudo ln -sf /usr/share/zoneinfo/US/Eastern /etc/localtime
echo 'EST5EDT,M3.2.0,M11.1.0' | sudo tee /etc/TZ    # busybox-style POSIX string
sudo systemctl restart crond                         # scheduler re-reads TZ
```

The same sweep found the **mini running UTC** — fixed with
`timedatectl set-timezone America/New_York` (systemd reschedules `OnCalendar`
timers automatically; `cron` needs a restart). Fleet policy now lives in
ansible (`roles/base`, `fleet_timezone` in `group_vars/all.yml`) for mini/rig;
the NAS is a DSM appliance outside ansible, so its setting is guarded by the
`nas-timezone-eastern` check (all three sources must agree — a DSM upgrade
regenerating `synoinfo.conf` is the realistic drift path). Fleet-wide skew is
caught by `fleet-timezone-consistent` (mini == nas == rig UTC offset).

DSM task times are stored as wall-clock (`run hour=`/`run min=` in
`/usr/syno/etc/synoschedule.d/root/*.task`) — after the switch they fire at
face value in Eastern: Immich DB dump 02:30, beets import 03:15, DSM auto
update Thu 03:40, daily S3 backup 19:10.

## AdGuard-NAS client attribution (M28)

All ~52k queries/day were attributed to `172.23.0.1` — the docker bridge
gateway — because port 53 was published from a bridge network. Per-client
stats, client-specific rules and querylog forensics were impossible. Fixed by
recreating the container with **`network_mode: host`**
(`configs/docker-stack/stacks/adguard-nas/compose.yaml`, mirrored live at
`/volume1/docker/adguard-nas/`).

- **Check:** `nas-adguard-client-attribution` — digs the canary
  `verify-attrib.tabaska.us` (answered locally by the `*.tabaska.us` rewrite,
  never leaks upstream) from the mini, then asks the querylog API who asked.
  Red means bridge NAT is back. Credentials: `ADGUARD_NAS_USER/PASS` in
  `/etc/verification/env` (vault `adguard_nas.*`).
- Resolution liveness itself is separately guarded by `dns-nas-internal` /
  `dns-nas-external` in `dns.yaml`.

## Soularr parked failed imports (M6 / M24)

An entry in `/volume1/docker/soularr/failed_imports.json` is a work item
soularr will **never retry or clean up** — it re-logs "Skipping failed import
album" every 5-minute cycle forever. The Eminem entry (album 5030) sat there
5+ days; meanwhile the album had already been imported to 100% by other means,
so the entry was pure stale state (cleared to `{}` 2026-07-19).

**When `nas-soularr-failed-imports-fresh` goes red** (`stale>0`): the listed
album needs a human decision —

1. Check the album in Lidarr (`http://192.168.10.4:8686`): if it is already
   100% on disk, the entry is stale — clear it:
   `ssh nas 'echo "{}" > /volume1/docker/soularr/failed_imports.json'`
   (or surgically remove one key with python; the file is btabaska-writable).
2. If genuinely incomplete: fix the underlying import (see the parked files
   under seedbox `~/files/slskd/failed_imports/`), import manually via Lidarr,
   *then* clear the entry.
3. `cycling=no` means soularr itself stopped running (log stale >20 min) —
   check the container on the NAS: `sudo /usr/local/bin/docker ps | grep soularr`.

Known leftover (deliberately kept, operator decision 2026-07-19): two orphan
folders on the seedbox at `~/files/slskd/failed_imports/` — `mgk - Hotel
Diablo (2019)` (241M) and `Owl City - Cinematic (2018)` (325M). Both albums
are 100% in Lidarr; the folders are residue from imports that succeeded by
another path. Reap them with the fix-45 seedbox cleanup batch.

## Single-disk volumes — accepted risk + tripwire (M4)

All three data volumes are **single-disk SHR with no redundancy** (DSM:
`shr_without_disk_protect`): md2/vol1 = WD161KFGX 16TB, md3/vol2 = WD120 12TB,
md4/vol3 = ST18000 18TB — each `raid1 [1/1] [U]`. A single disk failure loses
that entire volume; the only recovery is the off-site B2 Hyper Backup. This is
an **accepted, deliberate** layout on the 4-bay DS920+ (capacity over parity)
— reaffirmed 2026-07-19, not scheduled for change.

What makes it survivable is *noticing immediately*:

- **Check:** `nas-md-arrays-healthy` (crit) pins the exact healthy topology
  `md0=[UUU_]:md1=[UUU_]:md2=[U]:md3=[U]:md4=[U]:faulty=0`. The system arrays
  md0/md1 mirror across **all three** disks, so any single disk dying degrades
  them — the check pages on the first symptom even though the data volumes
  themselves have no mirror to degrade. (`[4/3] [UUU_]` is the normal shape:
  a 4-slot chassis with 3 disks.)
- DSM's own SMART monitoring + email notifications remain the disk-health
  channel; the check is the last-line tripwire that does not depend on DSM
  notification config.
- If it fires: treat as an active disk emergency — check DSM Storage Manager,
  verify the latest Hyper Backup integrity, and do not reboot the NAS until
  you know which disk is failing.

## Verification

All five checks live in `verification/checks.d/nas-host.yaml` (deployed to
mini `/opt/verification/checks.d/`), run unprivileged (no passwordless sudo on
DSM), alert to ntfy topic `verification`, and are part of the daily sweep
(dead-man ping `verification-mini`): `nas-timezone-eastern`,
`fleet-timezone-consistent`, `nas-adguard-client-attribution`,
`nas-soularr-failed-imports-fresh`, `nas-md-arrays-healthy`.
