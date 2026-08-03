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
(`configs/nas/adguard-nas/compose.yaml`, mirrored live at
`/volume1/docker/adguard-nas/`).

- **Check:** `nas-adguard-client-attribution` — digs the canary
  `verify-attrib.tabaska.us` (answered locally by the `*.tabaska.us` rewrite,
  never leaks upstream) from the mini, then asks the querylog API who asked.
  Red means bridge NAT is back. Credentials: `ADGUARD_NAS_USER/PASS` in
  `/etc/verification/env` (vault `adguard_nas.*`).
- Resolution liveness itself is separately guarded by `dns-nas-internal` /
  `dns-nas-external` in `dns.yaml`.

## Soularr failed-import denylist + music acquisition hygiene (M6 / M24 / fix-56)

An entry in `/volume1/docker/soularr/failed_imports.json` is a work item
soularr will **never retry or clean up** — it re-logs "Skipping failed import
album" every cycle forever. The upstream image (`add_to_failed_import_denylist`
in `/app/soularr.py`) is **append-only**: no code path ever removes an entry,
even after the album is completed elsewhere or unmonitored. The Eminem entry
(album 5030) sat there 5+ days at 100% imported (fix-40 cleared it by hand);
by 2026-08-02 the file had re-grown to 9 entries — 3 complete ghosts (Paradise,
Hybrid Theory, Underclass Hero) + 6 genuinely-stuck — and Camera/Heat Waves had
aged past the 3-day `nas-soularr-failed-imports-fresh` threshold (SM29).

**The closer (fix-56): a mini reconciler, not a manual clear.**
`soularr-denylist-reconcile` (configs/host/mini/soularr-reconcile, every 6h)
prunes any denylist entry whose album is, per live Lidarr, **complete /
unmonitored / deleted**, leaving only genuinely-stuck monitored+incomplete
albums. Force a run: `sudo systemctl start soularr-denylist-reconcile` on the
mini. Outcome probe: `soularr-denylist-no-ghosts`. Do **not** hand-edit the JSON.

**When `nas-soularr-failed-imports-fresh` goes red** (`stale>0`) despite the
reconciler, the surviving entries are monitored + still-incomplete — a human
decision:

1. Check the album in Lidarr (`http://192.168.10.4:8686`). If it can be sourced,
   complete it (a Lidarr AlbumSearch on the torrent path — a **different** source
   than the Soulseek path soularr failed on); the reconciler prunes it once it
   goes complete.
2. If it is unsourceable (soularr has failed it for days), **unmonitor** it
   (`PUT /api/v1/album/monitor {albumIds, monitored:false}`) — it leaves the
   wanted list and the reconciler prunes its denylist entry. Files already on
   disk stay; re-monitor + search to retry later.
3. `cycling=no` means soularr itself stopped running (log stale >20 min) —
   check the container on the NAS: `sudo /usr/local/bin/docker ps | grep soularr`.

**Junk MusicBrainz releases (SM30).** Bootleg/mislabeled release-groups (e.g.
Chinese-titled 'albums' under a Western pop artist — `莉查` / `呼啸山庄` /
`古 惑-狼豪 华版` under Charli xcx) get monitored when an artist is added; soularr
searches them every cycle and never matches ("N releases failed to find a match
and are still wanted"). Unmonitor them (same PUT as above) — the monitored flag
persists across metadata refreshes, so they stay quiet.

**Stuck partials (fix-28 class).** `album_match` requires **all** tracks before
grabbing, so a partial album (e.g. Born to Die 17/24) came from a flaky Soulseek
transfer, NOT a low `minimum_filename_match_ratio` — don't tune the ratio to
"fix" it. Either complete it out-of-band or unmonitor it (files stay on disk;
`lidarr-incomplete-albums` only flags MONITORED partials). A completed-but-
importFailed grab stuck in the Lidarr queue ("One or more tracks expected ...
were not imported" while the album is already 100% on disk) is now auto-reaped
by the `arr-queue-reconcile` timer (Lidarr added to it in fix-56).

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

## I/O pressure + arr SQLite 'database is locked' storm (fix-55)

The symptom: several NAS arrs (radarr / lidarr / whisparr / prowlarr / bookshelf
— **not** sonarr) log recurring `database is locked` at once, their scheduled
tasks (RefreshMonitoredDownloads, ImportListSync, vacuum) fail, their APIs 500,
soularr fatal-exits every cycle, the mini `lidarr-artist-monitor-reconcile` unit
flaps, CWA's container healthcheck times out, and `docker logs` / `docker system
df` hang for minutes. Every one of those looks green at the container level.

**Root cause is not per-app corruption — it is NAS-wide disk I/O saturation.**
Under sustained pressure the arrs' SQLite `fsync` runs slower than their
`busy_timeout`, so a writer holds the write lock too long and other writers get
`SQLITE_BUSY`. The arrs expose **no** `busy_timeout` knob (config.xml carries
only `LogLevel`) and their DB files are already `nodatacow` (`lsattr` shows `C`),
so the remedy is to **remove the I/O pressure, not tune SQLite**.

Diagnose (light, sequential — do not pile parallel heavy reads onto an already
saturated NAS):

- **Is it saturated?** `ssh nas uptime` → Synology splits the load average into
  `[IO: 1m, 5m, 15m CPU: …]`. Read the **15-min IO** figure. Quiet baseline is
  ~2.8; the fix-55 storm sat at 17-22. This is what `nas-io-pressure` watches
  (threshold 12).
- **Rule out a scrub / resync:** `sudo sh -c 'cat /proc/mdstat; btrfs scrub
  status /volume1'` — a real resync/scrub is expected transient load, not this.
- **Find the hog (blkio accounting is compiled out on DSM, and `docker stats`
  hangs)** — sample `/proc/<pid>/io` twice and diff, mapping each pid to its
  container via `/proc/<pid>/cgroup` (`…/docker/<id>`). In fix-55 the steady
  writers were: `btrfs-cleaner` (CoW GC, ~4.7 MB/s — downstream of everything
  else), **bitmagnet-postgres** (~3 MB/s — the always-on DHT crawler), and
  `dockerd` (~1.2 MB/s — the Synology `db` log driver writing per-container
  `log.db`). `synoimgbkptool` spikes are a transient nightly DSM backup.

Fixes applied by fix-55 (all codified in the repo mirrors):

- **bitmagnet DHT crawler throttled:** `DHT_CRAWLER_SCALING_FACTOR=3` (default 10)
  in `configs/nas/bitmagnet/docker-compose.yml` — ~3x less Postgres write I/O
  while still ingesting thousands/30min. (Env→config mapping has **no** prefix:
  it is `DHT_CRAWLER_SCALING_FACTOR`, not `BITMAGNET_*`.)
- **json-file log caps** (`max-size: 10m`, `max-file: 3`) on bitmagnet / CWA /
  soularr — replaces Synology's `db` driver so `docker logs` is fast + bounded
  (fixes the CWA logs hang) and cuts dockerd's write load.
- **CWA healthcheck relaxed** (`/login`, 60s/20s/5/120s) so load latency no
  longer flips it `unhealthy`.
- **soularr `SCRIPT_INTERVAL` 300→900** to cut failed-cycle churn (its per-run
  fatal-exit is upstream image behaviour with no retry knob; eliminating the arr
  500s is what stops it).
- **mini `lidarr-artist-monitor-reconcile.py`** now retries transient 5xx with
  backoff instead of `exit 1` on the first one.

There is **no blkio bandwidth cap available** — the Synology kernel stubs the
blkio controller (no throttle/accounting cgroup files), so workload reduction is
the only lever.

## Verification

Six checks. Five live in `verification/checks.d/nas-host.yaml`: `nas-timezone-eastern`,
`fleet-timezone-consistent`, `nas-adguard-client-attribution`,
`nas-soularr-failed-imports-fresh`, `nas-md-arrays-healthy`. Two more (fix-55)
live in `verification/checks.d/nas-io-storm.yaml` — `nas-io-pressure` (class-level:
NAS 15-min IO-load below threshold) and `arr-sqlite-not-locked` (regression: no
'database is locked' storm in the last 15 min across lidarr/radarr/whisparr).
Two more (fix-56) live in `verification/checks.d/soularr-backlog.yaml` —
`soularr-denylist-no-ghosts` (class/outcome: 0 denylist entries are complete/
unmonitored/deleted in Lidarr, i.e. the reconciler keeps the dead-letter honest)
and `soularr-reconcile-timer-healthy` (the reconciler timer is alive). All
run from mini (`ssh nas` / arr log API), alert to ntfy topic `verification`, and
are part of the daily sweep (dead-man ping `verification-mini`).
