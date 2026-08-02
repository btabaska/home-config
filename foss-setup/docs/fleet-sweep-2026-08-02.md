# Fleet sweep — 2026-08-02 (full read-only audit)

> **Method**: `/fleet-sweep` full run — 37 read-only auditor lanes (5 host, 9 service, 18 flow, 4 repo, 1 architecture) fanned out via the Workflow orchestrator, 41 adversarial skeptic verifications on medium-confidence and high/critical claims, 1 completeness critic, plus 5 critic-dispatched gap missions executed inline by the orchestrator after the subagent session limit (85 agents total, ~4.0M subagent tokens, 1,401 tool calls, 84 min wall; seeded by two audit-safe full check runs 10:23 + 13:01 EDT, 267-270/296 passing).
> **Nothing was modified on any host.** The only writes of the whole sweep are the repo artifacts of this commit and scratch state under `/tmp/verify-audit` on mini.
> Machine-readable twin: `fleet-sweep-2026-08-02.json` (severity-sorted; position within each block derives the id). Work items: `fleet-sweep-2026-08-02-worklist.md` → tasks `fix-49`…`fix-69`, drive with `/resolve-finding fix-NN`.
> Lane roster: host:mini|nas|rig|seedbox|ha · svc:arr-stack|nas-apps|media-aux|ai-stack|infra-mini|monitoring-stack|docs-life|gaming|reading · flow:movies-tv|music|books|audiobooks-ipod|manga-comics|photos|youtube|journaling|ai-serving|monitoring-alerting|bug-intake|git-control-plane|backups|syncthing-mesh|edge-dns|ha-consumer|game-servers|retro · repo:live-drift|verification-suite|tracker-wiki|junk-deadpaths · arch:topology · gap:nas-io-rootcause|wiki-rag-conflict|apollo-streaming|rig-relapse-aug1|stash-import-outcome (restore-drill mission not run — covered by open task sbom-05).

**Totals: 318 findings — 2 critical / 19 high / 58 medium / 46 low / 193 info** (2 candidates refuted during verification; 34 cross-lane duplicates merged)


---

## CRITICAL (2)

### SC1. Entire Navidrome library (3495/3495 tracks) flagged missing since 2026-08-01 — user-facing music outage; .ndignore comment-line + an empty-looking CIFS root during one hourly scan; quick scans cannot clear it

**Host:** mini · **Component:** navidrome · **Auditor:** svc:media-aux · **Work item:** `fix-49` · *skeptic-confirmed*

Check navidrome-library-present failed today (10:23 EDT run) with PRESENT_DEGRADED missing=3495/3495; live DB query confirms total=3495 missing=3495, i.e. every track is greyed out/unplayable — a user-facing outage of the music service. Root cause reproduced live: /mnt/nas/music/.ndignore (mtime Aug 1 05:00) contains the single line '#recycle', which in Navidrome's gitignore syntax is a COMMENT, making the file effectively empty — and an empty .ndignore at a folder root makes Navidrome skip that folder entirely (the documented fix-28 grey-out trap, now at the LIBRARY root). The first scan after (2026-08-01 09:18:49Z = 05:18 EDT) mass-flagged everything; hourly quick scans since (fullScan=false, ~400ms) cannot clear missing flags — a full scan is required after removing/fixing the marker. The writer is fix-28's own hardening: foss-setup/scripts/nas/empty-recycle-30d.sh (monthly, matches the Aug 1 05:00 mtime) and ensure-navidrome-music-ignore.sh both run printf '#recycle\n' > /volume1/music/.ndignore — the pattern needed escaping (\#recycle) to match a literal-# folder. The CIFS mount is healthy host-side and container-side (47 entries visible both ways), so this is NOT a mount failure. Regression of done task fix-28, caused by fix-28's own countermeasure. NOT fixed per read-only mandate (fix = correct/remove the root marker in both scripts + on NAS, then trigger a full scan).

MERGED duplicate from flow:music (C3): Entire Navidrome library (3495/3495 files, 139/140 folders incl. root) flagged missing since 2026-08-01 05:18 EDT — one hourly scan saw the CIFS root vanish; quick scans cannot clear it — Regression of fix-28 (check navidrome-library-present, PRESENT_DEGRADED missing=3495/3495). Root cause isolated: the hourly quick scan at 2026-08-01 09:18:49 UTC flagged every media_file row missing=1 (all updated_at stamped 09:18:49.04) and marked 139/140 folder rows missing INCLUDING the library root '.', with library.total_songs=0 — the scanner observed the /music root as empty/gone and logged only 'Finished refreshing albums refreshed=298' with zero errors. The preceding 08:18Z scan took 8.02s vs the normal ~0.4s, indicating the CIFS share was already stalling. Every other explanation is excluded live: NAS up 30 days no reboot, mini mnt-nas-music.mount continuously active since Jul 13, zero kernel CIFS/VFS errors since Jul 31, and the container sees all 47 artist dirs right now (host view == container view). Per known Navidrome behavior the 0.62 quick scan never clears missing flags — recovery needs a full scan (-f), NOT run per read-only mandate. Meanwhile the container reports (healthy) and /ping via Caddy returns 200 — textbook green-but-broken (pattern #2); user has had a fully greyed-out music library for 30+ hours while the check sat at severity warn.

*Verify note:* CONFIRMED with fresh probes. (1) DB re-query: media_file total=3495 missing=3495, newest missing update 2026-08-01 09:18:49Z. (2) /mnt/nas/music/.ndignore re-read: mtime Aug 1 05:00, content exactly '#recycle' — a gitignore COMMENT, so the file is effectively empty, which per the documented fix-28 trap skips the folder it sits in; here that folder is the library root. (3) Independent probe: a DB-flagged-missing track (Chappell Roan HOT TO GO!.flac) exists host-side AND in-container at identical byte size 40626998 — files are present, so this is a scanner false-missing mass-flag, not a mount/data failure; today's scan log shows fullScan=false, which cannot clear missing flags. (4) Writer confirmed in repo: foss-setup/scripts/nas/empty-recycle-30d.sh:29 and ensure-navidrome-music-ignore.sh:27 both printf '#recycle\n' > music-root/.ndignore (pattern needed \#recycle escaping); the monthly script's if-not-exists guard matches the Aug 1 05:00 mtime. Severity unchanged: full user-facing outage of the music service since Aug 1, self-inflicted by fix-28's own countermeasure. Remediation as stated: fix/remove root marker in both scripts + live NAS file, then trigger a FULL scan (quick scans won't clear missing).

<details><summary>Evidence</summary>

```
ssh mini 'python3 -c "import sqlite3; c=sqlite3.connect(\"file:/opt/stacks/navidrome/data/navidrome.db?mode=ro\",uri=True); print(c.execute(\"select count(*),sum(missing) from media_file\").fetchone())"'
-> total=3495 missing=3495 ; newest_missing_update: 2026-08-01 09:18:49.04078812+00:00
ssh mini 'ls -la /mnt/nas/music/.ndignore; cat -A /mnt/nas/music/.ndignore'
-rwxr-xr-x 1 btabaska btabaska 9 Aug  1 05:00 /mnt/nas/music/.ndignore
#recycle$
ssh mini 'ls /mnt/nas/music | wc -l; docker exec navidrome ls /music | wc -l'
47
47
ssh mini 'docker logs navidrome --tail 400 2>&1 | grep -i scan | tail -2'
time="2026-08-02T16:18:49Z" level=info msg="Scanner: Starting scan" fullScan=false numLibraries=1
time="2026-08-02T16:18:49Z" level=info msg="Scanner: Finished scanning all libraries" duration=458.5ms
grep -n "printf '#recycle" foss-setup/scripts/nas/empty-recycle-30d.sh foss-setup/scripts/nas/ensure-navidrome-music-ignore.sh
empty-recycle-30d.sh:  printf '#recycle\n' > /volume1/music/.ndignore   (runs monthly; if [ ! -f ] guard recreated it Aug 1 05:00)
ensure-navidrome-music-ignore.sh:27:  printf '#recycle\n' > "$ROOT_MARKER"
--- (merged lane flow:music) ---
ssh mini 'docker exec navidrome sqlite3 -readonly /data/navidrome.db "SELECT COUNT(*) FROM media_file; SELECT COUNT(*) FROM media_file WHERE missing=1;"'
3495
3495
ssh mini 'docker exec navidrome sqlite3 -readonly /data/navidrome.db "SELECT COUNT(*), SUM(missing) FROM folder; SELECT path, missing, num_audio_files, updated_at FROM folder WHERE parent_id='' LIMIT 2;"'
140|139
.|1|0|2026-08-01 09:18:49.039957166+00:00
ssh mini 'docker exec navidrome sqlite3 -readonly /data/navidrome.db "SELECT path, updated_at FROM media_file WHERE missing=1 LIMIT 1;"'
Chappell Roan/...HOT TO GO!.flac|2026-08-01 09:18:49.04078812+00:00
ssh mini 'docker logs navidrome --since 2026-08-01T03:00:00 --until 2026-08-01T05:19:30 2>&1 | tail -6'
time="2026-08-01T08:18:49Z" level=info msg="Scanner: Starting scan" fullScan=false
time="2026-08-01T08:18:57Z" level=info msg="Scanner: Finished scanning all libraries" duration=8.02s
time="2026-08-01T09:18:49Z" level=info msg="Scanner: Starting scan" fullScan=false
time="2026-08-01T09:18:50Z" level=info msg="Scanner: Finished refreshing albums" refreshed=298 skipped=3
time="2026-08-01T09:18:51Z" level=info msg="Scanner: Finished scanning all libraries" duration=2.15s
ssh mini 'journalctl -k --since "2026-07-31" --no-pager | grep -iE "cifs|vfs"'  # (no output)
ssh mini 'systemctl show mnt-nas-music.mount -p ActiveEnterTimestamp'
ActiveEnterTimestamp=Mon 2026-07-13 15:17:05 EDT
ssh mini 'ls /mnt/nas/music | wc -l; docker exec navidrome ls /music | wc -l'
47
47
ssh nas 'uptime'  # up 30 days, 21:41
curl -s https://music.tabaska.us/ping  # returns '.' (200) while library is 100% greyed
```

</details>

### SC2. Active Bitmagnet-DHT junk-grab storm: arrs re-grab owned titles hourly; foreign-audio rips imported into the movie library today

**Host:** nas · **Component:** radarr/sonarr + prowlarr Bitmagnet (DHT) indexer · **Auditor:** flow:movies-tv · **Work item:** `fix-50` · *skeptic-confirmed*

Every grab in both arrs' recent history (2026-08-02, observed ~15:30 EDT) is 'Bitmagnet (DHT) (Prowlarr)': radarr ~hourly (12 grabs 09:09Z-16:54Z), sonarr ~every 30min. The grabs are junk re-releases of ALREADY-OWNED titles (MegaPeer/seleZen 720p re-encodes, Rus.Eng/MULTi/NORDiC/Korean-dub rips) which then fail import as 'Not an upgrade for existing movie file. Existing quality: Bluray-1080p' — this storm IS the bulk of radarr-queue-stuck stuck=9 and feeds sonarr-queue-stuck (verify-06 regression), and it churns 3-16GB of seedbox disk/bandwidth per grab. Worse, grabs that pass the upgrade check DO import: Aliens (1986) and Chinatown (1974) landed today as Russian/English dual-audio rips and Hotel Transylvania 3 as Bulgarian/English (movieFile dateAdded 2026-08-02) — active user-facing library contamination, fix-27 'green-but-not-watchable' class. Also two 0%/0-seed dead bitmagnet grabs sit unhandled (Baywatch 5.0d, Deadpool 0.1d) — radarr stalled-download handling not kicking in. Shared root cause of this lane's queue stalls; no open task covers bitmagnet grab-quality gating. NOT fixed per read-only mandate (obvious mitigations: disable/negative-score the Bitmagnet indexer in arr profiles, blocklist the junk, re-grab clean copies).

*Verify note:* CONFIRMED by 4 fresh probes, and live state is worse than filed. (1) Radarr history eventType=1: 15/15 newest grabs = 'Bitmagnet (DHT) (Prowlarr)', storm STILL ACTIVE — new grabs at 17:29Z (after auditor's ~15:30 EDT snapshot). (2) Sonarr: 10/12 newest grabs Bitmagnet DHT, ~30-min cadence confirmed. (3) Radarr queue totalRecords=13: 8 stuck on 'Not an upgrade'/'Not a Custom Format upgrade'/importBlocked exactly as claimed; the two dead grabs (Baywatch 5d, Deadpool) still sit in downloading state. (4) Independent movie-file probe: 12 files imported 2026-08-02, >=8 foreign-audio — Aliens + Chinatown (Rus/Eng) and Hotel Transylvania 3 (Bulgarian/Eng) verified exactly, PLUS new contamination since audit: The Accountant² (Rus/Eng) imported 17:15Z, and Last Christmas imported today with Russian-ONLY audio (no English track). Severity critical stands: ongoing hourly, actively degrading the watchable library, no quality gate on the Bitmagnet indexer.

<details><summary>Evidence</summary>

```
ssh mini 'RK=$(sudo grep "^RADARR_API_KEY=" /etc/verification/env|cut -d= -f2); curl -s -H "X-Api-Key: $RK" "http://192.168.10.4:7878/api/v3/history?eventType=1&pageSize=12&sortKey=date&sortDirection=descending" | …'
2026-08-02T16:54:57Z | Bitmagnet (DHT) (Prowl | The.Accountant.2.2025.1080p.BluRay.DD.5.1.x264-Meg
2026-08-02T15:22:21Z | Bitmagnet (DHT) (Prowl | Deadpool.2016.BDRip.1080p.mkv
2026-08-02T14:51:36Z | Bitmagnet (DHT) (Prowl | Halloween.Kills.2021.Theatrical.BDRip.1080p.mkv
2026-08-02T14:51:34Z | Bitmagnet (DHT) (Prowl | Nope.2022.IMAX.1080p.BluRay.x264-SbR_EniaHD.mkv
2026-08-02T13:49:56Z | Bitmagnet (DHT) (Prowl | Kingsman.The.Secret.Service.2014.1080p.BluRay.x264
2026-08-02T12:17:36Z | Bitmagnet (DHT) (Prowl | Wreck-It.Ralph.2012.1080p.BluRay.3xRus.Ukr.Eng.HDC
2026-08-02T10:12:46Z | Bitmagnet (DHT) (Prowl | Chinatown.1974.BDRip.1080p.Rus.Eng.mkv
(sonarr eventType=1: 10/10 newest grabs also 'Bitmagnet (DHT) (Prowlarr)', 11:45Z-16:41Z)
Radarr queue rejects (…/api/v3/queue?pageSize=60): 'Not an upgrade for existing movie file. Existing quality: Bluray-1080p. New Quality WEBDL-1080p.' x Wicked/Moana-KoreanDub/SuperMario/Passengers; 'Bluray-720p' x Sinners/Borderlands
curl …/api/v3/movie | filter:
Aliens | Aliens (1986) {tmdb-679} - [Bluray-1080p][AC3 5.1][x264].mkv | added: 2026-08-02T08:48:12 | langs: [{'id': 11, 'name': 'Russian'}, {'id': 1, 'name': 'English'}
Chinatown | Chinatown (1974) {tmdb-829} - [Bluray-1080p][AC3 2.0][x264].mkv | added: 2026-08-02T10:29:15 | langs: [{'id': 11, 'name': 'Russian'}, {'id': 1, 'name': 'English'}
Hotel Transylvania 3: Summer Vacation | … | added: 2026-08-02T09:24:41 | langs: [{'id': 29, 'name': 'Bulgarian'}, {'id': 1, 'name': 'English'}
deluge RPC (seedbox 127.0.0.1:3254): radarr 0.00% Downloading seeds=0 age_d=5.0 Baywatch.2017…; radarr 0.00% Downloading seeds=0 age_d=0.1 Deadpool.2016.BDRip.1080p.mkv
```

</details>


---

## HIGH (19)

### SH1. Recurring 'database is locked' across 5 arr apps — scheduled tasks failing and consumer-visible 500s, reproduced live today

**Host:** nas · **Component:** arr-stack SQLite (radarr/lidarr/whisparr/prowlarr/bookshelf) · **Auditor:** svc:arr-stack · **Work item:** `fix-55` · *skeptic-confirmed*

Every NAS arr except Sonarr shows recurring SQLite 'database is locked' errors with latest occurrences today 2026-08-02 (17:42-17:46 UTC = during this probe). It is not just log noise: Lidarr fails RefreshMonitoredDownloads, Whisparr fails ImportListSync/ProcessMonitoredDownloads/RefreshMonitoredDownloads AND its database vacuum, Bookshelf logs 19x Task Error, Prowlarr fails HistoryService — i.e. the task engines that drive import tracking are intermittently dying. Consumer impact confirmed: musicseerr on mini received HTTP 500 from Lidarr /api/v1/history at 13:42:15 EDT, the exact second Lidarr logged a database-is-locked on that endpoint (taxonomy #2 masked by green containers). Error clusters at ~00:00-02:00 UTC and mid-day suggest a nightly job (backup/vacuum window) plus daytime API load (soularr cycling, fix-40) contending on /volume1/docker SQLite files. Possibly feeding nas-core-dumps (fix-45, taxonomy #3). No open task covers this. NOT fixed per read-only mandate.

*Verify note:* CONFIRMED with fresh probes from mini (arr keys from /etc/verification/env; prowlarr key from NAS config.xml via sudo). All 5 apps show SQLite 'database is locked' as their newest error record today 2026-08-02: lidarr 17:42:16Z (494 err records), prowlarr 17:46:25Z (56), whisparr 08:56:58Z (97), bookshelf 01:17:19Z (22), radarr 09:01:49Z GET /movie + 01:16Z POST /command + DownloadDecisionMaker 'Couldn't process release' (206 err records, 14 locked in latest 200 — worse than auditor's 2x). Independent consumer probe: musicseerr on mini received HTTP 500 from Lidarr /api/v1/history FOUR times today (06:27/10:20/12:21/13:42 EDT), not just the one 13:42 instance the auditor cited, while docker shows 'Up 2 weeks (healthy)'. Evidence is slightly stronger than filed; mechanism (task-engine failures + consumer 500s behind green containers, clustering ~00-02 UTC nightly window + daytime API load) stands. Severity high is correct — intermittent failure, not full outage.

<details><summary>Evidence</summary>

```
curl -sm 15 -H "X-Api-Key: $LIDARR_KEY" http://192.168.10.4:8686/api/v1/log?pageSize=30&level=error
 5x last=2026-08-02T17:42:15 Request Failed. GET /api/v1/history: database is locked
 3x last=2026-08-02T17:01:25 Task Error: database is locked
 1x last=2026-08-02T10:02:54 Error occurred while executing task RefreshMonitoredDownloads: database is locked
curl ... http://192.168.10.4:6969/api/v3/log?level=error   # whisparr, 97 error records total
 3x last=2026-08-02T08:56:58 Error occurred while executing task ImportListSync: database is locked
 1x last=2026-08-02T00:41:53 An Error occurred while vacuuming database.: database is locked
curl ... http://192.168.10.4:9696/api/v1/log?level=error   # prowlarr
12x last=2026-08-02T17:46:25 [GET /8/api]: database is locked
curl ... http://192.168.10.4:8790/api/v1/log?level=error   # bookshelf
19x last=2026-08-02T01:17:19 Task Error: database is locked
curl ... http://192.168.10.4:7878/api/v3/log?level=error   # radarr
 2x last=2026-08-01T23:49:15 Task Error: database is locked
ssh mini 'docker logs --tail 300 musicseerr 2>&1 | grep -i error'
2026-08-02 13:42:15,605 - httpx - INFO - HTTP Request: GET http://192.168.10.4:8686/api/v1/history?... "HTTP/1.1 500 Internal Server Error"
```

</details>

### SH2. Sonarr stuck=16 classified: two grabs from Jul 29-30 never materialized on the seedbox — retrying 'Import failed, path does not exist' for 3-4 days

**Host:** nas · **Component:** sonarr (:8989) import pipeline · **Auditor:** svc:arr-stack · **Work item:** `fix-54` · *skeptic-confirmed*

Verifies today's sonarr-queue-stuck check (regression of verify-06). Of 18 queue records, 13 are ONE season pack (Better.Off.Ted.S02.REPACK, added 2026-07-30T00:17Z, one row per episode) and 1 is A.Knight.of.the.Seven.Kingdoms.S01E03 (added 2026-07-29T19:02Z), both cycling 'Import failed, path does not exist or is not accessible by Sonarr: /seedbox/tv/...' (15x each in the last 30 error-log records, latest 17:46Z today). Root cause is upstream of the NAS: the rclone mount is live and healthy, but the payload directories exist on NEITHER the NAS mount NOR seedbox ~/files/tv — only the .torrent files sit in deluge's session dir since Jul 30, i.e. the torrents were added but never completed/moved (taxonomy #4 grabbed-but-never-imported; deluge lane owns the deeper walk). Remaining rows: 3 benign 'not an upgrade' importPending decisions, 1 importBlocked wrong-series match (Walking.Dead.Dead.City.S03E02 matched to Interview With The Vampire via grab history, added today), and House.of.the.Dragon.S02E07 in 'downloading' since 07-30 (3+ days — watch). Obvious fix (blocklist + re-search the two dead grabs, resolve the mismapping) NOT applied per read-only mandate.

*Verify note:* CONFIRMED with fresh probes (2026-08-02 ~18:00Z). (1) Fresh /api/v3/queue: 18 records — 13x Better.Off.Ted.S02.REPACK importPending (added 2026-07-30T00:17), 1x A.Knight.of.the.Seven.Kingdoms.S01E03 importPending (2026-07-29T19:02), 1x TWD.Dead.City.S03E02 importBlocked (today), 1x House.of.the.Dragon.S02E07 still status=downloading since 07-30T08:41 — matches the finding. (2) Fresh error log: still actively cycling — 15x 'Import failed, path does not exist ... /seedbox/tv/Better.Off.Ted.S02.REPACK...' and 14x same for A.Knight S01E03, latest 2026-08-02T17:59:09Z (minutes before probe), i.e. later than the auditor's 17:46 — retry loop ongoing. (3) Independent upstream probes: NAS rclone mount live (fuse.rclone mounted, tv dir listable) with ZERO matches for either payload in /volume1/mounts/seedbox-files/tv/; seedbox ~/files/tv has no match and a find across ~/files found no payload — only the .torrent files sit in deluge's ~/.session (Better.Off.Ted mtime Jul 30 03:39, Knight S01E03 Jul 30 11:17). Taxonomy #4 grabbed-but-never-completed is corroborated: torrents added Jul 30 but payload never materialized, so Sonarr's 'path does not exist' is a true statement, root cause upstream on the deluge/seedbox side (session dir also holds undelivered Knight S01E04-06 torrents — supports the deluge-lane deeper walk). Minor detail correction only: 2 benign 'not an upgrade' importPending rows now (Sunny S15E06, Only.Murders S02E05), not 3 — queue is dynamic, immaterial. Also observed one 'database is locked' ProcessMonitoredDownloads error at 17:56Z (single occurrence, noise). Severity high stands: 3-4 day content-delivery stall, ongoing retries, plus the wrong-series importBlocked mismap.

<details><summary>Evidence</summary>

```
curl -sm 20 -H "X-Api-Key: $SONARR_KEY" "http://192.168.10.4:8989/api/v3/queue?pageSize=60"
13x 2026-07-30T00:17:06 importPending  Better.Off.Ted.S02.REPACK.1080p.WEBRip.DDP5.1.x264
 1x 2026-07-29T19:02:11 importPending  A.Knight.of.the.Seven.Kingdoms.S01E03.The.Squire.1
 1x 2026-08-02T10:25:58 importBlocked  The.Walking.Dead.Dead.City.S03E02.Haven.1080p.AMZN
 1x 2026-07-30T08:41:18 downloading    House.of.the.Dragon.S02E07.1080p.MAX.WEB-DL.DDP5.1
curl ... /api/v3/log?level=error&pageSize=30
15x last=2026-08-02T17:46:07 Import failed, path does not exist or is not accessible by Sonarr: /seedbox/tv/Better.Off.Ted.S02.RE
15x last=2026-08-02T17:46:07 Import failed, path does not exist or is not accessible by Sonarr: /seedbox/tv/A.Knight.of.the.Seven
ssh nas 'mount | grep seedbox; ls /volume1/mounts/seedbox-files/tv/ | grep -iE "better|knight"'
seedbox:/home/hd34/btabaska/files on /volume1/mounts/seedbox-files type fuse.rclone (rw,...)
(only an unrelated S01E02 dir matched; no S02 REPACK, no S01E03)
ssh seedbox 'ls ~/files/tv/ | grep -iE "better.off|knight"; find ~ -maxdepth 3 -iname "*better.off.ted*"'
/home/hd34/btabaska/.session/Better.Off.Ted.S02.REPACK.1080p.WEBRip.DDP5.1.x264-NiXON[rartv].torrent  (mtime Jul 30 03:39; payload absent)
```

</details>

### SH3. sec-12 blast radius: every consumer of /etc/verification/env is broken or leaking — OnFailure paging dead on 4 mini units (incl. restic-backup), and llm-triage prints the full Hardcover JWT into the journal on every daily run `known-issue`

**Host:** mini · **Component:** ntfy-notify@.service / /opt/scripts/ntfy-notify.sh · **Auditor:** host:mini · *skeptic-confirmed*

Reproduced live 2026-08-02 06:00:29: ntfy-notify.sh does '. /etc/verification/env' under set -euo pipefail; line 40 of that file is a multi-line Hardcover JWT that executes as a command -> exit 127, so the alert never sends AND the raw JWT is written to the journal (10 occurrences in the last 7 days). Blast radius (grep OnFailure=ntfy-notify@ in /etc/systemd/system): restic-backup.service, lidarr-artist-monitor-reconcile.service, tv-torrent-cleanup.service — all mini OnFailure notifications are silently dropped, meaning a future restic backup failure would page nobody. Root cause is exactly open task sec-12 (malformed multi-line token in mini /etc/verification/env); this finding sizes the consequence. NOT fixed per read-only mandate.

MERGED duplicate from svc:infra-mini (H8): OnFailure ntfy alert path on mini is dead: ntfy-notify.sh exits 127 sourcing /etc/verification/env (JWT on line 40 executes as a command and leaks into the journal) — Reproduced from the journal this session: at 2026-08-02 06:00:29 EDT ntfy-notify@lidarr-artist-monitor-reconcile.service failed with status 127 because ntfy-notify.sh sources /etc/verification/env whose line 40 is a bare multi-line Hardcover JWT — the shell executes the token as a command ('command not found') and the raw JWT is written to the system journal (secret exposure, again). Consequence: every OnFailure= notification on mini that goes through this wrapper silently fails, so unit failures no longer page. The ntfy service itself is healthy (container healthy, vhost 200, anon publish 403, upstream relay pass) — only the publisher wrapper is broken. Fully covered by open task sec-12 (quote the token to one line); NOT fixed per read-only mandate.

MERGED duplicate from flow:monitoring-alerting (H16): All OnFailure ntfy paging on mini is dead: ntfy-notify@ exits 127 sourcing the malformed env file, and leaks the JWT into the journal on every attempt — Reproduced live today: ntfy-notify@lidarr-artist-monitor-reconcile.service.service failed at 06:00:29 EDT with exit 127 because /opt/scripts/ntfy-notify.sh line 18 sources /etc/verification/env, whose line 40 is a multi-line Hardcover JWT that executes as a command — the token also lands in the systemd journal at each failure (secret exposure). 4 units on mini use OnFailure=ntfy-notify@, so ANY of their failures currently produces no page; the failed notify unit also trips systemd-failed-mini daily (noise in the sweep). Fully covered by open task sec-12 (malformed multi-line token in mini /etc/verification/env); NOT fixed per read-only mandate.

MERGED duplicate from repo:verification-suite (H21): Full Hardcover JWT leaks into the mini journal on every daily triage run — llm-triage.sh sources the malformed env file, executing the token line — New consequence for open task sec-12: it is not just interactive sourcing or the ntfy-notify@ OnFailure path — llm-triage.sh line 11 ('set -a && . "$ENV_FILE"') sources /etc/verification/env on every triage run, and line 40 (a bare JWT continuation line) executes as a command, printing the complete token into the journal via 'command not found'. Observed at Aug 01 10:43:22 and Aug 02 10:23:08 — i.e., every daily run with failures re-leaks the credential into journald (persistent, adm-group readable). llm-triage-probe.sh line 14 sources the same file the same way, so the daily e2e probe leaks it too. The sourcing survives because the '.' sits in an && list (errexit-exempt), so triage continues, masking the breakage. Side effect already noted in preflight: ntfy-notify@ units die exit 127 on the same line, so OnFailure notifications on mini are broken. Fully covered by open task sec-12 (quote the token to one line / stop sourcing) — known issue, but the daily-recurrence via the verification cycle raises its urgency. NOT fixed per read-only mandate.

MERGED duplicate from svc:monitoring-stack (M26): OnFailure ntfy notifications on mini are dead: ntfy-notify.sh sources /etc/verification/env and dies exit 127 on the line-40 multi-line JWT (which also leaks into the journal) — Live-confirmed today: ntfy-notify@lidarr-artist-monitor-reconcile.service.service is in failed state; at 06:00:29 EDT its journal shows /etc/verification/env line 40 executing a JWT as a command (exit 127), so the failure page for the lidarr reconcile job never published — any mini unit relying on OnFailure=ntfy-notify@ is silently unpaged, and each attempt re-leaks the token into the journal. Fully covered by open task sec-12 (malformed multi-line token in /etc/verification/env). Note the underlying lidarr-artist-monitor-reconcile failure that triggered it is a separate media-lane item. NOT fixed per read-only mandate.

MERGED duplicate from flow:backups (M51): restic-backup failure alerting via ntfy is dead on mini (ntfy-notify.sh sources the sec-12 malformed env file) — restic-backup.service carries OnFailure=ntfy-notify@%n.service, and /opt/scripts/ntfy-notify.sh does 'set -a; . /etc/verification/env' — the multi-line Hardcover JWT at line 40 of that file executes as a command, so every ntfy-notify@ instantiation on mini exits 127 (proven live today at 06:00 by the failed unit ntfy-notify@lidarr-artist-monitor-reconcile.service, which also leaked the JWT into the journal). Consequence for this lane: if restic-backup fails on mini, no ntfy page fires. Mitigation: the Healthchecks dead-man drop-in still pings (restic-backup-mini up, grace 6h), so a failure is caught within ~6h rather than immediately. Fully covered by open task sec-12; NOT fixed per read-only mandate. MERGED from 5 lane observations (host:mini, svc:infra-mini, flow:monitoring-alerting, flow:backups, repo:verification-suite): the malformed multi-line JWT at /etc/verification/env line 40 (open task sec-12) (a) kills ntfy-notify@ with exit 127 so NO OnFailure alert on mini can send — blast radius restic-backup.service, lidarr-artist-monitor-reconcile.service and 2 more units; (b) leaks the complete raw JWT into journald on EVERY trigger and on EVERY daily llm-triage run (observed Aug 01 10:43, Aug 02 10:23, plus 10 ntfy-notify hits in 7 days). Covered by open task sec-12 — no new task filed, but this materially raises its urgency: the fleet's on-failure paging is dead while the token keeps landing in logs.

<details><summary>Evidence</summary>

```
ssh mini 'grep -rl "OnFailure=ntfy-notify@" /etc/systemd/system/'
/etc/systemd/system/ntfy-notify@.service
/etc/systemd/system/restic-backup.service
/etc/systemd/system/lidarr-artist-monitor-reconcile.service
/etc/systemd/system/tv-torrent-cleanup.service

ssh mini 'sudo journalctl -u ntfy-notify@lidarr-artist-monitor-reconcile.service.service --since "2026-08-02 05:55" --no-pager | tail -5'
Aug 02 06:00:29 macmini ntfy-notify.sh[3761062]: /etc/verification/env: line 40: <REDACTED-JWT>: command not found
Aug 02 06:00:29 macmini systemd[1]: ntfy-notify@lidarr-artist-monitor-reconcile.service.service: Main process exited, code=exited, status=127/n/a
Aug 02 06:00:29 macmini systemd[1]: Failed to start ntfy failure notification for lidarr-artist-monitor-reconcile.service.

ssh mini 'sudo journalctl -p err -S -7days --no-pager | awk ... | sort | uniq -c | sort -rn | head'
     10    macmini systemd[1]: Failed to start ntfy failure notification for lidarr-artist-monitor-reconcile.service.

/opt/scripts/ntfy-notify.sh (read, not run):
set -euo pipefail
set -a
[[ -r /etc/verification/env ]] && . /etc/verification/env
--- (merged lane svc:infra-mini) ---
ssh mini 'journalctl --since "2026-08-02 05:55" --until "2026-08-02 06:10" --no-pager | grep -i ntfy-notify'
Aug 02 06:00:29 macmini ntfy-notify.sh[3761062]: /etc/verification/env: line 40: <REDACTED-JWT>: command not found
Aug 02 06:00:29 macmini systemd[1]: ntfy-notify@lidarr-artist-monitor-reconcile.service.service: Main process exited, code=exited, status=127/n/a
Aug 02 06:00:29 macmini systemd[1]: ntfy-notify@lidarr-artist-monitor-reconcile.service.service: Failed with result 'exit-code'.
ssh mini 'docker ps --format "{{.Names}}\t{{.Status}}" | grep ntfy'
ntfy	Up 3 weeks (healthy)
--- (merged lane flow:monitoring-alerting) ---
ssh mini 'systemctl status "ntfy-notify@lidarr-artist-monitor-reconcile.service.service" --no-pager -n 6'
Active: failed (Result: exit-code) since Sun 2026-08-02 06:00:29 EDT
Process: ExecStart=/opt/scripts/ntfy-notify.sh lidarr-artist-monitor-reconcile.service (code=exited, status=127)
Aug 02 06:00:29 macmini ntfy-notify.sh[3761062]: /etc/verification/env: line 40: <REDACTED-JWT>: command not found

ssh mini 'grep -n "\. /" /opt/scripts/ntfy-notify.sh'
18:[[ -r /etc/verification/env ]] && . /etc/verification/env

ssh mini 'grep -rn OnFailure /etc/systemd/system/*.service | grep -c ntfy-notify'
4
--- (merged lane repo:verification-suite) ---
ssh mini 'journalctl -u verification.service --since "2026-08-01" --no-pager | grep "command not found"'
Aug 01 10:43:22 macmini verify-cycle.sh[1897961]: /etc/verification/env: line 40: <REDACTED-JWT>: command not found
Aug 02 10:23:08 macmini verify-cycle.sh[4189671]: /etc/verification/env: line 40: <REDACTED-JWT>: command not found
# leak vector (repo foss-setup/verification/bin/llm-triage.sh line 11):
[ -r "$ENV_FILE" ] && set -a && . "$ENV_FILE" && set +a
# same pattern in llm-triage-probe.sh line 14:
[ -r "$ENV_FILE" ] && { set -a; . "$ENV_FILE"; set +a; }
# (checks_runner.py itself is unaffected — it parses KEY=VALUE lines without sourcing, load_env_file lines 35-48)
--- (merged lane svc:monitoring-stack) ---
ssh mini 'systemctl --failed --no-legend'
snap-lxd-38800.mount not-found failed
ntfy-notify@lidarr-artist-monitor-reconcile.service.service loaded failed failed
ssh mini 'journalctl -u "ntfy-notify@lidarr-artist-monitor-reconcile.service.service" --since -24h --no-pager | tail -6'
Aug 02 06:00:29 macmini ntfy-notify.sh[3761062]: /etc/verification/env: line 40: <REDACTED-JWT>: command not found
Aug 02 06:00:29 macmini systemd[1]: ntfy-notify@...service: Main process exited, code=exited, status=127/n/a
Aug 02 06:00:29 macmini systemd[1]: Failed to start ntfy failure notification for lidarr-artist-monitor-reconcile.service.
--- (merged lane flow:backups) ---
grep -nE 'OnFailure' foss-setup/scripts/backup/restic-backup.service
19:OnFailure=ntfy-notify@%n.service
head -20 foss-setup/scripts/backup/ntfy-notify.sh
set -a
[[ -r /etc/verification/env ]] && . /etc/verification/env
[[ -r /etc/restic/env ]] && . /etc/restic/env
set +a
Preflight (today): mini failed unit ntfy-notify@lidarr-artist-monitor-reconcile.service exit 127 at 06:00 — /etc/verification/env line 40 JWT executed as a command (<REDACTED-JWT> in journal)
```

</details>

### SH4. Rig dark ~27h (Fri 07-31 11:07 → Sat 08-01 ~14:26 real EDT): operator poweroff via plasma-shutdown; RTC 4h skew falsified the boot time and hid the true outage length

**Host:** rig · **Component:** host-power / 24-7 mandate · **Auditor:** host:rig · **Work item:** `fix-64` · *skeptic-confirmed*

The ~23h dark window (boot -1 ended Fri 2026-07-31 11:07:16, boot 0 began Sat 2026-08-01 10:25:27) was a deliberate poweroff requested from the desktop: systemd-logind logged 'poweroff requested from client PID 2090252 (plasma-shutdown)' at 11:07:11, followed by a full clean shutdown sequence (sessions + Graphical Interface target stopped, docker containers torn down in order). It was NOT a crash and NOT update-driven — pacman.log shows no kernel/nvidia upgrades in the window (only ripgrep on 07-30). However the final journal flush was cut mid-docker-teardown: on the next boot journald renamed both system.journal and user-1000.journal as 'corrupted or uncleanly shut down', so the tail of the shutdown (power-off target) was lost — consistent with a forced power cut late in the shutdown. The host then stayed off ~23h, taking down the AI stack, game servers, and Suwayomi against the 24/7 mandate (suspend is masked but nothing guards/alerts on console poweroff). No open task covers a power-state guard or dead-man alert for the rig host itself.

MERGED duplicate from flow:game-servers (H19): All public game servers were unreachable for ~23h (Fri 07-31 11:07 -> Sat 08-01 10:25 EDT rig power-off) — 24/7 mandate breach — journalctl --list-boots on rig confirms boot -1 ended Fri 2026-07-31 11:07:16 EDT and boot 0 began Sat 2026-08-01 10:25:27 EDT — the host was off ~23.3h. Every friend-facing game endpoint routed through the rig (MC Java 69.9.181.17:1105, Bedrock :1111, Palworld, AMP panel) was necessarily dark that whole window; playit/amp containers show Up 27 hours matching the reboot. All services recovered and pass consumer probes today (this session), so this is a resolved outage, not active. Root-cause of the power-off belongs to the rig-host lane; from the consumer seat this is a user-facing multi-game outage under the 24/7 mandate (suspend is masked — something else took it down). Palworld additionally restarted once post-boot (RestartCount=1, StartedAt 2026-08-01T22:32:42Z) but is healthy now. No open task covers this outage; NOT investigated further per read-only mandate.

MERGED duplicate from svc:infra-mini (M25): Rig was unreachable from mini for ~70 min on Aug 1 13:15-14:25 EDT (3h AFTER its reboot) — 50 proxied 5xx, since recovered — Caddy 24h logs show a tight 5xx cluster on all three rig-backed vhosts: ai.tabaska.us 32x 502 ('dial tcp 192.168.10.12:3000: connect: no route to host'), llm.tabaska.us 4x ('dial tcp 192.168.10.12:4000: i/o timeout'), syncthing-rig.tabaska.us 14x ('dial tcp 192.168.10.12:8384: i/o timeout'), spanning ts 1785604534-1785608731 = 2026-08-01 13:15:34 to 14:25:31 EDT. Notably this window starts ~3h after the rig's boot at Sat 10:25 EDT (following its ~23h powered-off gap already flagged in preflight), i.e. the host went network-unreachable again after coming back. All three vhosts are healthy now (ai.tabaska.us 200 at 13:10 EDT today). Filed as cross-reference for the rig lane investigating the 24/7-mandate violation; no live impact remains. ORCHESTRATOR CORRECTION (gap:rig-relapse-aug1, live-probed): the rig's journal claims boot at 10:25 EDT, but one minute of journal later tailscaled logged 'monitor: time jump detected (slept 4h0m14s)' and NTP stepped the clock to 14:26 — mini's independent Caddy vantage (5xx on rig upstreams until 14:25) confirms the host actually powered on ~14:25 real EDT. The outage was ~27.3h, not 23h, and the separately-observed '70-min relapse 13:15-14:25' was simply the tail of the same outage seen from mini. Post-step catch-up failures fired at 14:26 (playit self-heal unit, immich-ml-window@on).

*Verify note:* CONFIRMED by fresh probes. (1) list-boots reproduces the gap: boot -1 ends Fri 07-31 11:07:16, boot 0 starts Sat 08-01 10:25:27 (~23.3h). (2) Boot -1 journal reproduces logind 'poweroff requested from client PID 2090252 (plasma-shutdown)' at 11:07:11 — deliberate desktop poweroff, not a crash. (3) Boot 0 reproduces journald renaming system.journal + user-1000.journal 'corrupted or uncleanly shut down'. (4) Independent wtmp probe (last -x): NO shutdown record for 07-31 (clean 07-25/07-29 shutdowns have one) — corroborates the teardown being cut before completion; kernel 7.1.3-2-cachyos identical across the outage and pacman 07-28..31 shows only app installs (retroarch/waterfox/go/yay), confirming not update-driven. (5) The 'nothing guards/alerts' claim is stronger than stated: mini verification sweeps run once daily ~10:23-10:26 (triage-2026-07-31.md written 10:26 — 41 min BEFORE the poweroff; no triage-2026-08-01.md), so the entire 23h outage fell inside the between-sweep gap and rig checks are all severity:warn service probes; tasks.json has WoL as recovery-tooling only and no open task for a rig host dead-man (sec-03 dead-man = backup jobs). Severity high stands; mechanism exactly as filed. Suggested fix shape: rig-side heartbeat to Healthchecks (dead-man) + optional logind inhibit/confirm on console poweroff.

<details><summary>Evidence</summary>

```
ssh rig 'journalctl --list-boots | tail -3'
 -1 2d83bae0... Wed 2026-07-29 12:58:12 EDT Fri 2026-07-31 11:07:16 EDT
  0 2fab5bab... Sat 2026-08-01 10:25:27 EDT Sun 2026-08-02 13:07:05 EDT
ssh rig 'journalctl -b -1 --since "2026-07-31 11:06:00" --until "2026-07-31 11:07:12" | grep -iE "poweroff|powering"'
Jul 31 11:07:11 cachyos systemd-logind[822]: poweroff requested from client PID 2090252 ('plasma-shutdown') (unit user@1000.service)...
Jul 31 11:07:11 cachyos systemd-logind[822]: The system will power off now!
Jul 31 11:07:11 cachyos systemd-logind[822]: System is powering down.
ssh rig 'journalctl -k -b 0 | grep journald'
Aug 01 10:25:35 systemd-journald[449]: File /var/log/journal/.../system.journal corrupted or uncleanly shut down, renaming and replacing.
ssh rig 'grep -E "^\[2026-07-(25|29|30|31)" /var/log/pacman.log | grep upgraded'
[2026-07-30T12:47:50-0400] upgraded ripgrep
--- (merged lane flow:game-servers) ---
ssh rig 'journalctl --list-boots --no-pager | tail -3'
 -1 2d83bae0949d4c2692da59557c1d35ec Wed 2026-07-29 12:58:12 EDT Fri 2026-07-31 11:07:16 EDT
  0 2fab5bab51f44e65841987000093325d Sat 2026-08-01 10:25:27 EDT Sun 2026-08-02 13:40:33 EDT
ssh rig 'docker ps -a --format "{{.Names}}\t{{.Status}}" | grep -iE "playit|palworld|amp"'
amp	Up 27 hours
palworld	Up 19 hours (healthy)
playit	Up 27 hours
ssh rig 'docker inspect palworld --format "RestartCount={{.RestartCount}} StartedAt={{.State.StartedAt}}"'
palworld RestartCount=1 StartedAt=2026-08-01T22:32:42.284044791Z
--- (merged lane svc:infra-mini) ---
ssh mini 'docker logs caddy --since 24h 2>&1 | grep -E "\"status\":5.." | grep -o "\"host\":\"[a-z0-9.-]*\"" | sort | uniq -c | sort -rn'
63 manga.tabaska.us / 32 ai.tabaska.us / 14 syncthing-rig.tabaska.us / 4 llm.tabaska.us
sample: {"level":"error","ts":1785608731.578693,"logger":"http.log.error","msg":"dial tcp 192.168.10.12:3000: connect: no route to host",..."host":"ai.tabaska.us","uri":"/api/v1/models/model?id=journaling-coach"..."status":502}
sample: {"ts":1785606199.4740415,"msg":"dial tcp 192.168.10.12:4000: i/o timeout",..."host":"llm.tabaska.us","uri":"/v1/models"...}
date -r 1785604534 => 2026-08-01 13:15:34 EDT ; date -r 1785608731 => 2026-08-01 14:25:31 EDT
curl -s -m 15 -o /dev/null -w "%{http_code}" https://ai.tabaska.us/ => 200 (recovered)
ssh rig 'journalctl -b 0 --no-pager | grep -iE "rtc_cmos|time jump"'
Aug 01 10:25:27 cachyos kernel: rtc_cmos rtc_cmos: setting system clock to 2026-08-01T14:25:26 UTC (1785594326)
Aug 01 14:26:08 cachyos tailscaled[913]: monitor: time jump detected (slept 4h0m14s), probably wake from sleep
Aug 01 14:26:14 cachyos systemd[1]: Failed to start End-to-end Bedrock UDP tunnel probe + playit self-heal (fix-34 M30).
Aug 01 14:26:48 cachyos systemd[1]: Failed to start Immich ML rig-GPU night window (on).
```

</details>

### SH5. Syncthing syncs nothing (0 folders, 0 peers, 0 bytes ever) yet its plaintext-HTTP GUI is reachable from the public internet on betty.bysh.me:12104

**Host:** seedbox · **Component:** syncthing · **Auditor:** host:seedbox · **Work item:** `fix-52` · *skeptic-confirmed*

Observed 2026-08-02 ~19:10 UTC. The seedbox syncthing process (up 3d15h) has zero real folders configured (only the empty defaults stanza), only its own device named in config, peer count 0, and lifetime transfer totals of 0 bytes in/out — pure zero-throughput green (pattern #13); seedbox is not part of the foss-03 mesh (hub NAS/mini/rig). Meanwhile its GUI binds <address>:12104</address> (all interfaces) with tls=false, and HTTP 200 was reproduced from the Mac both via tailnet (100.119.134.94:12104) and via the public hostname betty.bysh.me:12104 — a cleartext admin plane on a 29-user shared host and the open internet. It IS auth-gated (bcrypt user/password, /rest/config returns 403 without the API key), and relaysEnabled=true + globalAnnounceEnabled=true contradict the foss-03 hardening standard applied to the real mesh nodes (relays/global-discovery disabled, GUIs rebound). Either configure it into the mesh or retire it and bind/close the port; NOT fixed per read-only mandate. sec-04 seedbox-harden (gated) is the umbrella but does not enumerate this specific exposure.

*Verify note:* CONFIRMED via 4 fresh probes. (1) Config: single empty defaults folder stanza (id="" path=""), only own device betty.bysh.me, relaysEnabled=true + globalAnnounceEnabled=true, gui tls=false binding :12104 all interfaces, process up 3d16h. (2) Independent API cross-check: /rest/system/connections = 0 peers / 0 inBytesTotal / 0 outBytesTotal lifetime; /rest/config/folders = 0 folders — zero-throughput confirmed at the API layer, not just config grep. (3) Public exposure re-reproduced from Mac: http 200 on both tailnet 100.119.134.94:12104 and public betty.bysh.me:12104, body is genuine Syncthing GUI HTML over plaintext HTTP. (4) Auth gate holds from the public internet (/rest/config and /rest/system/status → 403 without key), but tls=false means any remote GUI login transmits the password in cleartext. Not in known-normal; seedbox is outside the foss-03 mesh. Severity high stands: publicly reachable plaintext admin plane on a 29-user shared host, syncing nothing — either enroll in mesh with hardening (tls, bind localhost/tailnet, relays+global-announce off) or retire and close the port; fold into sec-04 seedbox-harden with this exposure enumerated.

<details><summary>Evidence</summary>

```
ssh seedbox 'grep -c "<folder " ~/.config/syncthing/config.xml; grep -oE "<folder [^>]*" ~/.config/syncthing/config.xml | grep -oE "id=\"[^\"]*\"|path=\"[^\"]*\""; grep -oE "name=\"[^\"]*\"" ~/.config/syncthing/config.xml | sort | uniq -c; grep -oE "<(relaysEnabled|globalAnnounceEnabled)>[^<]*" ~/.config/syncthing/config.xml'
1
id=""
path=""
      1 name="betty.bysh.me"
<globalAnnounceEnabled>true
<relaysEnabled>true
ssh seedbox 'K=$(grep -oE "<apikey>[^<]+" ~/.config/syncthing/config.xml | cut -c9-); curl -s -H "X-API-Key: $K" http://127.0.0.1:12104/rest/system/connections | python3 -c "import json,sys;d=json.load(sys.stdin);print(len(d[\"connections\"]),d[\"total\"][\"inBytesTotal\"],d[\"total\"][\"outBytesTotal\"])"'
peer count: 0  total inBytes: 0 outBytes: 0
ssh seedbox 'sed -n "/<gui/,/<\/gui>/p" ~/.config/syncthing/config.xml'  (apikey/password redacted)
    <gui enabled="true" tls="false" sendBasicAuthPrompt="false">
        <address>:12104</address>
        <user>btabaska</user>
        <password><REDACTED-BCRYPT-HASH></password>
curl -s -m 8 -o /dev/null -w "no-key /rest/config http:%{http_code}\n" http://127.0.0.1:12104/rest/config
no-key /rest/config http:403
curl -s -m 10 -o /dev/null -w "tailnet http:%{http_code}\n" http://100.119.134.94:12104/
tailnet 100.119.134.94:12104 http:200
curl -s -m 10 -o /dev/null -w "public http:%{http_code}\n" http://betty.bysh.me:12104/
public betty.bysh.me:12104 http:200
```

</details>

### SH6. mini cannot reach the IoT VLAN: journaling docker bridge 192.168.16.0/20 swallows 192.168.20.0/24 (net-05 + ha-19 regression)

**Host:** mini · **Component:** docker network journaling_journaling / trusted-to-IoT path · **Auditor:** host:ha · **Work item:** `fix-66` · *skeptic-confirmed*

Today's failing check net-trusted-to-iot-reachable (output 'tok=BAD') is NOT an auth-token failure — 'tok' is just the echo label; the check is a raw TCP probe of the Hue bridge 192.168.20.100:80 from mini. Reproduced live 2026-08-02 ~13:10 EDT: TCP fails and ping is 100% loss from mini, while the Mac reaches the same bridge fine (HTTP 200) and HA is actively controlling Hue lights (state changes at 01:32/02:20/02:42 today). Root cause found on mini: 'ip route get 192.168.20.100' resolves into local docker bridge br-b2bc8abc0ddc — the journaling_journaling network (journal-01..06 stack) has subnet 192.168.16.0/20, which spans 192.168.16.0-192.168.31.255 and blackholes the entire IoT VLAN 192.168.20.0/24 from mini. This is exactly what today's failing sys-docker-subnet-squat check (3 squatters: journaling 192.168.16.0/20, scrutiny-collector 192.168.48.0/20, terraria 192.168.64.0/20) guards against. Regressions of done tasks net-05 and ha-19 (both in reopen-suggestions) — need a new work item to re-home these docker subnets off the 192.168.x space; the check's misleading 'tok=' label is worth renaming in the same pass. NOT fixed per read-only mandate.

*Verify note:* CONFIRMED with fresh probes 2026-08-02. Reproduced: mini TCP/ping to Hue bridge 192.168.20.100 fails (100% loss) while operator Mac gets HTTP 200 + 0% loss from the same bridge, so the IoT VLAN is healthy and the fault is mini-local. Independently tied the route to the cause: ip route get 192.168.20.100 resolves to br-b2bc8abc0ddc src 192.168.16.1, and docker network inspect confirms that bridge id/gateway belongs to journaling_journaling with subnet 192.168.16.0/20 (spans .16.0-.31.255). New probe beyond the auditor's: 192.168.20.1 (IoT gateway) is also unreachable from mini — the entire /24 is blackholed. Check def network.yaml:18-24 confirms 'tok=' is only an echo label on a raw /dev/tcp probe (task net-05); mini last-summary.md shows both net-trusted-to-iot-reachable (tok=BAD) and sys-docker-subnet-squat (3 squatters: journaling 192.168.16.0/20, scrutiny-collector 192.168.48.0/20, terraria 192.168.64.0/20) failing in the latest sweep, matching the net-05 + ha-19 regression claim. Severity high stands: primary docker/automation host has lost the whole trusted-to-IoT path (HA's own Hue control is unaffected, which is why lights still work). Fix direction in the finding is correct: re-home the three docker subnets off 192.168.x (only journaling currently overlaps a deployed VLAN, but all three squat guarded space) and rename the misleading tok= label in the same pass.

<details><summary>Evidence</summary>

```
ssh mini 'timeout 4 bash -c "echo > /dev/tcp/192.168.20.100/80" 2>/dev/null && echo tok=ok || echo tok=BAD; ping -c 2 -W 2 192.168.20.100 | tail -2'
tok=BAD
2 packets transmitted, 0 received, 100% packet loss, time 1022ms

ssh mini 'ip route get 192.168.20.100; docker network ls -q | xargs docker network inspect --format "{{.Name}} {{range .IPAM.Config}}{{.Subnet}} {{end}}" | grep 192.168'
192.168.20.100 dev br-b2bc8abc0ddc src 192.168.16.1 uid 1000
journaling_journaling 192.168.16.0/20
scrutiny-collector_default 192.168.48.0/20
terraria_default 192.168.64.0/20

# same bridge from the operator Mac (bridge itself is UP):
curl -s -m 5 http://192.168.20.100/api/0/config -o /dev/null -w "bridge-http:%{http_code}\n"
bridge-http:200

# check def foss-setup/verification/checks.d/network.yaml (id net-trusted-to-iot-reachable, task net-05):
cmd: timeout 4 bash -c 'echo > /dev/tcp/192.168.20.100/80' 2>/dev/null && echo tok=ok || echo tok=BAD
```

</details>

### SH7. Bazarr has ZERO subtitle providers enabled — 2868 wanted episodes + 27 movies can never be fetched while the sync check stays green (media-12 regression)

**Host:** nas · **Component:** bazarr · **Auditor:** svc:media-aux · **Work item:** `fix-59` · *skeptic-confirmed*

Live API probe (2026-08-02 ~13:20 EDT): /api/system/settings shows enabled_providers=[], /api/providers returns {"data": []}, and episode download history total=0 (no subtitle has ever been downloaded). Meanwhile the wanted backlog is 2868 episodes + 27 movies. The check bazarr-synced-from-arrs passed today (BAZARR_OK movies=283 series=163 sonarr=LIVE radarr=LIVE) but by design only asserts arr sync, and its own comment block states the deploy-time state was 'the sole enabled provider is Podnapisi... proven at deploy time: 27 real candidates returned' (media-12, 2026-07-28) — so the provider has since been removed/lost, a regression of done work media-12. Textbook taxonomy #2 green-but-broken: the consumer end (actually obtaining subtitles) is completely dead. No provider search was triggered (deliberate probe exclusion honored) — this is pure config/history evidence. NOT fixed per read-only mandate (fix = re-enable Podnapisi; the check file also flags adding an OpenSubtitles account as a handoff item).

*Verify note:* CONFIRMED with fresh probes. (1) Re-ran live API with key from mini /etc/verification/env: enabled_providers=[], /api/providers {"data":[]}, episode history total=0, movie history total=0, wanted=2868 episodes + 27 movies — all match the finding. (2) Independent probe the auditor did not run: read Bazarr's persisted config on NAS directly (sudo grep /volume1/docker/bazarr/config/config/config.yaml) — line 74 'enabled_providers: []', so the empty list is on-disk state, not an API quirk. (3) Green-but-broken mechanism verified: results.json (run 2026-08-02T10:23:08-04:00) shows bazarr-synced-from-arrs=pass, and media-subtitles.yaml lines 15-19 confirm Podnapisi was the sole provider proven at media-12 deploy (2026-07-28) with provider auth deliberately unasserted — so this is a genuine regression of done work that monitoring cannot see. Severity high stands (whole subtitle consumer end dead, check stays green). Fix direction in finding is correct: re-enable Podnapisi; optionally add OpenSubtitles account per the check's own handoff note, and consider a rate-limit-safe provider-count assertion (enabled_providers non-empty via /api/system/settings, no search needed) so this regression class alerts.

<details><summary>Evidence</summary>

```
BK=$(ssh mini 'grep -oP "^BAZARR_API_KEY=\K.*" /etc/verification/env')  # value never printed
curl -s -H "X-API-KEY: $BK" 'http://192.168.10.4:6767/api/system/settings' | python3 -c "...print(d['general']['enabled_providers'])"
enabled_providers: []
curl -s -H "X-API-KEY: $BK" 'http://192.168.10.4:6767/api/providers'
{"data": []}
curl -s -H "X-API-KEY: $BK" 'http://192.168.10.4:6767/api/episodes/history?start=0&length=3'
{"data": [], "total": 0}
curl -s -H "X-API-KEY: $BK" 'http://192.168.10.4:6767/api/episodes/wanted?start=0&length=1' -> wanted_episodes_total: 2868
curl ... /api/movies/wanted -> wanted_movies_total: 27
mini /var/lib/verification/results.json (2026-08-02T10:23:08-04:00): bazarr-synced-from-arrs | pass | BAZARR_OK movies=283 series=163 sonarr=LIVE radarr=LIVE
foss-setup/verification/checks.d/media-subtitles.yaml comment: "the sole enabled provider is Podnapisi ... proven at deploy time: 27 real candidates returned for a real movie"
```

</details>

### SH8. Aug 1 daily verification sweep silently died on its 30-min global timeout while rig was down — fleet unaudited for a day, no page from the run itself

**Host:** mini · **Component:** verification.service (daily fleet sweep) · **Auditor:** svc:monitoring-stack · **Work item:** `fix-61` · *skeptic-confirmed*

verification.service (Type=oneshot, TimeoutStartSec=30min, OnFailure= empty) started Aug 1 10:15:18 EDT and was killed at 10:45:18 with result 'timeout' — only 49.7s CPU consumed, i.e. ~29 min spent blocked on per-check timeouts against the powered-off rig (rig was off Jul 31 11:07 → Aug 1 10:25 EDT; the outage itself belongs to the rig lane). Because ExecStartPost pings Healthchecks only on success, no ping was sent, results.json was not updated, and no ntfy summary went out — detection waited 12h until the verification-mini dead-man (timeout 86400 + grace 43200) flipped down at Aug 1 22:26:49 EDT. This is the root cause of today's alert-healthchecks-none-down CRIT at 10:23 (recorded output: down_checks=verification-mini — the check was RIGHT, not broken). Design gap: a single unreachable host aborts the entire fleet sweep with zero partial results and zero direct failure notification (OnFailure is empty, and the mini ntfy-notify@ path is broken anyway per sec-12). Related to done work verify-06/fix-42 (per-check timeouts exist but stack sequentially). NOT fixed per read-only mandate.

MERGED duplicate from repo:verification-suite (H22): Daily sweep killed by 30-min unit timeout on 08-01 mid-triage; dead-man ping skipped, verification-mini dark ~12h, triage lost, no OnFailure alert — On 2026-08-01 the daily sweep started 10:15:18, run-checks completed at 10:43:22 (201/296, 95 failed — rig was powered off, inflating per-check ssh times) and paged '71 NEW failure(s)', but LLM triage pushed the unit past TimeoutStartSec=30min: systemd killed it 10:45:18 ('Failed with result timeout'). ExecStartPost (the verification-mini Healthchecks ping) only fires on ExecStart success, so despite the sweep having executed and written results.json, the dead-man missed its ping and flipped down ~22:26 EDT (period 86400s + grace 43200s), staying down until today's 10:25 ping — which is exactly what today's 10:23 crit alert-healthchecks-none-down caught (down_checks=verification-mini). triage-2026-08-01.md was never written. The unit's own comment claims the dead-man 'flips down only if a sweep never runs' — falsified by this event: the sweep ran, triage overran. verification.service has no OnFailure= (and mini's ntfy-notify@ is broken by the env JWT line regardless), so the unit death itself was silent for ~12h. Worst-case sweep runtime is unbounded (296 checks x 60s default cap) so any one degraded host can reproduce this. NOT fixed per read-only mandate. Regression-adjacent to verify-01/02 and glue-03 (sys-failed-units); the rig 23h power-off that triggered it belongs to another lane.

MERGED duplicate from arch:topology (M74): Daily verification.service died by systemd start-timeout mid-incident (08-01 10:45) — the recovery path exceeds the unit's start window — On 08-01 the daily run detected the rig incident and entered WoL recovery at 10:43, then systemd killed it: 'start operation timed out. Terminating.' at 10:45:18, 'Failed with result timeout', 'Failed to start Homelab continuous verification'. The one run per day that owns triage + self-heal aborted exactly while handling an incident, leaving the daily results incomplete for 08-01. Compounding it, mini's OnFailure notifier is broken independently: ntfy-notify@ units exit 127 because /etc/verification/env line 40 is a multi-line Hardcover JWT executed as a command and leaked into the journal (observed live in the 08-01 10:43:22 entry, redacted here) — that env-file defect is sec-12 (open); the too-small start-timeout for the recovery path is new. Today's 08-02 daily succeeded (10:23), so this is incident-path-only. NOT fixed per read-only mandate.

*Verify note:* CONFIRMED with fresh probes. (1) mini journal: Aug 1 verification.service started 10:15:18, 'Failed with result timeout' 10:45:18 (exactly TimeoutStartSec=30min), only 49.761s CPU consumed — vs Jul 30/31 and Aug 2 runs which all finished normally in ~10-11 min with similar CPU, so the run was wall-clock blocked (~29 min) on the powered-off rig. (2) Unit: Type=oneshot, OnFailure= empty, Healthchecks ping is ExecStartPost (skipped on timeout kill) — no failure notification path exists. (3) Independent Healthchecks API probe: verification-mini pings 07-31T14:26:49Z then NOTHING Aug 1, next 08-02T14:25:01Z; flip up=0 at 08-02T02:26:49Z = Aug 1 22:26:49 EDT, exactly 36h (86400s timeout + 43200s grace) after last ping — dead-man math verified to the second. (4) results.json (2026-08-02T10:23:08-04:00): alert-healthchecks-none-down fail with down_checks=verification-mini — today's CRIT was a correct detection, not a check bug. Timeline, mechanism, and design-gap analysis all accurate; severity high stands (fleet's only daily sweep dies silently with zero partial results and 12h+ detection lag whenever one host is unreachable).

<details><summary>Evidence</summary>

```
ssh mini 'journalctl -u verification.service --since 2026-07-30 --no-pager | grep -E "Starting|Failed|Finished|Consumed"'
Aug 01 10:15:18 macmini systemd[1]: Starting Homelab continuous verification (checks + LLM triage)...
Aug 01 10:45:18 macmini systemd[1]: verification.service: Failed with result 'timeout'.
Aug 01 10:45:18 macmini systemd[1]: verification.service: Consumed 49.761s CPU time.
Aug 02 10:25:01 macmini systemd[1]: Finished Homelab continuous verification (checks + LLM triage).
ssh mini 'systemctl cat verification.service | grep -E "Timeout|OnFailure"; systemctl show verification.service -p OnFailure'
TimeoutStartSec=30min
OnFailure=
curl -s -H "X-Api-Key: $HK" https://health.tabaska.us/api/v3/checks/<uuid>/pings/  (verification-mini)
2026-08-02T14:25:01Z success | 2026-07-31T14:26:49Z success   <-- Aug 1 ping MISSING
flips: 2026-08-02T14:25:01Z up=1 | 2026-08-02T02:26:49Z up=0
results.json alert-healthchecks-none-down output: "down_checks=verification-mini" (status=fail, crit)
--- (merged lane repo:verification-suite) ---
ssh mini 'journalctl -u verification.service --since "2026-07-30" --no-pager | grep -E "Starting|Finished|Failed"'
Aug 01 10:15:18 macmini systemd[1]: Starting Homelab continuous verification (checks + LLM triage)...
Aug 01 10:45:18 macmini systemd[1]: verification.service: Failed with result 'timeout'.
Aug 01 10:45:18 macmini systemd[1]: Failed to start Homelab continuous verification (checks + LLM triage).
Aug 02 10:15:09 macmini systemd[1]: Starting Homelab continuous verification (checks + LLM triage)...
Aug 02 10:25:01 macmini systemd[1]: Finished Homelab continuous verification (checks + LLM triage).
# but the 08-01 sweep DID execute before the kill:
Aug 01 10:43:22 macmini verify-cycle.sh[1845387]: ntfy: sent (Verification: 71 NEW failure(s))
Aug 01 10:43:22 macmini verify-cycle.sh[1845387]: 201/296 passed, 95 failed (8 crit), 6 skipped
# unit: ExecStartPost dead-man + 30min cap, no OnFailure=
ssh mini 'systemctl cat verification.service'
ExecStartPost=/usr/bin/curl -fsS -m 10 --retry 3 -o /dev/null ${VERIFY_DAILY_PING_URL}
TimeoutStartSec=30min
# Healthchecks schedule (why down lasted ~12h): timeout=86400 grace=43200
curl -s -H "X-Api-Key: $HK" https://health.tabaska.us/api/v3/checks/ | python3 …
{'name': 'verification-mini', 'status': 'up', 'last_ping': '2026-08-02T14:25:01+00:00', 'n_pings': 27, 'timeout': 86400, 'grace': 43200}
# today's crit payload confirming detection:
results.json alert-healthchecks-none-down output: down_checks=verification-mini
# triage file gap: ls /var/lib/verification/triage-*.md → ...triage-2026-07-31.md, triage-2026-08-02.md (NO 2026-08-01)
--- (merged lane arch:topology) ---
ssh mini 'sudo journalctl -u verification.service --since "2026-08-01 10:40" --until "2026-08-01 10:50" --no-pager | tail -7'
Aug 01 10:43:22 macmini verify-cycle.sh[1897961]: /etc/verification/env: line 40: <REDACTED-JWT>: command not found
Aug 01 10:43:26 macmini verify-cycle.sh[1897958]: LLM endpoint http://cachyos.tailb31641.ts.net:9292/v1 down — rig should be 24/7, this is an incident; attempting WoL recovery
Aug 01 10:45:18 macmini systemd[1]: verification.service: start operation timed out. Terminating.
Aug 01 10:45:18 macmini systemd[1]: verification.service: Failed with result 'timeout'.
Aug 01 10:45:18 macmini systemd[1]: Failed to start Homelab continuous verification (checks + LLM triage).
```

</details>

### SH9. Sonarr queue wedged unrecoverably: 2 torrents 'Seeding 100%' in deluge but content deleted from seedbox disk (13 of 16 stuck records)

**Host:** seedbox · **Component:** deluge + sonarr import path · **Auditor:** flow:movies-tv · **Work item:** `fix-54` · *skeptic-confirmed*

Better.Off.Ted.S02.REPACK…-NiXON[rartv] (12 episode queue records, age 3.6d) and A.Knight.of.the.Seven.Kingdoms.S01E03…-playWEB (age 3.3d) are 100% 'Seeding' in deluge with save_path=/home/hd34/btabaska/files/tv, but the content does NOT exist there or anywhere under files/ — something deleted the payload under a live torrent. Sonarr polls '/seedbox/tv/<name>' forever getting 'No files found are eligible for import' (unpackerr independently logs 'stat err: no such file or directory' for AKotSK E03). These 13 records are the bulk of sonarr-queue-stuck stuck=16 and can never self-resolve; regression of fix-25 (grabbed-never-imported class) / verify-06. NOT fixed per read-only mandate (needs: remove+blocklist queue items, re-grab; investigate what deleted seeding payloads — reaper/cleanup suspects).

*Verify note:* CONFIRMED with fresh probes. (1) Sonarr queue re-pulled from mini: stuck_warning now 17 (was 16), including exactly 12x Better.Off.Ted.S02.REPACK-NiXON + 1x A.Knight.S01E03, all importPending 'No files found are eligible for import in /seedbox/tv/...'. (2) Fresh deluge RPC (127.0.0.1:3254) shows both torrents 100% Seeding, save_path=/home/hd34/btabaska/files/tv, label=sonarr, ages 3.7d/4.0d, done bytes 12.9GB/2.0GB. (3) Fresh find over /home/hd34/btabaska/files: zero matches for Better.Off.Ted or Squire — payloads deleted under live torrents, mechanism confirmed. (4) Independent corroboration: existing guard ~/scripts/deluge-preimport-stuck.py fires PREIMPORT_STUCK 9 including A.Knight S01E03. Nuances: a spaces-named A.Knight S01E03 variant with label=sonarr-imported exists (episode likely satisfied by another release; its payload is ALSO missing from disk), so unrecoverable loss = the 12 Better.Off.Ted records; 3 live torrents lost payloads at ~3.5-4d age, far under deluge-reaper.py's 14d threshold — reaper misfire or provider-side cleanup is the root-cause lead. Severity high stands (worsening: 16→17 stuck; sonarr-queue-stuck check threshold <=5 badly exceeded).

<details><summary>Evidence</summary>

```
ssh mini '… curl sonarr /api/v3/queue?pageSize=60' → 12x '| completed | importPending | warning | Better.Off.Ted.S02.REPACK… | No files found are eligible for import in /seedbox/tv/Better.Off.Ted…' + 1x A.Knight…S01E03
seedbox deluge RPC (get_torrents_status): sonarr 100.00% Seeding mcp=/home/hd34/btabaska/files/tv sp=/home/hd34/btabaska/files/tv :: Better.Off.Ted.S02.REPACK… ; same for A.Knight…S01E03
ssh seedbox 'ls /home/hd34/btabaska/files/tv/ | grep -iE "better|knight"'
www.UIndex.org - A Knight of the Seven Kingdoms S01E02 … (ONLY the E02 variant; no Better.Off.Ted at all)
ssh seedbox 'ls -la /home/hd34/btabaska/files/tv/Better.Off.Ted*' → (no output / no such dir)
ssh nas 'ls -la /volume1/mounts/seedbox-files/tv/Better.Off.Ted*' → ls: cannot access …: No such file or directory
unpackerr log 13:23:17: A.Knight…S01E03…-playWEB … (stat err: stat /seedbox/tv/A.Knight…: no such file or directory)
```

</details>

### SH10. Lidarr SQLite 'database is locked' storm — 1254 errors in 30h, crash-killing soularr repeatedly and 500ing API endpoints

**Host:** nas · **Component:** lidarr · **Auditor:** flow:music · **Work item:** `fix-55` · *skeptic-confirmed*

Lidarr (Up 2 weeks, v3.1.0.4875) logged 1254 'database is locked' (SQLite code Busy) errors in the last 30h, including on GET /api/v1/history. This is the direct root cause of the soularr-not-crashlooping failure (verify-06 regression, fatal_errors=2): soularr dies with pyarr.exceptions.PyarrServerError 'Internal Server Error: database is locked' → 'Fatal error! Exiting...' at 2026-08-01 20:11, 21:49, 22:37 and 2026-08-02 01:12 EDT, then container-restarts into the next cycle. The lock storm coincides with RSS syncs processing ~1214 releases and likely also contributes to the import failures cycling in fix-40/fix-28 checks. No open task covers Lidarr DB contention — needs a new work item (pattern #3/#7 territory). NOT fixed per read-only mandate.

*Verify note:* CONFIRMED via independent path. Auditor's docker-logs command hangs now (Synology log.db driver), so re-probed Lidarr's own app logs: /volume1/docker/lidarr/config/logs/lidarr.txt has 684 'database is locked' hits, 1958 combined with lidarr.0.txt (Jul 31 19:15→now), latest 2026-08-02 13:42 — minutes before probe, storm ongoing. Soularr chain confirmed and accelerating: soularr.log shows PyarrServerError 'database is locked' → 'Fatal error! Exiting' 7x this morning alone (06:36–08:45 EDT, 12 in current file). soularr-not-crashlooping check (mini results.json, sweep 10:23) counts 'Fatal error' over --since 2h → its 08:23–10:23 window captures exactly the 08:29+08:45 fatals = fatal_errors=2, matching. tasks.json has no open item on Lidarr DB contention (only sec-10/API-keys mentions lidarr). One wording nit: soularr container is 'Up 2 weeks' — the entrypoint loop re-runs the script; the container itself never restarts (immaterial to the check, which greps log fatals). Severity high stands — pipeline actively degraded and fatal rate rising.

<details><summary>Evidence</summary>

```
PW=$(python3 -c "import yaml;print(yaml.safe_load(open('foss-setup/.handoff-secrets.yaml'))['sudo']['nas_password'])")
printf '%s\n' "$PW" | ssh nas 'sudo -S /usr/local/bin/docker logs lidarr --since 30h 2>&1 | grep -ci "database is locked"'
1254
printf '%s\n' "$PW" | ssh nas 'sudo -S /usr/local/bin/docker logs lidarr --since 30h 2>&1 | grep -i -B2 "database is locked" | head -8'
[Info] RssSyncService: RSS Sync Completed. Reports found: 1214, Reports grabbed: 0
[Warn] LidarrErrorPipeline: System.Data.SQLite.SQLiteException: database is locked
[Error] LidarrErrorPipeline: [GET /api/v1/history]
[v3.1.0.4875] code = Busy (5), message = System.Data.SQLite.SQLiteException (0x87AF00AA): database is locked
printf '%s\n' "$PW" | ssh nas 'sudo -S /usr/local/bin/docker logs soularr --since 24h 2>&1 | grep -iE "fatal|PyarrServerError" | head -8'
pyarr.exceptions.PyarrServerError: Internal Server Error: database is locked
[ERROR|soularr|L1432] 2026-08-01T20:11:23-0400: Fatal error! Exiting...
pyarr.exceptions.PyarrServerError: Internal Server Error: database is locked
[ERROR|soularr|L1432] 2026-08-01T21:49:30-0400: Fatal error! Exiting...
pyarr.exceptions.PyarrServerError: Internal Server Error: database is locked
[ERROR|soularr|L1432] 2026-08-01T22:37:26-0400: Fatal error! Exiting...
pyarr.exceptions.PyarrServerError: Internal Server Error: database is locked
[ERROR|soularr|L1432] 2026-08-02T01:12:04-0400: Fatal error! Exiting...
```

</details>

### SH11. Grabbed book 'Adrift - K. T. Konkoly' 100% complete, parked in pre-import label ~306h, absent from Bookshelf AND Calibre — lost import

**Host:** seedbox · **Component:** deluge label=bookshelf -> Bookshelf import · **Auditor:** flow:books · **Work item:** `fix-57` · *skeptic-confirmed*

Live deluge RPC (read-only) on 2026-08-02 shows 'Adrift - K. T. Konkoly.epub' at 100% in the PRE-import label 'bookshelf', completed ~306h ago (~2026-07-20 19:00, Bookshelf migration day bmig-05). Bookshelf has NO record (0 'adrift' books, 0 Konkoly authors, queue empty, 0 history events — total history is only 24 events back to 07-20T19:38), and Calibre metadata.db has no matching title or author, so the book was downloaded but never delivered to the library. Taxonomy #4 grabbed-but-never-imported; only deluge-preimport-stuck (part of today's PREIMPORT_STUCK 17, fix-25 regression) sees it — books-pipeline-lost-imports is structurally blind (compares only Bookshelf records WITH files vs Calibre; a deleted/never-created record vanishes from both sides) and bookshelf-import-deadends has a 48h window + needs a history event. Regression of done work fix-25/fix-47 with a real consumer loss (a requested book never arrived). NOT fixed per read-only mandate — needs manual import into CWA ingest or a deliberate discard+relabel.

*Verify note:* CONFIRMED with 4 fresh probes using an independent mechanism (deluge.ui.client twisted RPC, not the auditor's deluge_client script). (1) Seedbox deluge RPC: 'Adrift - K. T. Konkoly.epub' at 100%, label 'bookshelf' (pre-import), completed ~307h ago, while all 10 same-era peers (Cassiel's Servant, LOTR set, Newsflesh, etc.) sit in 'bookshelf-imported'. (2) Bookshelf API (:8790, key via mini /etc/verification/env BOOKSHELF_API_KEY): queue_total=0; 104 books with 0 'adrift' matches; 10 authors with 0 Konkoly; history totalRecords=24 spanning only 2026-07-20T19:38:54Z to 23:45:15Z with 0 adrift events — so no grab/import event was ever recorded, corroborating the blind-spot claim. (3) NAS Calibre metadata.db (read-only): 81 books, no title LIKE %drift%, no author LIKE %onkoly%. (4) Independent new probe: the payload exists on seedbox disk at /home/hd34/btabaska/files/Adrift - K. T. Konkoly.epub (1,366,330 bytes, mtime Jul 21 01:18) — genuinely downloaded, never delivered, and recoverable by manual import into CWA ingest. Not on the known-normal list. Severity high stands: real consumer loss (requested book never arrived), regression of fix-25/fix-47 with two structurally-blind checks (books-pipeline-lost-imports compares only Bookshelf-records-with-files vs Calibre; bookshelf-import-deadends needs a history event within 48h and there is none).

<details><summary>Evidence</summary>

```
ssh seedbox '~/venvs/deluge/bin/python - <<PYEOF ... client.connect("127.0.0.1",3254,...); get_torrents_status({},[name,label,progress,completed_time]) ...'
BOOK: [bookshelf] 100% done_age_h=306 Adrift - K. T. Konkoly.epub
BOOK: [bookshelf-imported] 100% done_age_h=306 Cassiel's Servant (Jacqueline Carey)   # 10 others correctly relabelled
curl -s -H "X-Api-Key: $BK" 'http://192.168.10.4:8790/api/v1/queue?pageSize=50'   -> queue_total=0
curl -s -H "X-Api-Key: $BK" 'http://192.168.10.4:8790/api/v1/book' | (filter title~adrift)   -> adrift_records=0
curl -s -H "X-Api-Key: $BK" 'http://192.168.10.4:8790/api/v1/author' | (filter konkoly)     -> author_total=10 konkoly_authors=0
curl -s -H "X-Api-Key: $BK" 'http://192.168.10.4:8790/api/v1/history?pageSize=200...'       -> history_pulled=24 oldest=2026-07-20T19:38:54 adrift_history_events=0
ssh nas 'sqlite3 "file:/volume1/books/metadata.db?mode=ro" "select id,title from books where title like \"%Adrift%\" or title like \"%Konkoly%\";"'  -> (empty)
ssh nas 'sqlite3 ... "select name from authors where name like \"%Konkoly%\";"'             -> (empty)
```

</details>

### SH12. Komga Manga library has NEVER been periodically scanned — scheduler fires a stale libraryId, 279 downloaded chapters invisible to readers for 6 days

**Host:** nas · **Component:** komga (Manga library scan scheduler) · **Auditor:** flow:manga-comics · **Work item:** `fix-58` · *skeptic-confirmed*

Komga's LibraryScanScheduler resolves the name 'Manga' but emits ScanLibrary for stale id 0R33RZ4PAF7JC (the pre-read-18 library deleted when the lib was re-homed to /manga); every 6h it logs 'Cannot execute task... Library does not exist' — 28 times in the last 168h, while the real Manga library 0R3629KVZ4AKY (correctly configured scanInterval=EVERY_6H, unavailable=False) got ZERO scans and zero 'Scanning folder: /manga' lines. Result: /volume1/manga holds 155 Spy x Family + 124 My Dress-Up Darling chapters downloaded 2026-07-27 19:50, but Komga's Manga library still shows only Yotsuba&! (1 book, indexed 07-23) — 6 days of content unreadable at the consumer end. The Comics library scans fine every 6h (02:03 + 08:03 today), proving the scanner itself works. This is a regression at the consumer end of done task read-18 (chain Suwayomi->CIFS->/volume1/manga->Komga); checks suwayomi-feeds-komga and komga-libraries-consumer both passed today at 10:23 because they only assert series>=1. Obvious fix (restart Komga to re-register the scheduler, or POST /api/v1/libraries/0R3629KVZ4AKY/scan) NOT applied per read-only mandate.

*Verify note:* CONFIRMED with fresh probes. (1) Fresh docker logs --since 168h: stale id 0R33RZ4PAF7JC x112, real Manga id 0R3629KVZ4AKY x0, 'Library does not exist' x28, 'Scanning folder: /manga' x0 vs 29 total scan-folder lines (all Comics); latest failure today 2026-08-02T08:03:52 immediately after 'Periodic scan for library: Manga' — mechanism (scheduler emits pre-read-18 stale libraryId) reproduced live. (2) Independent Komga API probe: Manga lib 0R3629KVZ4AKY root=/manga EVERY_6H unavailable=False yet totalElements=1 (Yotsuba&! created 07-24), while Comics scans fine (Watchmen indexed 07-27). (3) Filesystem: 155+124 chapters at /volume1/manga (newest cbz 07-27 19:50) plus a third unindexed series (His and Her Circumstances) not in the original finding — gap slightly larger than reported. Severity high stands: 6+ days of consumer-invisible content with checks suwayomi-feeds-komga/komga-libraries-consumer blind (assert only series>=1); those checks should be tightened to assert scan recency or series>1 as part of the fix.

<details><summary>Evidence</summary>

```
$ printf '%s\n' "$PW" | ssh nas 'sudo -S sh -c "/usr/local/bin/docker logs komga --since 168h 2>&1 | grep -iE scan | tail"'  # PW = vault sudo.nas_password
2026-08-02T08:03:49.157-04:00  INFO ... LibraryScanScheduler : Periodic scan for library: Manga
2026-08-02T08:03:49.157-04:00  INFO ... TaskEmitter : Sending task: ScanLibrary(libraryId='0R33RZ4PAF7JC', ...)
2026-08-02T08:03:52.754-04:00  WARN ... TaskHandler : Cannot execute task ScanLibrary(libraryId='0R33RZ4PAF7JC', ...): Library does not exist
$ ...grep -c "ScanLibrary(libraryId=.0R3629KVZ4AKY" -> 0   (real Manga lib id, 168h)
$ ...grep -c "Library does not exist" -> 28
$ ...grep -c "Scanning folder: /manga" -> 0
$ curl -s -u "$KU:$KP" http://192.168.10.4:25600/api/v1/libraries   # vault homepage_widgets.komga_user/pass
Comics | id: 0R33RYW9TF9NX | scanInterval: EVERY_6H | unavailable: False
Manga  | id: 0R3629KVZ4AKY | scanInterval: EVERY_6H | unavailable: False
$ curl -s -u "$KU:$KP" 'http://192.168.10.4:25600/api/v1/series?library_id=0R3629KVZ4AKY&size=20'
total: 1  ->  Yotsuba&! | books: 1 | url: /manga/mangas/MangaDex (EN)/Yotsuba&!
$ ssh nas 'for d in "/volume1/manga/mangas/Weeb Central (EN)"/*/; do echo "$(ls "$d" | wc -l) $d"; done'
124 /volume1/manga/mangas/Weeb Central (EN)/My Dress-Up Darling/
155 /volume1/manga/mangas/Weeb Central (EN)/Spy x Family/
$ ssh nas 'find /volume1/manga -name "*.cbz" -printf "%TY-%Tm-%Td %TH:%TM %p\n" | sort -r | head -1'
2026-07-27 19:50 /volume1/manga/mangas/Weeb Central (EN)/Spy x Family/Unknown_Mission 138.cbz
```

</details>

### SH13. Suwayomi container raced the CIFS mount at 08-01 boot — bind captured empty pre-mount dir, container sees ZERO downloads; new chapter downloads would silently miss the NAS

**Host:** rig · **Component:** suwayomi (docker bind vs mnt-nas\x2dmanga.mount) · **Auditor:** flow:manga-comics · **Work item:** `fix-58` · *skeptic-confirmed*

After the rig's ~23h power-off, boot 0 (08-01) started the suwayomi container at 10:25:47 EDT but mnt-nas-manga.mount only became active at 10:25:52 EDT; with rprivate bind propagation the container captured the empty underlying /mnt/nas-manga directory. Inside the container /home/suwayomi/.local/share/Tachidesk/downloads/ is EMPTY (thumbnails subdir 'No such file or directory') while the host-side mount is healthy and holds mangas/ + thumbnails/. Consequences: all 279 downloaded chapters (DB says Spy x Family 155/155, Dress-Up Darling 124/124) are unservable from Suwayomi; recurring 'FileNotFoundException .../thumbnails/<id>.tmp' for ALL 19 library manga (~60 errors/96h); any new auto/manual download would write into the hidden underlay on the rig root fs — never reaching /volume1/manga or Komga. No data lost yet (container-view dir empty, download queue empty). Check suwayomi-feeds-komga stays green because it probes mount writability from the rig HOST, not the container (pattern #2). Regression of done read-18 hardening (mount is persistent + ordered, but the container has no ordering/guard against starting pre-mount). Obvious fix (restart suwayomi now; add systemd/compose dependency or :rslave propagation) NOT applied per read-only mandate.

*Verify note:* CONFIRMED with fresh probes 2026-08-02. Re-ran core evidence: suwayomi container running since 2026-08-01T14:25:47Z with rprivate binds; mnt-nas\x2dmanga.mount ActiveEnterTimestamp 10:25:52 EDT (5s AFTER container start); container-side downloads/ is empty (total 0, root-owned, Jul 23 mtime = pre-mount underlay) and thumbnails/ ENOENT, while host /mnt/nas-manga has mangas/ + thumbnails/. Independent consumer probes not in auditor evidence: GET :4567/api/v1/manga/39/thumbnail returns HTTP 500; GraphQL manga(id:39) reports downloadCount:0 despite 36 chapters (app believes zero downloads exist); 65 FileNotFoundException .../downloads/thumbnails/*.tmp in the last 24h, still recurring. Mechanism (rprivate bind captured empty pre-mount dir at 08-01 boot; suwayomi-feeds-komga stays green because it probes the host mount, not the container view) verified as stated. Severity high stands: live consumer breakage plus silent-divergence risk for any new download onto the rig root fs. No change to severity.

<details><summary>Evidence</summary>

```
$ ssh rig 'docker inspect suwayomi --format "{{.State.StartedAt}} {{range .Mounts}}{{.Destination}}={{.Propagation}} {{end}}"'
2026-08-01T14:25:47.05502468Z /home/suwayomi/.local/share/Tachidesk=rprivate /home/suwayomi/.local/share/Tachidesk/downloads=rprivate
$ ssh rig 'systemctl show mnt-nas\\x2dmanga.mount -p ActiveEnterTimestamp'
ActiveEnterTimestamp=Sat 2026-08-01 10:25:52 EDT   (container started 10:25:47 EDT — 5s EARLIER)
$ ssh rig 'docker exec suwayomi ls /home/suwayomi/.local/share/Tachidesk/downloads/'
(empty)
$ ssh rig 'docker exec suwayomi ls /home/suwayomi/.local/share/Tachidesk/downloads/thumbnails'
ls: cannot access '...downloads/thumbnails': No such file or directory
$ ssh rig 'ls /mnt/nas-manga/'   # host side, same moment
mangas  thumbnails
$ ssh rig 'docker logs suwayomi --since 96h 2>&1 | grep -oE "thumbnails/[0-9]+\.tmp" | sort | uniq -c' (19 distinct ids, 3-7 each, e.g.)
  5 thumbnails/39.tmp
  7 thumbnails/941.tmp
13:16:55.677 ERROR suwayomi.tachidesk.server.JavalinSetup -- IOException while handling the request
java.io.FileNotFoundException: /home/suwayomi/.local/share/Tachidesk/downloads/thumbnails/39.tmp (No such file or directory)
$ curl -s -X POST http://192.168.10.12:4567/api/graphql -d '{"query":"query{downloadStatus{state queue{state}}}"}'
{"data":{"downloadStatus":{"state":"STOPPED","queue":[]}}}
```

</details>

### SH14. nas-immich-backup-freshness check is dead (find cannot complete even in 140s) — fix-35 regression; actual backup state verified healthy by other means

**Host:** nas · **Component:** verification/nas-immich-backup-freshness · **Auditor:** flow:photos · **Work item:** `fix-62` · *skeptic-confirmed*

Reproduced the 10:23 daily-run TIMEOUT live at ~13:25 EDT: the check's core command (ssh nas find over /volume1/photo/upload + /volume1/photo/library -mtime -7) was killed at 140s (rc=124) run from mini, and a reduced upload-only find plus a trailing ls produced zero output in 90s. The check's 60s budget is structurally insufficient: an unbounded find over a ~4TB photo tree on a NAS currently at 78% iowait. Meanwhile the real state is fine: newest phone-backup asset createdAt 2026-07-29T10:42Z (inside the 7-day window) and the Immich pg dump landed today 02:01. This is a regression of done task fix-35 — the phone-backup dead-man is currently blind, so a real stall would go unnoticed. A cheap alternative probe exists (single-dir ls -lt of /volume1/photo/backups + API createdAfter count) but NOT fixed per read-only mandate.

MERGED duplicate from svc:nas-apps (M11): nas-immich-backup-freshness TIMEOUT is a false negative — the check's find takes 6m55s against a 60s budget; backups ARE landing (fresh file 2026-07-26, newest DB upload 2026-07-29) — Reproduced the check's exact find over /volume1/photo/upload + /volume1/photo/library on 2026-08-02 ~14:12 EDT: it emitted its first -mtime -7 file (library/admin/2026/2026-07-26/IMG_2091.png) only after 6m55.76s wall time, far beyond the check's 60s timeout — hence today's 'TIMEOUT after 60s' (fix-35 regression). The tree is deep/slow to traverse (upload/ subtree alone holds no fresh files and takes minutes; O(1) stat and df on /volume1 are instant, volume healthy at 29% used), so the check design no longer fits the library size. Ground truth from immich_postgres: max(createdAt)=2026-07-29 10:42 UTC — assets landed 4 days ago, within the 7-day freshness window, so the Immich backup path is working. NOT fixed per read-only mandate; the check needs a cheaper freshness probe (e.g. the DB max(createdAt), or find bounded to library/admin/2026/).

MERGED duplicate from repo:verification-suite (M60): nas-immich-backup-freshness times out at 60s on every run — the flagship 'photos actually flowing' signal is dark, state unknown, and cannot distinguish backup-stale from check-broken — The check declares no per-check 'timeout:' override, so it gets the 60s default, but its command chains a 10s Immich statistics curl with an UNBOUNDED 'ssh nas find /volume1/photo/upload /volume1/photo/library -type f -mtime -7' over the whole photo library — on a busy DS920+ that traversal alone exceeds the budget. It exited 124 'TIMEOUT after 60s' in both today's 10:23 daily run and the 13:01 audit sweep (dur 60.1s each). This is the check that fix-35 built specifically after Immich sat green for 14 days around an empty library (H17/H28); in its current state that exact blindness is back: nobody can tell from monitoring whether phone photos are still landing. Taxonomy: the check died, state unknown — a routine-timeout check is broken monitoring, and it also wrongly names fix-35 in reopen-suggestions daily. NOT fixed per read-only mandate (fix: bound the find, e.g. -maxdepth/newest-dir strategy or timeout(1) inside, plus a 'timeout:' override; keep the two signals separable so STALE vs PROBE_DEAD are distinct outputs).

*Verify note:* CONFIRMED with fresh probes. (1) Daily sweep 2026-08-02T10:23 results.json: nas-immich-backup-freshness fail/rc=124 "TIMEOUT after 60s" (severity warn, task_id fix-35; defined at foss-setup/verification/checks.d/nas-services.yaml:215). (2) Fresh re-run of the check's exact find over /volume1/photo/{upload,library} from mini killed at 110s, rc=124, zero output — NAS load 16.17 with IO component 14.94, so the 60s budget is structurally unreachable. (3) Real state independently healthy: Immich API newest asset 2026-07-29T10:42:20Z (inside 7-day window); newest pg dump Aug 2 02:01, and dump freshness has separate passing crit coverage (backup-immich-dump-fresh). Mechanism nuance: the check fails visibly (not silently), but as a permanently-red check it can't distinguish a real phone-backup stall from its own timeout — and per the nas-31 retirement comment (nas-services.yaml:232) it is the ONLY phone-backup-flowing monitor, so the dead-man is effectively blind. Severity high stands.

<details><summary>Evidence</summary>

```
ssh mini 'timeout 140 bash -c "time ssh -o BatchMode=yes -o ConnectTimeout=10 nas \"find /volume1/photo/upload /volume1/photo/library -type f -not -name .immich -mtime -7 2>/dev/null | head -1\""; echo rc=$?'
rc=124
ssh mini 'timeout 90 bash -c "... nas \"find /volume1/photo/upload -type f -mtime -7 | head -3; echo ---; ls /volume1/photo ...\""; echo rc=$?'
rc=124   (no output at all — even the trailing ls never ran)
# real freshness, cheap path:
curl -s -m 30 https://immich.tabaska.us/api/search/metadata -H "x-api-key: $KEY" -d '{"createdAfter":"2026-07-26T00:00:00Z","size":1}'  # KEY = vault immich.verify_api_key
createdAfter=2026-07-26 total=1 newest_createdAt= 2026-07-29T10:42:20.707Z
ssh nas 'ls -lt /volume1/photo/backups | head -3'
-rwxrwxrwx+ 1 root root 256374315 Aug  2 02:01 immich-db-backup-20260802T020000-v3.0.3-pg14.19.sql.gz
-rwxrwxrwx+ 1 root root 256371997 Aug  1 02:01 immich-db-backup-20260801T020000-v3.0.3-pg14.19.sql.gz
--- (merged lane svc:nas-apps) ---
time ssh -o BatchMode=yes nas 'find /volume1/photo/upload /volume1/photo/library -type f -not -name .immich -mtime -7 2>/dev/null | head -1'
/volume1/photo/library/admin/2026/2026-07-26/IMG_2091.png
ssh ... 0.05s user 0.02s system 0% cpu 6:55.76 total

printf '%s\n' "$PW" | ssh nas 'sudo -S /usr/local/bin/docker exec immich_postgres psql -U postgres -d immich -tAc "SELECT max(\"createdAt\") FROM asset"'
2026-07-29 10:42:20.713498+00

ssh nas 'ls -ld /volume1/photo/upload /volume1/photo/library; df -h /volume1 | tail -2'  (instant)
drwxrwxrwx+ 1 root root  24 Jul 22 17:43 /volume1/photo/library
drwxrwxrwx+ 1 root root  86 Jul 22 17:43 /volume1/photo/upload
/dev/mapper/cachedev_2   14T  4.0T   11T  29% /volume1

results.json 2026-08-02T10:23: nas-immich-backup-freshness fail 'TIMEOUT after 60s'
--- (merged lane repo:verification-suite) ---
# results.json 10:23:
==== nas-immich-backup-freshness status=fail exit=124 dur=60.1
TIMEOUT after 60s
# same in the fresh 13:01 audit sweep (fail_both set) — chronic, not transient
# cmd (nas-services.yaml): t=$(curl -sm 10 ... /api/server/statistics ...); f=$(ssh -o BatchMode=yes -o ConnectTimeout=10 nas "find /volume1/photo/upload /volume1/photo/library -type f -not -name .immich -mtime -7 | head -1")
# no timeout: field on this check; runner default CHECK_TIMEOUT=60 (checks_runner.py line 30); grep -rn 'timeout:' checks.d/ shows overrides only in backups(300), journaling(300/90), bug-intake(240), ipod-abs-sync(60)
```

</details>

### SH15. Aug 01 daily verification run timed out (30min cap) during LLM triage, skipping the dead-man ping — this morning's crit was correct self-detection, not a false positive

**Host:** mini · **Component:** verification.service / alert-healthchecks-none-down · **Auditor:** flow:monitoring-alerting · **Work item:** `fix-61` · *skeptic-confirmed*

The 10:23 crit alert-healthchecks-none-down (task sec-03) and the Healthchecks API (16/16 up) are BOTH right, 2 minutes apart: recorded check output at 10:23:08 was 'down_checks=verification-mini', and the dead-man recovered at 10:25:01 EDT when today's run pinged. Root cause: the Aug 01 daily run produced 95 failed / 8 crit (rig had just rebooted from its 23h outage) and verification.service hit TimeoutStartSec=30min during llm-triage at 10:45:18, so the ExecStartPost dead-man ping never fired; Healthchecks flipped verification-mini down at 2026-08-02T02:26:49Z (36h after the last good ping on Jul 31). Design weakness: sweep+triage duration scales with fleet failure count, so the daily run is most likely to overrun its timeout exactly when the fleet is at its worst — a regression-class risk against verify-06 runner-health work. The '18 objects imported automatically' first line is only Django 5.2's shell auto-import banner (runner matches with re.search re.M — harmless noise). NOT fixed per read-only mandate (obvious fixes: raise TimeoutStartSec or bound triage time; silence the Django banner with shell -v 0 or a plain script).

*Verify note:* CONFIRMED with fresh probes. (1) mini journal: Aug 01 10:43:22 '201/296 passed, 95 failed (8 crit)' then 10:45:18 'Failed with result timeout' — exactly 30min after ~10:15 start and ~2min after checks finished, i.e. during LLM triage. (2) results.json (run_ts 2026-08-02T10:23:08-04:00): alert-healthchecks-none-down fail with output 'down_checks=verification-mini' plus the Django 5.2 shell banner, verbatim. (3) Independent Healthchecks API probe: verification-mini flips down 2026-08-02T02:26:49Z, up 2026-08-02T14:25:01Z (=10:25:01 EDT, second-exact match to journal 'Deactivated successfully'); now 16/16 up, none down — so the 10:23 crit and the 10:25 all-up are BOTH correct as claimed. (4) Deployed and repo unit both have ExecStartPost dead-man curl + TimeoutStartSec=30min; systemd skips ExecStartPost on start timeout, so the missed ping mechanism is real. Scaling mechanism corroborated: Aug 02 run with 29 failures finished in ~10min vs Aug 01's 95-failure run overrunning 30min. Severity high stands — the runner most likely misses its own dead-man precisely when the fleet is worst (regression risk vs verify-06).

<details><summary>Evidence</summary>

```
ssh mini 'journalctl -u verification.service --since 2026-07-30 --no-pager | grep -iE "Started|Failed|Deactivated"'
Aug 01 10:45:18 macmini systemd[1]: verification.service: Failed with result 'timeout'.
Aug 01 10:45:18 macmini systemd[1]: Failed to start Homelab continuous verification (checks + LLM triage).
Aug 02 10:25:01 macmini systemd[1]: verification.service: Deactivated successfully.
(journal also: Aug 01 10:43:22 verify-cycle.sh: 201/296 passed, 95 failed (8 crit))

mini /var/lib/verification/results.json (run_ts 2026-08-02T10:23:08-04:00):
 "id": "alert-healthchecks-none-down", "status": "fail",
 "output": "18 objects imported automatically (use -v 2 for details).\n\ndown_checks=verification-mini"

curl -s -H "X-Api-Key: $HK" https://health.tabaska.us/api/v3/checks/<uuid-of-verification-mini>/flips/
{"timestamp": "2026-08-02T14:25:01+00:00", "up": 1},
{"timestamp": "2026-08-02T02:26:49+00:00", "up": 0}

foss-setup/verification/systemd/verification.service:
ExecStartPost=/usr/bin/curl -fsS -m 10 --retry 3 -o /dev/null ${VERIFY_DAILY_PING_URL}
TimeoutStartSec=30min
```

</details>

### SH16. local-ai-tooling Forgejo remote is 16 commits behind HEAD/GitHub — ai-03 dual-remote regression

**Host:** rig · **Component:** local-ai-tooling (Forgejo home/local-ai-tooling) · **Auditor:** flow:git-control-plane · **Work item:** `fix-65` · *skeptic-confirmed*

Verified live 2026-08-02 ~13:05 EDT: /home/btabaska/Documents/GitHub/local-ai-tooling HEAD=9a11062 equals origin/main (GitHub current), but forgejo/main=b24ca1d after a fresh fetch — exactly 16 commits behind, 0 commits diverged (pure fast-forward). The missing commits are the entire ai-10 body of work (swarm orchestration tiers, prefix-cache probe, LLM knowledge base, deterministic verification loop). Working tree is clean, so this is purely an un-pushed mirror. This is a regression of ai-03 (dual-remote push-BOTH discipline, memorialized 2026-07-29); the tripwire ai-tooling-clean-pushed caught it correctly in today's 10:23 run. Consequence: the no-cloud Forgejo copy used for rebuild would silently lose all ai-10 work. NOT fixed (no push executed) per read-only mandate; the fix is a single fast-forward push via id_forgejo.

MERGED duplicate from repo:live-drift (H20): local-ai-tooling Forgejo remote strictly 16 commits behind origin — regression of ai-03 dual-remote mandate — Verified live 2026-08-02 ~13:45 EDT: the rig checkout ~/Documents/GitHub/local-ai-tooling is clean (porcelain 0) at HEAD 9a11062 which matches origin (GitHub), but the forgejo remote main is b24ca1d, a strict ancestor 16 commits behind — pushes have been going to GitHub only. This regresses ai-03 (dual-remote fidelity: push BOTH remotes via id_forgejo); a rebuild from the self-hosted Forgejo copy would lose 16 commits of AI-stack tooling, defeating the no-cloud mandate. The ai-tooling-clean-pushed tripwire is correctly failing in today's 10:23 daily run (warn, task ai-03). NOT fixed per read-only mandate — remediation is a git push forgejo main from the rig, needs a new work item per the regression-set rule.

MERGED duplicate from svc:infra-mini (M24): ai-03 regression measured: Forgejo remote is 16 commits behind origin — all ai-10 swarm/orca work exists only on GitHub — This morning's check ai-tooling-clean-pushed warned head=9a11062 origin=9a11062 forgejo=b24ca1d. Measured live on rig: forgejo (b24ca1d) is exactly 16 commits behind local HEAD/origin (9a1106274059), spanning the entire ai-10 tier-5 swarm-orchestration arc plus docs commits. Working tree is clean, so this is purely a missed 'push both remotes' from ai-03's dual-remote mandate — the no-cloud Forgejo copy would lose 16 commits if GitHub disappeared. Regression of done task ai-03; needs a new work item. NOT fixed per read-only mandate (fix = git push forgejo main from rig with id_forgejo).

*Verify note:* CONFIRMED with fresh probes (2026-08-02 ~13:3x EDT). Independent check: `git ls-remote` from rig (no local ref writes, does not rely on the auditor's fetch) shows Forgejo home/local-ai-tooling main = b24ca1d while GitHub origin main = 9a11062 = local HEAD. Gap re-counted live: exactly 16 commits ahead of forgejo/main, 0 behind; `git merge-base --is-ancestor b24ca1d 9a11062` succeeds, so it is a pure fast-forward — the missing range is the ai-10 work (swarm tiers, swarm.py deletion, etc.). Working tree clean (porcelain empty), so purely an un-pushed mirror, a regression of the ai-03 push-BOTH discipline. Corroborated by the tripwire: ai-tooling-clean-pushed = fail in both the 10:23 daily run (/var/lib/verification/results.json) and the 13:01 audit-safe sweep (/tmp/verify-audit/sweep-run.json). Not on the known-normal list. Severity high stands: the Forgejo copy is the designated no-cloud rebuild source and would silently omit all ai-10 work; fix remains a single fast-forward push via id_forgejo (not executed, read-only sweep).

<details><summary>Evidence</summary>

```
ssh rig 'cd /home/btabaska/Documents/GitHub/local-ai-tooling && git fetch forgejo; git fetch origin; git rev-parse HEAD forgejo/main origin/main; git rev-list --count forgejo/main..HEAD; git rev-list --count HEAD..forgejo/main; git status --porcelain'
9a11062740590e0567db672537cb1d7ffd80c960   (HEAD)
b24ca1dfc2f540485558d12240b0b42308c0b9a7   (forgejo/main)
9a11062740590e0567db672537cb1d7ffd80c960   (origin/main)
16
0
(status empty)
git log --oneline forgejo/main..HEAD | head -6
9a11062 Merge branch 'btabaska/research-local-llm-tooling' into main
33a0758 ai-10: delete swarm.py, use Orca's native orchestration instead
779221c Merge branch 'btabaska/research-local-llm-tooling' into main
f0eb8ce ai-10: tier 5 — swarm orchestration layer (task DAG, collision proof, claims)
bedc0b9 Merge branch 'btabaska/research-local-llm-tooling' into main
3c56ba9 ai-10: reasoning OFF on the swarm profile (+ matching instruct sampler)
--- (merged lane repo:live-drift) ---
ssh rig 'git -C ~/Documents/GitHub/local-ai-tooling status --porcelain | wc -l; git -C ~/Documents/GitHub/local-ai-tooling rev-parse HEAD; git ls-remote origin main | cut -f1; git ls-remote forgejo main | cut -f1'
0
9a11062740590e0567db672537cb1d7ffd80c960
9a11062740590e0567db672537cb1d7ffd80c960
b24ca1dfc2f540485558d12240b0b42308c0b9a7
ssh rig 'git -C ~/Documents/GitHub/local-ai-tooling merge-base --is-ancestor b24ca1d... 9a11062... && echo forgejo-is-strictly-behind; git rev-list --count b24ca1d...9a11062...'
forgejo-is-strictly-behind
16
(daily run 10:23: ai-tooling-clean-pushed FAIL: head=9a11062 origin=9a11062 forgejo=b24ca1d)
--- (merged lane svc:infra-mini) ---
ssh rig 'cd ~/Documents/GitHub/local-ai-tooling && git rev-parse HEAD | cut -c1-12 && git log --oneline b24ca1d..9a11062 | wc -l && git status --porcelain | wc -l'
9a1106274059
16
0
git log --oneline b24ca1d..9a11062 | head -4
9a11062 Merge branch 'btabaska/research-local-llm-tooling' into main
33a0758 ai-10: delete swarm.py, use Orca's native orchestration instead
779221c Merge branch 'btabaska/research-local-llm-tooling' into main
f0eb8ce ai-10: tier 5 — swarm orchestration layer (task DAG, collision proof, claims)
```

</details>

### SH17. LLM auto-triage 91% nonfunctional (68/75 verdicts are malformed-JSON fallbacks) while its dedicated e2e guard check passes — green-but-broken inside the verification suite itself

**Host:** mini · **Component:** llm_triage.py / llm-triage-probe.sh (verify-04, fix-30) · **Auditor:** repo:verification-suite · **Work item:** `fix-61` · *skeptic-confirmed*

Over the last 5 daily runs (07-28..08-02), 68 of 75 triage verdicts were the hardcoded fallback {'confidence': 0.0, 'escalate': true, 'diagnosis': 'triage failed — model did not return valid JSON'} (llm_triage.py lines 103-107), with likely_cause 'no JSON object in response'. Meanwhile llm-triage-completion-e2e (fix-30's guard against exactly this class) passed today. Cause of divergence: the probe (llm-triage-probe.sh) sends a trivial one-line prompt ('Reply with {"ok":true}') with max_tokens=600 and only requires non-empty content; real triage sends a full skill-prompt + failed-check JSON to qwen3.6-35b-a3b, whose reasoning consumes the 600-token budget before emitting the JSON object — the documented reasoning-model trap at realistic prompt size, which the probe was built to catch but structurally cannot. Net effect: the triage subsystem burns ~30 rig completions per day producing near-zero signal, and 13 of today's 15 verdicts were noise. This is failure-pattern #2 (liveness masking) recurring inside the monitoring layer; regression of verify-04/fix-30 intent. NOT fixed per read-only mandate.

MERGED duplicate from repo:verification-suite (L43): Triage's 15-verdict cap takes the first 15 failures in file order, not crit-first — today's only failing crit got no LLM verdict while a known false positive consumed a slot — llm_triage.py line 118 slices failed[:MAX_CHECKS] in checks.d alphabetical order with no severity sort. Today 29 checks failed: the 15 triaged were simply the first 15 by file order, so nas-secret-file-perms (crit, fix-23) and 13 other failures (media-arr-file-quality, sonarr/radarr-queue-stuck, deluge-preimport-stuck, stash-serving, nas-immich-backup-freshness, etc.) received no verdict, while the structurally-false-positive spent-enabled-timers occupied a slot (and got the LLM's most confident verdict of the day: escalate=False 0.9). Low impact today only because triage output is currently ~91% fallback garbage anyway (separate finding), but once triage is repaired this ordering bug will systematically starve crits in high-failure runs — which are exactly the runs where triage matters. NOT fixed per read-only mandate (fix: sort failed by severity crit-first before slicing).

*Verify note:* CONFIRMED with fresh probes. (1) journalctl reproduces 75 verdicts over the 5 runs Jul28-Aug02 with 68 confidence=0.0 fallbacks (13/14/15/13/13) — 91% exactly as claimed. (2) triage-2026-08-02.md: 13x confidence 0.0 vs 2x 0.9; all fallbacks show likely_cause 'malformed JSON (attempt 2): no JSON object in response' (em-dash stored JSON-escaped —); zero 'LLM request failed' entries in last two runs, so the endpoint is up and the failure is content-level, consistent with reasoning-token exhaustion, not an outage. (3) Guard llm-triage-completion-e2e passes in both results.json (10:23) and audit sweep-run.json (13:01) — green-but-broken confirmed. (4) Mechanism verified from source: deployed scripts md5-identical to repo; probe sends trivial 'Reply with {"ok":true}' at max_tokens=600 asserting only non-empty content, real triage sends full skill prompt at the same max_tokens=600; llm_triage.py lines 103-107 emit the observed hardcoded fallback; probe's own line-9 comment documents the <think>-budget trap it structurally cannot exercise at realistic prompt size. Not known-normal. Severity high stands (monitoring-layer regression of verify-04/fix-30, ~13 noise escalations/day, ~30 wasted rig completions/day, no direct user-facing outage). Fix direction: raise max_tokens for triage (and probe with a realistic-size prompt), or strip/allow reasoning before JSON extraction.

<details><summary>Evidence</summary>

```
ssh mini 'journalctl -u verification.service --since "2026-07-28" --no-pager | grep -E "wrote [0-9]+ verdicts"'
Jul 28: wrote 15 verdicts (14 escalations); Jul 29: 15 (14); Jul 30: 15 (15); Jul 31: 15 (13); Aug 02: 15 (13)
ssh mini 'journalctl -u verification.service --since "2026-07-28" --no-pager | grep "confidence=0.0" | awk "{print \$1, \$2}" | uniq -c'
13 Jul 28 / 14 Jul 29 / 15 Jul 30 / 13 Jul 31 / 13 Aug 02   (= 68/75 fallbacks)
# sample verdict from /var/lib/verification/triage-2026-08-02.md:
### alert-healthchecks-none-down (sev crit, ... attempts 2)
"diagnosis": "triage failed — model did not return valid JSON",
"likely_cause": "malformed JSON (attempt 2): no JSON object in response",
# yet the guard passes: llm-triage-completion-e2e absent from today's 29 fails (results.json 10:23 + sweep-run.json 13:01)
# probe asks a trivial question (llm-triage-probe.sh line 21):
{"model":"$MODEL","messages":[{"role":"user","content":"Reply with the JSON object {\"ok\":true} and nothing else."}],"temperature":0,"max_tokens":600}
# real triage: system=skills/*.md (full prompt) + check JSON, max_tokens=600 (llm_triage.py lines 52-58)
--- (merged lane repo:verification-suite) ---
# llm_triage.py: MAX_CHECKS = int(os.environ.get("TRIAGE_MAX_CHECKS", "15")) (line 30); failed = failed[:MAX_CHECKS] (line 118) — no sort
# journal 2026-08-02 10:25:01 — the 15 triaged ids (file-order): alert-healthchecks-none-down, ansible-site-converged-mini, soularr-not-crashlooping, systemd-failed-mini, edge-plex-version-current, wiki-drift, ai-tooling-clean-pushed, spent-enabled-timers, stacks-orphan-dirs, kometa-run-clean, pinchflat-stuck-media, bitmagnet-torznab-via-prowlarr, plex-unmatched-items, lidarr-incomplete-albums, navidrome-library-present
# NOT triaged despite failing: nas-secret-file-perms (CRIT) + 13 warns
Aug 02 10:25:01 verify-cycle.sh[4189668]: wrote 15 verdicts (13 escalations) — vs 29 failed in results.json
```

</details>

### SH18. Regression ledger: 20 done tasks have 29 failing checks; tracker still shows all of them closed with zero formal reopens

**Host:** repo · **Component:** docs/progress.json + /var/lib/verification/reopen-suggestions.json · **Auditor:** repo:tracker-wiki · **Work item:** `fix-68` · *skeptic-confirmed*

The 2026-08-02 10:23 EDT daily run's reopen-suggestions.json names 22 task_ids with failing checks; 20 of them are genuinely marked done in progress.json (dates 2026-07-17..07-29), the other two are mis-included (see the separate ledger-hygiene finding). progress.json's 'reopened' array is EMPTY and acks.json is empty, so the tracker asserts all 20 closed with no annotation — confirming the 'tracker checkmarks are not trustworthy' mandate. Worst clusters: fix-28 (navidrome-library-present PRESENT_DEGRADED missing=3495/3495 — the ENTIRE music library — plus plex-unmatched-items and lidarr-incomplete-albums), fix-23 (nas-secret-file-perms CRIT + nas-worldwritable-sweep=5), sec-03 (alert-healthchecks-none-down CRIT — the alerting layer itself), and fix-25/fix-27 (deluge-preimport-stuck=17 + media-arr-file-quality WATCHABLE_BAD=3 — the grabbed-never-imported class reopened). Full regressed set: ai-03, fix-23, fix-24, fix-25, fix-27, fix-28, fix-35, fix-37, fix-38, fix-39, fix-40, fix-42, fix-43, fix-45, glue-03, nas-01, net-05, sec-03, seed-12, wiki-05. These need new work items; NOT fixed per read-only mandate.

*Verify note:* CONFIRMED with fresh probes. Re-read reopen-suggestions.json (generated 2026-08-02T10:23:08-04:00): exactly 22 task_ids, 29 failed_checks. Fresh progress.json parse: 20/22 genuinely done (ha-19 and verify-06 are the two not-done mis-inclusions, as the finding already caveats), reopened=[] and acks.json={}. Same-timestamp results.json shows all headline checks fail with the exact claimed outputs. Independent live probes: (1) navidrome sqlite fresh query returns 3495|3495 media_file/missing — the whole-library grey-out is CURRENT, not stale; (2) Healthchecks API now reports 0 checks down — the sec-03 crit fired on down_checks=verification-mini (the runner's own dead-man) at 10:23 and has since transiently recovered, so that one member of the 29 is intermittent, but the ledger claim (20 done tasks with failing checks, zero formal reopens/acks) is unaffected. Severity high stands: tracker-integrity gap spanning 2 crits plus a live entire-library regression.

<details><summary>Evidence</summary>

```
ssh mini 'cat /var/lib/verification/reopen-suggestions.json' | python3 -m json.tool
"generated": "2026-08-02T10:23:08-04:00"
"task_ids": ["ai-03","fix-23","fix-24","fix-25","fix-27","fix-28","fix-35","fix-37","fix-38","fix-39","fix-40","fix-42","fix-43","fix-45","glue-03","ha-19","nas-01","net-05","sec-03","seed-12","verify-06","wiki-05"]
failed_checks incl: alert-healthchecks-none-down(sec-03,crit), nas-secret-file-perms(fix-23,crit), navidrome-library-present(fix-28), deluge-preimport-stuck(fix-25), media-arr-file-quality(fix-27) — 29 checks total

python3 - # cross-ref progress.json done dict
fix-23: 2026-07-17: secrets & perms hygiene — health.env root:root 600 + leaked admin ntfy token r
fix-25: 2026-07-17: silent grabbed-never-imported class closed — H3: 3 movies re-grabbed+tracked;
fix-28: 2026-07-17: Plex/Navidrome library correctness. M32: 9 junk-titled bulk-scan movies Fix-Ma
sec-03: True  glue-03: True  nas-01: True  net-05: True  wiki-05: True
progress.json top-level keys: ['_meta','done','reopened','retired','deferred']
reopened len 0
```

</details>

### SH19. Entire alerting/observability plane co-located on mini with edge TLS, DNS and deploy remote — mini down means no alert can report it

**Host:** mini · **Component:** alerting-plane (ntfy + Healthchecks + Uptime Kuma + verification runner + Caddy + Forgejo) · **Auditor:** arch:topology · **Work item:** `fix-63` · *skeptic-confirmed*

Verified live 2026-08-02 ~13:40 EDT: the ntfy server, Healthchecks server, Uptime Kuma, and all three verification tiers (fast/quick/daily systemd timers) run on mini, alongside Caddy (62 vhost site blocks, sole TLS edge), AdGuard primary DNS, and the Forgejo deploy remote. Every notification path terminates on mini — Healthchecks pages route through mini's own ntfy (the 'verification-mini is UP' page appears in mini's local ntfy cache). If mini loses power/disk, all 62 https vhosts, the runner, both dead-man systems and the pager die simultaneously; there is no off-host or external dead-man that would fire. DNS alone has a fallback (NAS AdGuard answers, see separate finding). No open task covers moving any alerting component off-host or adding an external heartbeat (e.g. a free-tier hosted Healthchecks check pinged BY mini). NOT fixed per read-only mandate.

*Verify note:* CONFIRMED with fresh probes. (1) Re-ran docker ps on mini: ntfy, healthchecks+db, uptime-kuma, caddy (sole 80/443), adguardhome (:53), forgejo all Up on mini; (2) all three verification timers (fast/quick/daily) confirmed on mini only. Independent probes strengthen the claim: (3) Healthchecks /api/v3/channels/ shows EXACTLY ONE notification channel — 'ntfy (self-hosted)' on mini itself; no email/external integration exists, so a mini outage silences alerting by configuration, not just co-location; (4) rig and NAS container lists have zero ntfy/healthchecks/uptime-kuma instances — no off-host alerting component in the fleet; (5) tasks.json keyword scan confirms no open task covers off-host alerting or an external heartbeat (sec-03 dead-man is itself hosted on mini; ha-17 is LiteLLM, unrelated). Severity high stands — architecture SPOF where no alert can report mini's own death, in a fleet with a 100%-monitoring mandate. Cheapest remediation path noted by auditor (external hosted dead-man pinged BY mini, e.g. free-tier healthchecks.io cron ping) remains uncovered by any task.

<details><summary>Evidence</summary>

```
ssh mini 'docker ps --format "{{.Names}}\t{{.Status}}\t{{.Ports}}"' | egrep 'caddy|adguard|ntfy|healthchecks|uptime-kuma|forgejo'
adguardhome  Up 12 days  0.0.0.0:53->53/tcp, 0.0.0.0:853->853/tcp ...
caddy        Up 6 days   0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
forgejo      Up 4 days (healthy)  0.0.0.0:2222->22/tcp, 0.0.0.0:3030->3000/tcp
healthchecks Up 3 weeks (healthy) 0.0.0.0:8001->8000/tcp
ntfy         Up 3 weeks (healthy) 0.0.0.0:8080->80/tcp
uptime-kuma  Up 5 days (healthy)  0.0.0.0:3001->3001/tcp
ssh mini 'systemctl list-timers --all --no-pager | grep verif'
verification-fast.timer  NEXT Sun 2026-08-02 13:45:04 EDT
verification-quick.timer NEXT Sun 2026-08-02 14:40:02 EDT
verification.timer       NEXT Mon 2026-08-03 10:15:47 EDT
ssh mini 'sudo grep -E "^[a-zA-Z0-9*.\{\}\$_-]+ \{" /opt/stacks/caddy/caddy/Caddyfile | grep -v "^(" | wc -l'
62
ntfy cache (on mini) shows Healthchecks' own pages routed through it:
2026-08-02T10:25:03 healthchecks | verification-mini is UP | Project: Homelab ...
```

</details>


---

## MEDIUM (58)

### SM1. immich_server ffmpeg segfaults every night at 00:00 on the same asset, dumping a 23MB core to /volume1 root (fix-45 regression)

**Host:** nas · **Component:** immich_server / jellyfin-ffmpeg · **Auditor:** host:nas · **Work item:** `fix-60`

The nas-core-dumps check (task fix-45) failure is caused by immich_server (container 45d2bac8) whose bundled /usr/lib/jellyfin-ffmpeg/ffmpeg dumps core on signal 11 at 00:00 EDT every night — observed 5 consecutive nights (Jul 29, 30, 31, Aug 1, Aug 2) in /var/log/messages. Every crash is on the identical preview-generation command for asset /data/library/admin/2021/2021-06-28/IMG_3674.mov (likely a corrupt/edge-case .mov); the nightly job retries forever and never succeeds (failure patterns #3 + #6). Each night overwrites /volume1/@ffmpeg...core.gz (~23MB), so the check re-fails daily and that asset's video preview is never generated. Regression of done task fix-45 — needs a new work item (skip/quarantine the asset or fix the source file). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
PW=$(python3 -c "import yaml;print(yaml.safe_load(open('foss-setup/.handoff-secrets.yaml'))['sudo']['nas_password'])")
printf '%s\n' "$PW" | ssh nas 'sudo -S sh -c "ls -la /volume1/ | grep core; grep -iE \"segfault|core|ffmpeg\" /var/log/messages | tail -15" 2>/dev/null'
-rw------- 1 root root 23255589 Aug  2 00:00 @ffmpeg.synology_geminilake_920+.72806.45d2bac8daed7bc273b669e02f6fe6988ec1d1ff64e7d8e9ba88598fd0ce0c2a.core.gz
2026-07-29T00:00:21-04:00 TabaskaNAS coredump[3763]: Process ffmpeg[2676](/usr/lib/jellyfin-ffmpeg/ffmpeg) dumped core on signal [11]. Core file [/volume1/@ffmpeg...core.gz]. Cmdline [/usr/bin/ffmpeg -skip_frame nointra ... -i /data/library/admin/2021/2021-06-28/IMG_3674.mov ... /data/thumbs/936853a2-657c-4796-a90e-2adc27df16d1/8a/5d/8a5d0a66-9ee4-47d3-a058-c80eea7d53ba_preview.jpeg ]
2026-07-30T00:00:13-04:00 ... same cmdline, same input IMG_3674.mov
2026-07-31T00:00:17-04:00 ... same
2026-08-01T00:00:11-04:00 ... same
2026-08-02T00:00:10-04:00 ... same
printf '%s\n' "$PW" | ssh nas 'sudo -S /usr/local/bin/docker ps --no-trunc --format "{{.ID}} {{.Names}}" 2>/dev/null' | grep 45d2bac8
45d2bac8daed7bc273b669e02f6fe6988ec1d1ff64e7d8e9ba88598fd0ce0c2a immich_server
```

</details>

### SM2. nas-secret-file-perms crit failure = mylar3 config.ini mode 0644 with 23 credential-class keys (fix-23 regression via Jul 27 mylar3 deploy)

**Host:** nas · **Component:** /volume1/docker/mylar3/config/mylar/config.ini · **Auditor:** host:nas · **Work item:** `fix-53`

Re-ran the nas-secret-file-perms check cmd (foss-setup/verification/checks.d/secrets.yaml, severity crit, task fix-23) read-only: exactly one offender, /volume1/docker/mylar3/config/mylar/config.ini, mode -rw-r--r-- (0644) btabaska:users, rewritten by the app as recently as Aug 2 10:53 so a one-off chmod will be reverted — the app's umask needs addressing. The file contains 23 credential-class key names (api_key, sab_apikey, torznab_apikey, http_password, deluge_password, etc.); nuance: a value-requiring grep matched zero lines, so these fields currently appear EMPTY — actual leak exposure is likely nil today, but the crit check will stay red and any future key entry lands world-readable. Regression of done task fix-23, introduced by the ~Jul 27 mylar3 deployment; needs a new work item. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh nas 'find /volume1/docker \( -name @eaDir -o -name "#recycle" \) -prune -o -type f \( -name "*.env" -o -name ".env" -o -name "config.ini" -o -name "config.xml" \) -perm /0044 -print 2>/dev/null'
/volume1/docker/mylar3/config/mylar/config.ini
printf '%s\n' "$PW" | ssh nas 'sudo -S sh -c "ls -la /volume1/docker/mylar3/config/mylar/config.ini" 2>/dev/null'
-rw-r--r-- 1 btabaska users 10007 Aug  2 10:53 /volume1/docker/mylar3/config/mylar/config.ini
# credential-class key names present (values suppressed; value-requiring grep matched 0 lines => fields appear empty):
api_key, http_password, sab_apikey, sab_password, torznab_apikey, external_apikey, deluge_password, qbittorrent_password, transmission_password, rtorrent_password, utorrent_password, nzbget_password, opds_password, email_password, telegram_token, gotify_token, pushover_apikey, pushbullet_apikey, boxcar_token, git_token, airdcpp_password, password_32p, encrypt_passwords
```

</details>

### SM3. nas-worldwritable-sweep=5: all five world-writable paths are mylar3 cache/ComicTagger files from the Jul 27 deploy (fix-23 regression)

**Host:** nas · **Component:** /volume1/docker/mylar3 (cache + .ComicTagger) · **Auditor:** host:nas · **Work item:** `fix-53`

Re-ran the nas-worldwritable-sweep check cmd (secrets.yaml, task fix-23) read-only: the 5 offenders are all under /volume1/docker/mylar3/config/mylar — html_cache dir (0777), 3622.jpg, .ComicTagger/settings, .ComicTagger/cache_version.txt, .ComicTagger/cv_cache.db (all 0666), timestamps Jul 27 19:40-20:06 (deployment day). Same root cause as the config.ini finding: mylar3/ComicTagger create files world-writable, so cv_cache.db and the cache dir will keep regressing after any chmod until the container's umask/PUID handling is fixed. Regression of done task fix-23 introduced by the mylar3 deploy; needs a new work item together with the config.ini one. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh nas 'find /volume1/docker /volume1/scripts \( -name @eaDir -o -name "#recycle" \) -prune -o ! -type l -perm -0002 -print 2>/dev/null'
/volume1/docker/mylar3/config/mylar/cache/html_cache
/volume1/docker/mylar3/config/mylar/cache/3622.jpg
/volume1/docker/mylar3/config/mylar/.ComicTagger/settings
/volume1/docker/mylar3/config/mylar/.ComicTagger/cache_version.txt
/volume1/docker/mylar3/config/mylar/.ComicTagger/cv_cache.db
printf '%s\n' "$PW" | ssh nas 'sudo -S sh -c "ls -la <those 5 paths>" 2>/dev/null'
-rw-rw-rw- 1 btabaska users  32768 Jul 27 19:49 .ComicTagger/cv_cache.db
-rw-rw-rw- 1 btabaska users   1790 Jul 27 20:06 .ComicTagger/settings
-rw-rw-rw- 1 btabaska users 105079 Jul 27 19:40 cache/3622.jpg
drwxrwxrwx 1 btabaska users      0 Jul 27 19:49 cache/html_cache
```

</details>

### SM4. Radarr stuck=9 classified: 6 stale 'not an upgrade' decisions (3-5 days), 1 wrong-movie importBlocked since 07-28, 2 incomplete imports; plus seedbox-path import failures for 5 more titles

**Host:** nas · **Component:** radarr (:7878) queue · **Auditor:** svc:arr-stack · **Work item:** `fix-54`

Verifies today's radarr-queue-stuck check (regression of verify-06). The 9 warning rows: 6x importPending 'Not an upgrade / Not a Custom Format upgrade for existing movie file' aged 07-28 to 08-02 (Passengers, Moana KO-dub, Good Will Hunting V2, Wicked, Super Mario Bros, Fantastic 4) — grabs that will never import and need manual rejection; Jackass.2010 importBlocked since 2026-07-28 ('release was matched via grab history' wrong-movie map); Sinners.2025 and Borderlands.2024 'importing' but 'one or more movies expected were not imported'. Error log additionally shows the same rclone-path race as Sonarr on 5 other titles (The.Accountant, Chinatown, Hotel.Transylvania, Shape.of.Water, Moana) — 'Import failed, path does not exist /seedbox/movies/...', latest 17:14Z today. Note the deluge-preimport-stuck check (fix-25 regression, 17 items incl. To.Wong.Foo) names titles NOT present in this queue — those grabs are no longer tracked by Radarr at all, consistent with pre-import parking on the deluge side (flow lane territory). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
curl -sm 20 -H "X-Api-Key: $RADARR_KEY" "http://192.168.10.4:7878/api/v3/queue?pageSize=60"
totalRecords: 13
2026-07-28T21:27 | Jackass.2010.UNRATED.1080p.BluRay.x264-DON | warning/importBlocked | Found matching movie via grab history, but release was match
2026-07-29T20:55 | Passengers 2016 1080p WEB-DL x264 AC3-JYK | warning/importPending | Not an upgrade for existing movie file
2026-07-29T18:20 | Sinners.2025.720p.BluRay...MegaPeer.mkv | warning/importing | One or more movies expected in this release were not importe
(+4 more 'Not an upgrade' importPending 07-28..08-02; 4 rows ok/downloading)
curl ... /api/v3/log?level=error&pageSize=30
 1x last=2026-08-02T17:14:06 Import failed, path does not exist or is not accessible by Radarr: /seedbox/movies/The.Accounta
 1x last=2026-08-02T10:28:06 Import failed, ... /seedbox/movies/Chinatown.19
 1x last=2026-08-02T09:16:10 Import failed, ... /seedbox/movies/Hotel.Transy
 1x last=2026-08-02T05:20:05 Import failed, ... /seedbox/movies/The.Shape.of
curl ... /api/v3/rootfolder -> /movies accessible= True free= 6152 GiB
```

</details>

### SM5. Libreseerr: 12 of 30 requests in error state; last successful request 2026-07-20 — the 07-28 user session failed 6/6 on Hardcover metadata candidacy

**Host:** mini · **Component:** libreseerr (:8789) · **Auditor:** svc:arr-stack · **Work item:** `fix-57`

Read /opt/stacks/libreseerr/data/requests.json (session-auth app, requests persisted on disk): 18 completed / 12 error, no pending. Every request since 2026-07-20 has errored — the 2026-07-28 session was 6 attempts, 6 failures, all public-domain classics (The Odyssey x3, The Iliad, Le Morte d'Arthur, The Romance of Arthur) rejected with 'No eligible metadata candidate — refusing to add a degraded record' or 'not found in the backend metadata provider (Hardcover)'; the 07-20 batch (Wuthering Heights x3, Persuasion, Rolling in the Deep) failed identically. The refusal guard is working as designed, but the consumer outcome is a book-request pipeline with a 13-day success drought and a 100% failure rate on classics due to Hardcover metadata coverage. Related to but not covered by open task books-hc-upstream-swap (that task is about the temp local rg-hc image, not the classics metadata gap). Container Up 12 days, no runtime errors in log tail. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'sudo python3 -c "import json; d=json.load(open(\"/opt/stacks/libreseerr/data/requests.json\")); ..."'
total requests: 30
Counter({'completed': 18, 'error': 12})
newest completed: 2026-07-20T23:00:19
- 2026-07-28T23:02:02 | The Odyssey | No eligible metadata candidate ... refusing to add a degraded record
- 2026-07-28T23:00:14 | Le Morte d'Arthur | No eligible metadata candidate ...
- 2026-07-28T22:56:19 | The Iliad | was not found in the backend metadata provider (Hardcover)
- 2026-07-20T23:19:42 | Wuthering Heights | No eligible metadata candidate ...
- 2026-07-20T22:31:20 | The Rotten Romans | Book is unmonitored in the backend with no file — nothing will ever search for it
ssh mini 'docker ps --format "{{.Names}} {{.Status}}" | grep libreseerr' -> libreseerr Up 12 days
```

</details>

### SM6. Bitmagnet indexer failing through Prowlarr for >6h — corroborated from three arr consumers

**Host:** nas · **Component:** prowlarr (:9696) -> bitmagnet torznab · **Auditor:** svc:arr-stack · **Work item:** `fix-50`

Verifies today's bitmagnet-torznab-via-prowlarr TIMEOUT (regression of seed-12) from the service side: Prowlarr error log shows 12x feed failures against http://192.168.10.4:3333/torznab/api (latest 08:59Z today), Sonarr health reports 'Indexers unavailable due to failures: Bitmagnet (DHT) (Prowlarr)', and Bookshelf escalates it to IndexerLongTermStatusCheck 'unavailable for more than 6 hours'. Whisparr also logged 2x prowlarr feed-processing errors. Per lane rules I did not run indexer test actions; the bitmagnet service itself belongs to another lane. NOT fixed per read-only mandate.

MERGED duplicate from svc:reading (M31): Bookshelf reports Bitmagnet (DHT) indexer unavailable >6h — consumer-side confirmation of seed-12 regression — Bookshelf's /api/v1/health (probed live 2026-08-02 ~13:10 EDT) carries an IndexerLongTermStatusCheck warning: 'Indexers unavailable due to failures for more than 6 hours: Bitmagnet (DHT) (Prowlarr)'. This matches today's 10:23 EDT failing check bitmagnet-torznab-via-prowlarr (TIMEOUT after 60s, task seed-12) — this is the consumer end of that failure: book grabs through Bookshelf have lost the Bitmagnet source. seed-12 is in the regression set (previously done), so this is a regression needing a new work item, not a known open task. NOT fixed per read-only mandate. Bookshelf is otherwise healthy (queue empty, hardcover-token-valid pass).

<details><summary>Evidence</summary>

```
curl -sm 15 -H "X-Api-Key: $PROWLARR_KEY" http://192.168.10.4:9696/api/v1/log?level=error&pageSize=30
12x last=2026-08-02T08:59:37 An error occurred while processing indexer feed. [http://192.168.10.4:3333/torznab/api?t=search
curl -sm 15 -H "X-Api-Key: $SONARR_KEY" http://192.168.10.4:8989/api/v3/health
warning | IndexerStatusCheck | Indexers unavailable due to failures: Bitmagnet (DHT) (Prowlarr)
curl -sm 15 -H "X-Api-Key: $BOOKSHELF_KEY" http://192.168.10.4:8790/api/v1/health
warning | IndexerLongTermStatusCheck | Indexers unavailable due to failures for more than 6 hours: Bitmagnet (DHT) (Prowlarr)
--- (merged lane svc:reading) ---
printf '%s\n' "$PW" | ssh nas 'sudo -S sh -c '\''K=$(grep -oP "(?<=<ApiKey>)[^<]+" /volume1/docker/bookshelf/config/config.xml); curl -s -m 15 -H "X-Api-Key: $K" http://localhost:8790/api/v1/health'\'' 2>/dev/null'
[
  {
    "source": "IndexerLongTermStatusCheck",
    "type": "warning",
    "message": "Indexers unavailable due to failures for more than 6 hours: Bitmagnet (DHT) (Prowlarr)",
    "wikiUrl": "https://wiki.servarr.com/readarr/system#indexers-are-unavailable-due-to-failures"
  }
]
# 10:23 sweep: bitmagnet-torznab-via-prowlarr | fail | TIMEOUT after 60s (task seed-12)
```

</details>

### SM7. Lidarr queue: 2 importFailed album grabs, one stuck 5 days (Charli XCX - Brat) with 'tracks expected were not imported'

**Host:** nas · **Component:** lidarr (:8686) queue · **Auditor:** svc:arr-stack · **Work item:** `fix-56`

Both queue records are warning/importFailed 'One or more tracks expected in this release were not imported': Charli XCX - Brat (2024) FLAC added 2026-07-28T21:49Z (5 days stuck) and Daft Punk - Homework Remixes added 2026-08-02T02:48Z. Adjacent to but distinct from today's failing checks lidarr-incomplete-albums (fix-28 regression: One More Light 9/10, Born to Die 17/24) and nas-soularr-failed-imports-fresh (fix-40: soularr Camera/Heat Waves cycling) — these two are Prowlarr/deluge-path grabs whose partial imports leave albums incomplete, feeding the same fix-28 symptom. Root folder /music accessible, 10260 GiB free. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
curl -sm 20 -H "X-Api-Key: $LIDARR_KEY" "http://192.168.10.4:8686/api/v1/queue?pageSize=40"
totalRecords: 2
2026-08-02T02:48 | Daft Punk - Homework (Remixes) (2LP) (2022) [24- | warning/importFailed | One or more tracks expected in this release were not importe
2026-07-28T21:49 | Charli XCX - Brat (2024) [FLAC] 88               | warning/importFailed | One or more tracks expected in this release were not importe
curl ... /api/v1/rootfolder -> /music accessible= True free= 10260 GiB
```

</details>

### SM8. edge-plex-version-current is structurally broken — grep picks the XML declaration version="1.0"; real WAN-exposed Plex is 1.43.3.10793 (one build behind 1.43.3.10828)

**Host:** nas · **Component:** verification edge-plex-version-current / Plex Media Server · **Auditor:** svc:nas-apps · **Work item:** `fix-62`

The failing check (fix-24 regression, 10:23 run: VERSION_STALE:exposed=1.0_latest=1.43.3.10828) parses /identity with grep -oE 'version="[^"]+"' | head -1, which always matches the XML declaration <?xml version="1.0"?> before the MediaContainer version attribute — so the check can never emit VERSION_OK:current and its 'exposed=1.0' evidence is garbage. Live reproduction from the seedbox vantage on 2026-08-02 shows the WAN-exposed server is actually 1.43.3.10793-cd55560bb vs Synology-channel latest 1.43.3.10828-00f62d37d — same 1.43.3 stream, one build behind, and past the check's 14-day grace since VERSION_STALE fired. So there are two defects: a real (mild) version lag, and a check parser bug that misreports it. NOT fixed per read-only mandate; the check needs a MediaContainer-anchored parse (e.g. grep 'MediaContainer' line first) and fix-24 needs the package updated.

MERGED duplicate from flow:edge-dns (M53): edge-plex-version-current check parses the XML declaration, so exposed version is always '1.0' — permanent false alarm that also masks real staleness — Today's 10:23 EDT run reports VERSION_STALE exposed=1.0 latest=1.43.3.10828 (fix-24 regression set). Reproduced live 2026-08-02 ~13:35 EDT: the check pipes /identity through grep -oE 'version="[^"]+"' | head -1, and the FIRST match in the response is the XML declaration <?xml version="1.0"?>, not the MediaContainer version attribute. exp is therefore always '1.0', exp==latest can never be true, and the only pass path is the 14-day post-release grace window — the check fires stale after every Plex release regardless of the actual exposed build, and conversely never actually compares the real version. The genuinely exposed build off-net is 1.43.3.10793-cd55560bb vs latest 1.43.3.10828 — same 1.43.3 train, patch-level lag only, so today's failure wildly overstates. Regression of done task fix-24; needs a new work item (fix regex to skip the declaration, e.g. grep the MediaContainer line first). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
WAN=$(curl -s -m 10 https://ifconfig.me); ssh seedbox "curl -s -m 10 http://$WAN:32400/identity"
<?xml version="1.0" encoding="UTF-8"?>
<MediaContainer size="0" apiVersion="1.2.2" claimed="1" machineIdentifier="70ffcfbb5dc9389e315070cf3a8af99c5fb340b4" version="1.43.3.10793-cd55560bb">

curl -s http://192.168.10.4:32400/identity | grep -oE 'version="[^"]+"'
version="1.0"            <- head -1 takes this (XML declaration)
version="1.43.3.10793-cd55560bb"

curl -s https://plex.tv/api/downloads/5.json | python3 -c "... ['nas']['Synology (DSM 7.2.2+)'] ..."
latest 1.43.3.10828-00f62d37d

mini /var/lib/verification/results.json (run 2026-08-02T10:23:08-04:00):
edge-plex-version-current fail 'VERSION_STALE:exposed=1.0_latest=1.43.3.10828-00f62d37d'
edge-plex-remote-identity pass (machineIdentifier matches)
--- (merged lane flow:edge-dns) ---
ssh seedbox 'curl -s -m 8 http://162.0.177.18:32400/identity'
<?xml version="1.0" encoding="UTF-8"?>
<MediaContainer size="0" apiVersion="1.2.2" claimed="1" machineIdentifier="70ffcfbb5dc9389e315070cf3a8af99c5fb340b4" version="1.43.3.10793-cd55560bb">

grep -A 12 "id: edge-plex-version-current" foss-setup/verification/checks.d/edge.yaml
  exp=$(ssh ... seedbox "curl -s -m 10 http://$WAN:32400/identity"
  | grep -oE 'version="[^"]+"' | head -1 | cut -d'"' -f2);
  ... print("VERSION_OK:current" if exp==d["version"] else ("VERSION_OK:grace_%.0fd" % age if age < 14 else "VERSION_STALE:exposed="+exp+...))
# head -1 matches <?xml version="1.0" ...> -> exp='1.0' always
# today's runner output: edge-plex-version-current fail VERSION_STALE:exposed=1.0_latest=1.43.3.10828
```

</details>

### SM9. stash-serving check fails with empty output because Stash now requires auth (anonymous GraphQL = 401 empty body); Stash itself verified healthy — effectively unmonitored since ~2026-07-22

**Host:** nas · **Component:** stash / verification stash-serving · **Auditor:** svc:nas-apps · **Work item:** `fix-62`

Reproduced the check's exact unauthenticated GraphQL POST from the Mac: HTTP 401 with a zero-byte body, which is exactly the empty output the 10:23 run recorded (nas-01 regression). With the ApiKey header (vault homepage_widgets.stash_api_key) the same query returns v0.31.1 in 22ms, findScenes count=3232 (5.5s), systemStatus OK — service fully working; the check simply predates the auth requirement. /volume1/docker/stash/config/config.yml mtime is 2026-07-22 18:07 EDT, consistent with auth being enabled then; triage files show stash-serving failing at least since 07-29. Secondary observation: the stats{} aggregate query timed out twice at 8s (curl exit 28) while other queries answer — avoid stats in any replacement probe. NOT fixed per read-only mandate; check needs the ApiKey header.

MERGED duplicate from repo:verification-suite (M62): stash-serving fails with empty output because Stash now 401s unauthenticated GraphQL — service is actually up; the check carries no credentials and no diagnostics — Reproduced live from mini at 13:5x: POST http://nas:9999/graphql returns HTTP 401 with a 0-byte body in 0.2s, and GET / returns 302 (login) — Stash is serving fine but has authentication enabled on the GraphQL endpoint, which the check's bare unauthenticated POST cannot satisfy. Because the probe uses 'curl -s' with no '-w %{http_code}' and no error branch, the stored output is completely empty (results.json: status=fail exit=0 dur=0.05, output ''), giving the operator zero clue whether the pipe or the service broke — the exact ambiguity this sweep lane was asked to resolve. The check can never pass in its current form; nas-01 is being named daily in reopen-suggestions for what is a check-vs-config credential mismatch, not a service regression. NOT fixed per read-only mandate (fix: send ApiKey header from the verification env, or assert the 401/login behavior explicitly, and always emit an http_code).

<details><summary>Evidence</summary>

```
curl -s -m 8 -X POST http://192.168.10.4:9999/graphql -H 'Content-Type: application/json' -d '{"query":"{version{version}}"}' -o /dev/null -w 'http=%{http_code} size=%{size_download}\n'
http=401 size=0        <- check's expect '"version":"v[0-9]' fails on empty body

SK=$(python3 -c "...['homepage_widgets']['stash_api_key']")
curl -s -m 8 -X POST http://192.168.10.4:9999/graphql -H "ApiKey: $SK" -d '{"query":"{version{version}}"}' -D -
HTTP/1.1 200 OK / Content-Length: 42
{"data":{"version":{"version":"v0.31.1"}}}
curl ... -d '{"query":"{findScenes(filter:{per_page:1}){count}}"}'
{"data":{"findScenes":{"count":3232}}} http=200 time=5.504323
curl ... -d '{"query":"{systemStatus{status databaseSchema}}"}'
{"data":{"systemStatus":{"status":"OK","databaseSchema":85}}}
curl ... -m 8 -d '{"query":"{stats{scene_count image_count}}"}'  -> exit 28 (timeout), http=000

ssh nas 'sudo -S sh -c "stat -c \"%y %n\" /volume1/docker/stash/config/config.yml"'
2026-07-22 18:07:54.975418130 -0400 /volume1/docker/stash/config/config.yml
--- (merged lane repo:verification-suite) ---
# stored result (results.json 10:23): stash-serving status=fail exit=0 dur=0.05, output EMPTY
# live reproduction from mini (2026-08-02 ~13:55 EDT):
ssh mini "curl -s -m 8 -o /tmp/stash-probe-body.txt -w 'http=%{http_code} size=%{size_download} time=%{time_total}\n' -X POST http://nas:9999/graphql -H 'Content-Type: application/json' -d '{\"query\":\"{version{version}}\"}'; curl -s -m 8 -o /dev/null -w 'root_http=%{http_code}\n' http://nas:9999/"
http=401 size=0 time=0.203820
root_http=302
# check cmd (nas-services.yaml lines 144-147): curl -s -m 8 -X POST http://nas:9999/graphql ... expect '"version":"v[0-9]' — no auth header, no -w, no failure branch
```

</details>

### SM10. CWA container marked unhealthy (healthcheck exceeds its 3s timeout, failing streak 7) while the app itself serves login in 25ms

**Host:** nas · **Component:** calibre-web-automated container · **Auditor:** svc:nas-apps · **Work item:** `fix-55`

docker inspect at ~14:00 EDT 2026-08-02 shows calibre-web-automated (Up 5 days) Health.Status=unhealthy, FailingStreak=7, with every logged probe ending 'Health check exceeded timeout (3s)'. Meanwhile the actual web app answers http://192.168.10.4:8083/login with 200 in 0.025s, so the image's built-in healthcheck (from the pinned fork image ghcr.io/new-usemame/calibre-web-nextgen:v4.0.7) is what is failing, not the service. Consequence: the docker health signal for CWA is now noise — a real outage would look identical, and anything gating on container health is misled. Live compose image line matches the repo mirror exactly (digest pin present), so no drift; the fork pin itself is a documented June 2026 decision (CVE-2026-7713). Not covered by an open task; NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
printf '%s\n' "$PW" | ssh nas 'sudo -S /usr/local/bin/docker ps -a ...' | grep calibre
calibre-web-automated  ghcr.io/new-usemame/calibre-web-nextgen:v4.0.7  Up 5 days (unhealthy)

sudo docker inspect calibre-web-automated --format '{{json .State.Health}}'
unhealthy 7
2026-08-02T11:02:53 -1 'Health check exceeded timeout (3s)'
2026-08-02T11:03:39 -1 'Health check exceeded timeout (3s)'
2026-08-02T11:04:53 -1 'Health check exceeded timeout (3s)'

curl -s -m 10 -o /dev/null -w 'http=%{http_code} time=%{time_total}s' http://192.168.10.4:8083/login
http=200 time=0.024934s   (body: 'Calibre-Web Automated | Login')

live /volume1/docker/calibre-web-automated/docker-compose.yml line 26 == repo foss-setup/configs/nas/calibre-web-automated/docker-compose.yml line 26 (same digest pin sha256:89899edd...)
```

</details>

### SM11. lidarr-artist-monitor-reconcile flaps: 10 failures in 7 days on intermittent Lidarr HTTP 500, with no retry and a dead failure notifier

**Host:** mini · **Component:** lidarr-artist-monitor-reconcile.service · **Auditor:** host:mini · **Work item:** `fix-55`

The media-07 reconciler (15-min timer) failed 10 times in the last 7 days (journal p-err flood scan), each time with a single 'API_ERR HTTPError: HTTP Error 500' from Lidarr and immediate exit 1 — no retry/backoff for a transient upstream error. Confirmed today's 06:00:29 failure and that subsequent runs (12:30, 12:45, 13:00) succeed with RECONCILE_OK flipped=0 artists=38 albums=1254, so the invariant self-heals, but every failure also triggers the broken ntfy-notify@ (sec-12), so the flapping is invisible. ~2-3 fails/day of one unit is also what keeps p-err journal noise nonzero. Not covered by an open task (sec-12 covers the notifier, not this unit's fragility); this unit is manual/doc-only per configs/host/mini (not ansible-managed). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'sudo journalctl -u lidarr-artist-monitor-reconcile.service --since "2026-08-02 05:55" --until "2026-08-02 06:05" --no-pager'
Aug 02 06:00:29 macmini lidarr-artist-monitor-reconcile.py[3761033]: API_ERR HTTPError: HTTP Error 500: Internal Server Error
Aug 02 06:00:29 macmini systemd[1]: lidarr-artist-monitor-reconcile.service: Main process exited, code=exited, status=1/FAILURE
Aug 02 06:00:29 macmini systemd[1]: Failed with result 'exit-code'.

ssh mini 'sudo journalctl -p err -S -7days --no-pager | awk ... | sort | uniq -c | sort -rn | head'
     10    macmini systemd[1]: Failed to start Reconcile Lidarr artist-monitored invariant — close the musicseerr unmonitored-artist generator (media-07).

later runs OK:
Aug 02 13:00:42 macmini lidarr-artist-monitor-reconcile.py[257913]: RECONCILE_OK flipped=0 artists=38 albums=1254
```

</details>

### SM12. 3 reboots in 7 days: 07-25 was an abrupt crash-like end; 07-29 and 07-31 were clean operator shutdowns; no kernel updates involved

**Host:** rig · **Component:** host-stability / reboot pattern · **Auditor:** host:rig · **Work item:** `fix-64`

Boot history: boot -4 ended ABRUPTLY Sat 07-25 16:27:05 (last entries are routine moondeckbuddy restart-loop + UFW noise, no shutdown sequence) followed by a 1.5h dark gap, a 1.5-minute boot at 17:53, and a second clean reboot at 17:55 — the 07-25 event is the only unexplained crash/hard-power-off in the window. Boot -2 ended Wed 07-29 12:57 with a clean shutdown sequence ~90min after an llama-server SIGSEGV storm (8 coredumps 11:18-11:21) and an orca-ide SEGV at 12:21 — pattern reads as an operator recovery reboot. Boot -1 ended 07-31 with the plasma poweroff (separate finding). pacman.log shows zero linux/linux-cachyos/nvidia upgrades across 07-25..08-01, so none of the reboots were update-driven. The 07-25 abrupt end has no captured cause (journal can't record a panic) — worth watching for recurrence.

<details><summary>Evidence</summary>

```
ssh rig 'journalctl --list-boots'
 -4 8c4dec4d... Sun 2026-07-19 09:59:59 EDT Sat 2026-07-25 16:27:05 EDT
 -3 e5ee6e1f... Sat 2026-07-25 17:53:29 EDT Sat 2026-07-25 17:54:52 EDT
 -2 efec823e... Sat 2026-07-25 17:55:38 EDT Wed 2026-07-29 12:57:25 EDT
ssh rig 'journalctl -b -4 -e | tail -5'   # abrupt end, no shutdown sequence:
Jul 25 16:27:05 cachyos systemd[3642]: moondeckbuddy.service: Scheduled restart job, restart counter is at 76451.
ssh rig 'journalctl -b -2 -e | tail -3'   # clean:
Jul 29 12:57:25 cachyos systemd[1]: Stopped Network Time Synchronization.
ssh rig 'coredumpctl list | grep "07-29"'
Wed 2026-07-29 11:18:08 EDT 3770963 0 0 SIGSEGV missing /app/llama-server  (x8 through 11:21:41)
Wed 2026-07-29 12:21:33 EDT 3850238 1000 1000 SIGSEGV missing /opt/stably-orca/orca-ide
```

</details>

### SM13. containerd-shim SIGSEGV ('fatal error: fault') killed lumiverse with exit 137 at 10:07 EDT today; docker auto-restarted it

**Host:** rig · **Component:** containerd / lumiverse · **Auditor:** host:rig · **Work item:** `fix-64`

At 2026-08-02 10:07:16 EDT containerd logged a Go fatal runtime fault (SIGSEGV) with a stack trace inside containerd-shim-runc-v2 exec handling (exec.go:215 start path — likely a health-check exec), and dockerd simultaneously logged lumiverse exiting with exitCode=137 and restarting under the unless-stopped policy (restartCount=1). This explains the preflight 'lumiverse RestartCount=1'. The app came back clean (Up 3 hours, healthy; normal startup banner, no data errors) so impact was a brief blip, but a segfaulting container runtime shim is an infra-level flake worth tracking — if it recurs it graduates to a runtime/kernel bug investigation. Single occurrence observed; NOT fixed per read-only mandate (nothing to fix yet — monitor).

MERGED duplicate from flow:ai-serving (M45): containerd-shim SIGSEGV at 10:07 EDT today killed lumiverse (exit 137); auto-recovered, single occurrence since boot — At 2026-08-02 10:07:16 EDT a Go 'fatal error: fault' SIGSEGV crash dump was emitted under containerd[938] on rig; the containerd main process itself survived (same Main PID 938, active since boot 08-01 10:25, NRestarts=0), so this was a containerd-shim process crash (dump stack is in containerd/v2/internal/oom watcher code, which runs inside the shim). dockerd lost the ttrpc connection, recorded lumiverse exit 137, and restart policy brought it back within ~1s (RestartCount=1, now Up 3h healthy; rig-lumiverse and rig-lumiverse-connections both passed at 10:23). Only ONE such event exists since 08-01 — an initial grep count of 2 was polluted by my own SSH command line echoed into the journal by tailscaled session logging. palworld's RestartCount=1 is a separate, unrelated clean exit 0 at 08-01 18:32 EDT (game server self-exit). Not covered by any open task and not in the known-normal list; NOT fixed per read-only mandate (nothing to fix yet — but a repeat shim segfault should trigger a containerd/runc version + memory review on rig).

<details><summary>Evidence</summary>

```
ssh rig 'journalctl -u docker.service --since "2026-08-02 09:55" --until "2026-08-02 10:15" | grep -i lumiverse'
Aug 02 10:07:16 dockerd[1952]: msg="restarting container" container=91d8489eff02... exitCode=137 exitedAt="2026-08-02 14:07:16.677 UTC" manualRestart=false restartCount=1 restartPolicy="{unless-stopped 0}"
ssh rig 'journalctl --since "2026-08-02 10:07:10" --until "2026-08-02 10:07:20" | grep -iE "panic|fatal|SIGSEGV"'
Aug 02 10:07:16 containerd[938]: fatal error: fault
Aug 02 10:07:16 containerd[938]: [signal SIGSEGV: segmentation violation code=0x1 addr=0x48d366f4 pc=0x43ec37]
(stack: containerd-shim-runc-v2/process/exec.go:215 execProcess.start)
ssh rig 'docker inspect lumiverse --format "{{.State.Status}} rc={{.RestartCount}} started={{.State.StartedAt}}"'
running rc=1 started=2026-08-02T14:07:16.91160643Z
--- (merged lane flow:ai-serving) ---
ssh rig 'journalctl -u containerd --no-pager --since "2026-08-02 10:05" --until "2026-08-02 10:10" | grep -iE "panic|fatal|signal" | head -3'
Aug 02 10:07:16 cachyos containerd[938]: fatal error: fault
Aug 02 10:07:16 cachyos containerd[938]: [signal SIGSEGV: segmentation violation code=0x1 addr=0x48d366f4 pc=0x43ec37]
Aug 02 10:07:16 cachyos containerd[938]: runtime.sigpanic()
(dump frames include github.com/containerd/containerd/v2/internal/oom.(*watcher).start — shim code)
ssh rig 'journalctl -u docker --no-pager --since "2026-08-02 10:05" --until "2026-08-02 10:10" | grep -viE sbJoin | head -3'
Aug 02 10:07:16 dockerd[1952]: level=warning msg="Health check for container 91d8489eff02... error: ttrpc: closed"
Aug 02 10:07:16 dockerd[1952]: level=info msg="restarting container" container=91d8489eff02... exitCode=137 manualRestart=false restartCount=1 restartPolicy="{unless-stopped 0}"
ssh rig 'docker inspect lumiverse --format "RestartCount={{.RestartCount}} StartedAt={{.State.StartedAt}}"'
RestartCount=1 StartedAt=2026-08-02T14:07:16.91160643Z
ssh rig 'systemctl status containerd --no-pager | head -4; systemctl show containerd -p NRestarts --value'
Active: active (running) since Sat 2026-08-01 10:25:39 EDT; Main PID: 938 (containerd)
NRestarts: 0
ssh rig 'docker inspect palworld --format "palworld RestartCount={{.RestartCount}} StartedAt={{.State.StartedAt}}"'
palworld RestartCount=1 StartedAt=2026-08-01T22:32:42.284044791Z  (separate event, dockerd logged exitCode=0)
```

</details>

### SM14. moondeckbuddy crash-looping every ~10s for weeks — AppImage missing, exit 127; 76,451 restarts by Jul 25, still looping now

**Host:** rig · **Component:** moondeckbuddy.service (user unit) · **Auditor:** host:rig · **Work item:** `fix-64` · *skeptic-confirmed*

The user unit execs /home/btabaska/Applications/MoonDeckBuddy-1.9.2-x86_64_a7bd76f9cd54ef8cdd9271cd5c6d7d22.AppImage which no longer exists — every start exits 127 and Restart= re-fires ~10s later, forever. Restart counter was 76451 on the 07-25 boot, 16196 on the 07-31 boot, and this boot (~26h) has already produced 7990 journal lines; at 13:08:16 today it was again 'activating (auto-restart)'. Consequence: MoonDeck (Steam Deck game-streaming companion) is dead, and the loop floods the user journal (taxonomy #7/#17). Fix is trivial (disable unit or restore AppImage path) but NOT fixed per read-only mandate. glue-02 (rig desktop baseline, operator) is adjacent but does not name this. ORCHESTRATOR CONFIRMATION (gap:apollo-streaming, 16:48 EDT): still crash-looping live — status=127, ExecStart references /home/btabaska/Applications/MoonDeckBuddy-1.9.2-…AppImage which does not exist; unit is 'activating (auto-restart)' with a fresh invocation every ~10s. Apollo itself (the actual streaming server) is healthy — filed as a green confirmation.

<details><summary>Evidence</summary>

```
ssh rig 'systemctl --user status moondeckbuddy.service | head -8'
Active: activating (auto-restart) (Result: exit-code) since Sun 2026-08-02 13:08:16 EDT; 9s ago
Process: 947127 ExecStart=/bin/sh -c NO_GUI=... /home/btabaska/Applications/MoonDeckBuddy-1.9.2-x86_64_a7bd76f9cd54ef8cdd9271cd5c6d7d22.AppImage (code=exited, status=127)
sh[...]: /bin/sh: line 1: /home/btabaska/Applications/MoonDeckBuddy-1.9.2-...AppImage: No such file or directory
ssh rig 'journalctl -b -4 -e | tail -1'
Jul 25 16:27:05 systemd[3642]: moondeckbuddy.service: Scheduled restart job, restart counter is at 76451.
ssh rig 'journalctl -b 0 _SYSTEMD_USER_UNIT=moondeckbuddy.service | wc -l'
7990
```

</details>

### SM15. avahi hostname-conflict storm: 1,856 conflicts this boot, mDNS name drifted to cachyos-8306, cachyos.local does not resolve

**Host:** rig · **Component:** avahi-daemon / mDNS · **Auditor:** host:rig · **Work item:** `fix-64`

avahi-daemon has renamed the host 8306+ times ('Host name conflict, retrying with cachyos-8306') with 1,856 conflict events in this 26h boot (~one per 50s), and avahi-resolve for cachyos.local times out. Each cycle withdraws/re-registers address records on both enp10s0 and tailscale0, and Apollo (game-streaming host) re-registers its service every time — so mDNS/Moonlight discovery of the rig is effectively broken and the log churns continuously. The conflict loop registering records on tailscale0 suggests avahi may be seeing its own reflected announcements via the tailnet interface (or a duplicate 'cachyos' claimant on the LAN). Also observed in boot -1, so it predates the outage. NOT fixed per read-only mandate (candidate fix: exclude tailscale0 from avahi allow-interfaces).

<details><summary>Evidence</summary>

```
ssh rig 'journalctl -b 0 -u avahi-daemon | grep -c "Host name conflict"'
1856
ssh rig 'avahi-resolve -n cachyos.local'
Failed to resolve host name 'cachyos.local': Timeout reached
boot -1 sample (Jul 31 11:05:06):
avahi-daemon[812]: Host name conflict, retrying with cachyos-8306
avahi-daemon[812]: Withdrawing address record for 100.68.237.117 on tailscale0.
avahi-daemon[812]: Registering new address record for 192.168.10.12 on enp10s0.IPv4.
apollo[10092]: Info: Adding avahi service cachyos
apollo[10092]: Info: Avahi service cachyos successfully established.
```

</details>

### SM16. Rig manifest loop degraded: ansible-pull non-convergent (changed=1 every run) + pkglist lookup fails every run + export-manifests silently skips inventory refresh

**Host:** rig · **Component:** ansible-pull + export-manifests (rebuildability loop) · **Auditor:** host:rig · **Work item:** `fix-65`

Three related silent-partial failures in the rig reproducibility chain (taxonomy #6): (1) ansible-pull runs on schedule but reports changed=1 on every run (08-01 14:29 and 08-02 04:47) — non-idempotent task, same class as the failing ansible-site-converged-mini check (fix-42 regression on mini, so this is the rig-side sibling); (2) every run also WARNs 'Unable to access the file hosts/cachyos/pkglist.pacman-explicit.txt: File not found' — the package manifest the playbook expects is missing from the control repo, so a rebuild would not restore the package set; (3) export-manifests (weekly Mon 04:08 timer, last ran 07-27) logged '[!] gen-inventory-md.sh not executable/found; skipping inventory.md refresh' — a job leg silently skipped under exit 0. Side-answer to preflight: the Healthchecks export-manifests-rig last_ping 152h old is schedule-normal for the weekly Monday timer (next run Mon 08-03 04:08). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh rig 'journalctl -u ansible-pull.service --since -48h | grep -iE "WARNING|ok="'
Aug 02 04:47:07 bash[588144]: [WARNING]: An error occurred while running the lookup plugin 'file': Unable to access the file 'hosts/cachyos/pkglist.pacman-explicit.txt': File not found.
Aug 02 04:47:07 bash[588144]: cachyos : ok=29 changed=1 unreachable=0 failed=0 skipped=25
(identical WARNING + changed=1 on Aug 01 14:29:52 run)
ssh rig 'journalctl -u export-manifests.service --since "2026-07-27" | tail -4'
Jul 27 04:09:37 export-manifests.sh[1471948]: [export-manifests][!] gen-inventory-md.sh not executable/found; skipping inventory.md refresh.
Jul 27 04:09:37 ...: Done. Review + commit /opt/foss-setup/foss-setup/hosts/cachyos ...
ssh rig 'systemctl list-timers --all | grep export'
Mon 2026-08-03 04:08:32 EDT ... Mon 2026-07-27 04:09:37 EDT export-manifests.timer
```

</details>

### SM17. User quota 88% consumed (2541G of 2862G soft / 2909G hard) — real headroom is ~321G, far tighter than the 73%-of-17T disk figure

**Host:** seedbox · **Component:** disk-quota · **Auditor:** host:seedbox · **Work item:** `fix-54`

Observed 2026-08-02. The /home/hd34 volume shows 4.5T free (73% used), but the btabaska user quota is 2541G used against a 2862G soft / 2909G hard limit — the effective constraint is the quota, not the disk. Deluge (536 torrents in state) is the primary writer and has no quota awareness; at the current fill level roughly 321G of grabs would start failing with write errors, stalling the arr import pipeline downstream (pattern #4 precursor). Open reclaim work media-09 (~200GB unextractable RARs) and media-10 (retire readarr labels, gated til 08-04) would relieve most of the pressure but neither task tracks the quota ceiling itself. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh seedbox 'df -h /home/hd34/btabaska; quota -s'
Filesystem      Size  Used Avail Use% Mounted on
/dev/sdal1       17T   12T  4.5T  73% /home/hd34
Disk quotas for user btabaska (uid 30002):
     Filesystem   space   quota   limit   grace   files   quota   limit   grace
     /dev/sdal1   2541G   2862G   2909G           57031       0       0
ssh seedbox 'ls ~/.config/deluge/state/ | grep -c "\.torrent$"'
536
```

</details>

### SM18. deluged.log is a retry-storm flood: 1649 of 1655 lines in a 25-min window are the same libtorrent performance warning (~1.1/sec), unrotated at 30.4MB

**Host:** seedbox · **Component:** deluged.log · **Auditor:** host:seedbox · **Work item:** `fix-69`

Observed 2026-08-02 19:07 UTC. A 400KB tail window (18:42-19:07) contained 1655 lines of which 1649 were 'on_alert_performance ... max outstanding piece requests reached, outstanding_request_limit_reached' (mostly John.Wick.Chapter.4 and Euphoria.US.S02 under heavy seeding) — pattern #7: any real error is invisible in the flood, and at this rate the log grows ~20MB/day with no rotation (already 30.4MB, up from the documented ~29MB), eating into the tight user quota. Zero [ERROR-level lines and zero other error/fail lines in the window, so the daemon itself is healthy; the fix is a libtorrent max_out_request_queue/session tunable or log rotation. NOT fixed per read-only mandate. The ~29MB-unrotated size was documented as an access hazard but the flood rate is new signal.

<details><summary>Evidence</summary>

```
ssh seedbox 'ls -la ~/.config/deluge/deluged.log'
-rw-r--r-- 1 btabaska hd34 30374029 Aug  2 19:07 /home/hd34/btabaska/.config/deluge/deluged.log
ssh seedbox 'W=$(tail -c 400000 ~/.config/deluge/deluged.log); echo lines: $(echo "$W" | wc -l); echo perf: $(echo "$W" | grep -c outstanding_request_limit_reached); echo first-ts: $(echo "$W" | sed -n 2p | cut -c1-8); echo "$W" | grep -iE "error|fail" | grep -v outstanding_request_limit_reached | tail -15; echo "$W" | grep -c "\[ERROR"'
window lines: 1655
perf-warning lines: 1649
window first ts: 18:42:11
== non-perf errors in window == (none)
== ERROR-level lines == 0
sample line:
19:07:25 [WARNING ][deluge.core.torrentmanager :1616] on_alert_performance: John.Wick.Chapter.4.2023.1080p.AMZN.WEB-DL...mkv: performance warning: max outstanding piece requests reached, outstanding_request_limit_reached
```

</details>

### SM19. Kometa run errors (29) are a single root cause: 7 IMDb list fetches blocked with 403 Forbidden — collections built from those lists are silently stale (fix-37 regression)

**Host:** mini · **Component:** kometa · **Auditor:** svc:media-aux · **Work item:** `fix-67`

Today's 05:00 run finished (05:00:51-05:02:10, exit banner present) but check kometa-run-clean failed with kometa_run_errors=29. Classification from /opt/stacks/kometa/config/logs/meta.log: exactly 7 IMDb list fetches (ls501373412, ls539646485, ls544963772, ls547463722, ls566357882, ls566667558, ls567618635) each produce 4 counted lines (403 Forbidden HTML body + json.decoder.JSONDecodeError + requests JSONDecodeError + 'Unknown Error: Expecting value') plus 1 Error Summary line = 29. This is taxonomy #11 upstream rot — IMDb is blocking Kometa's list scraper with 403 (not a 401 API-key issue); every collection sourced from those 7 lists silently stops updating. Kometa is 2.4.4 while the log banner reports newest 2.4.6 — an upgrade with refreshed scraper headers is the likely remediation path. Regression of done task fix-37 (kometa-run-clean). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'grep -cE "\[ERROR\]|\[CRITICAL\]" /opt/stacks/kometa/config/logs/meta.log; grep -E "\[ERROR\]" .../meta.log | sort | uniq -c'
14
7 [ERROR] | Unknown Error: Expecting value: line 1 column 1 (char 0)
7 [ERROR] | b'<html>\r\n<head><title>403 Forbidden</title></head>...'
replicated check awk on meta.log -> kometa_run_errors=29 (7 lists x 4 lines + 1 summary line)
context lines before each 403: Processing IMDb List: ls567618635 / ls566667558 / ls566357882 / ls547463722 / ls544963772 / ls539646485 / ls501373412
tail meta.log: | Finished 05:00 Run | Version: 2.4.4  Newest Version: 2.4.6 | Start Time: 05:00:51 2026-08-02 Finished: 05:02:10 Run Time: 0:01:19
```

</details>

### SM20. New pinchflat media item stuck on YouTube bot-check beyond the 7 accepted: id 3076 'Non AI Lofi for Summer Days' (source Yellow Cherry Jam) — POT versions match, so YouTube escalated (fix-37 regression)

**Host:** mini · **Component:** pinchflat · **Auditor:** svc:media-aux · **Work item:** `fix-67`

Check pinchflat-stuck-media failed today with new_botcheck_stuck=1. Read-only DB query identifies the item: media_items id=3076, title 'Non AI Lofi for Summer Days 🌿 Escape to a Chill Place', source custom_name 'Yellow Cherry Jam', uploaded_at 2026-07-20, media_filepath NULL, last_error matching 'Sign in to confirm' with a tail recommending YouTube cookie export. The bgutil POT countermeasure is correctly deployed and version-matched (server 1.3.1 via :4416/ping == plugin 1.3.1 inside /etc/yt-dlp/plugins/bgutil-ytdlp-pot-provider.zip in the pinchflat container), so per the check's own comment this is the 'YouTube escalated' branch, not the pipeline-regressed branch — this item needs cookies or acceptance into the accepted-ID list. Regression of done task fix-37 (check def accepts only ids 409,702,895,915,939,1008,1333). NOT fixed per read-only mandate.

MERGED duplicate from flow:youtube (M43): fix-37 regression: new M14 bot-check-stranded video (id 3076, 9bJ1sXn0Gsw) beyond the 7 accepted, abandoned since 07-20 — Check pinchflat-stuck-media (fail today 10:23, new_botcheck_stuck=1) traced to media_items id 3076 'Non AI Lofi for Summer Days' (video 9bJ1sXn0Gsw, source 1 Yellow Cherry Jam), uploaded 2026-07-20, error = the exact 'Sign in to confirm you're not a bot' LOGIN_REQUIRED text — the same POT-cant-beat-LOGIN_REQUIRED class as the 7 accepted 2026-07-14 casualties. The countermeasure pipeline is NOT regressed: bgutil plugin 1.3.1 matches server 1.3.1 and pinchflat-pot-provider passed today, so this is YouTube hard-gating one video; source cookie_behaviour=disabled so only sign-in cookies would recover it. Row updated_at is frozen at 2026-07-20T19:26:35 while the source indexed daily through 2026-08-02T00:34:50Z — pinchflat has stopped retrying, so it will not self-heal; needs an operator decision (attach cookies to recover, or add 3076 to the check's accepted-id list). Regression of done task fix-37 per reopen-suggestions; NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'python3 -c "import sqlite3; c=sqlite3.connect(\"file:/opt/stacks/pinchflat/config/db/pinchflat.db?mode=ro\",uri=True); [print(r) for r in c.execute(\"select id,title,substr(last_error,1,80),uploaded_at from media_items where last_error like ,%Sign in to confirm%, and media_filepath is null and id not in (409,702,895,915,939,1008,1333)\")]"'
(3076, 'Non AI Lofi for Summer Days 🌿 Escape to a Chill Place', 'WARNING: [youtube] No title found in player responses; falling back to title fro', '2026-07-20T00:00:00Z')
source join -> custom_name='Yellow Cherry Jam'; last_error tail: '//github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies  for tips on effectively exporting YouTube cookies'
ssh mini 'docker exec pinchflat python3 - (zipfile read of /etc/yt-dlp/plugins/bgutil-ytdlp-pot-provider.zip)'
yt_dlp_plugins/extractor/getpot_bgutil.py 1.3.1
results.json 10:23 EDT: bgutil-pot-serving | pass | "version":"1.3.1"
--- (merged lane flow:youtube) ---
ssh mini 'python3 -c "import sqlite3; c=sqlite3.connect(\"file:/opt/stacks/pinchflat/config/db/pinchflat.db?mode=ro\", uri=True); print(c.execute(\"select id,title,substr(inserted_at,1,19),substr(updated_at,1,19),source_id from media_items where last_error like :e and media_filepath is null and id not in (409,702,895,915,939,1008,1333)\",{\"e\":\"%Sign in to confirm%\"}).fetchall())"'
(3076, 'Non AI Lofi for Summer Days ...', '2026-07-20T00:25:30', '2026-07-20T19:26:35', 1)
last_error: ERROR: [youtube] 9bJ1sXn0Gsw: Sign in to confirm you're not a bot. Use --cookies-from-browser or --cookies ...
3076 flags: prevent_download=0 culled_at=None media_filepath=None
sources: (1,'Yellow Cherry Jam',enabled=1,last_indexed_at='2026-08-02T00:34:50Z',freq=1440,cookie_behaviour='disabled')
/var/lib/verification/results.json 2026-08-02T10:23: pinchflat-stuck-media | fail | new_botcheck_stuck=1 ; pinchflat-pot-provider | pass | bgutil:http-1.3.1 (external)
```

</details>

### SM21. Suwayomi library thumbnails broken: 63x HTTP 500 across 19 manga IDs in 24h, reproduced live — orphaned .tmp thumbnail cache entries

**Host:** rig · **Component:** suwayomi (via mini Caddy vhost manga.tabaska.us) · **Auditor:** svc:infra-mini · **Work item:** `fix-58`

Caddy access log shows 63 status-500 responses on manga.tabaska.us in the last 24h, all /api/v1/manga/N/thumbnail across 19 distinct manga IDs, served to a real browser (192.168.10.253, Firefox) browsing /library between 12:07 and 13:16 EDT today. Reproduced live at ~13:17 EDT: the 500 body is a Jetty exception '/home/suwayomi/.local/share/Tachidesk/downloads/thumbnails/39.tmp (No such file or directory)' — Suwayomi's DB references .tmp thumbnail files that no longer exist, plausibly orphaned by the rig's ~23h power-off (Fri 07-31 11:07 → Sat 08-01 10:25 EDT) interrupting thumbnail downloads mid-write. App root and reading path still serve (manga root 200); library UI is degraded for 19 series. Regression of done work read-18 (Suwayomi deploy); not in today's check set (rig services get no wiki/service coverage per known quirk). NOT fixed per read-only mandate (likely fix: clear/refresh the thumbnail cache rows).

<details><summary>Evidence</summary>

```
curl -s -m 15 -o /dev/null -w "%{http_code}\n" https://manga.tabaska.us/api/v1/manga/39/thumbnail
500
curl -s https://manga.tabaska.us/api/v1/manga/39/thumbnail | head -c 120
/home/suwayomi/.local/share/Tachidesk/downloads/thumbnails/39.tmp (No such file or directory)
ssh mini 'docker logs caddy --since 24h 2>&1 | grep "\"status\":500" | grep manga | grep -oE "manga/[0-9]+/thumbnail" | sort -u | wc -l'
19
ssh mini 'docker logs caddy --since 24h 2>&1 | grep -E "\"status\":5.." | grep -o "\"host\":\"[a-z0-9.-]*\"" | sort | uniq -c | sort -rn'
63 "host":"manga.tabaska.us" (of 277 total manga requests; resp_headers Server: Jetty(12.1.8), first ts 1785686846 = 12:07 EDT, last 1785691015 = 13:16 EDT 2026-08-02)
curl -s -m 15 -o /dev/null -w "%{http_code}\n" https://manga.tabaska.us/
200
```

</details>

### SM22. spent-enabled-timers chronically false-positives on verification.timer by observing it mid-activation of its own daily run — fix-39 regression noise

**Host:** mini · **Component:** spent-enabled-timers check (host-hygiene.yaml / spent-timers.sh) · **Auditor:** svc:monitoring-stack · **Work item:** `fix-61` · *skeptic-confirmed*

The check (runs inside the 10:15 daily sweep) flags timers with NEXT=n/a and LAST set. While the long oneshot verification.service is still activating, systemd reports its own verification.timer NEXT as n/a, so the check flags its own activator every daily run whose host-hygiene phase executes before the sweep finishes (~10 min run, check at ~10:23). Live at 13:15 EDT the timer is perfectly healthy: OnCalendar=*-*-* 07:15 America/Los_Angeles (=10:15 EDT daily), NEXT=Mon 2026-08-03 10:15 (correct — today is Sunday), LAST=today 10:15. This chronic warn buries the real M3 class (genuinely spent timers) the check was built to catch and keeps fix-39 on reopen-suggestions. Fix would be excluding verification.timer / timers whose service is currently active. NOT fixed per read-only mandate; regression of fix-39 check quality, needs a new work item.

MERGED duplicate from repo:verification-suite (M58): spent-enabled-timers false-positives on verification.timer during every daily sweep — the check flags the timer that triggered it, 14 consecutive days — While verification.service is running, systemd reports NEXT=n/a for its own verification.timer (OnCalendar daily 10:15 EDT), and LAST is set — exactly spent-timers.sh's 'spent' signature ($1==n/a && $3!=n/a, enabled). Since the daily sweep is the only unfiltered run and it is by definition triggered by that timer, the check fails on 100% of daily runs by construction: it appears in every triage-*.md from 07-19 through 08-02 (14 files), failed at 10:23 today with SPENT_ENABLED=verification.timer, and passed in the 13:01 audit sweep when the timer showed NEXT=Mon 2026-08-03 10:15:47. Consequences: daily warn noise erodes trust, fix-39 is wrongly named in reopen-suggestions.json every day (polluting the regression signal), and the false positive consumed one of today's 15 LLM triage slots. verification-quick.timer shows the same NEXT=n/a-while-service-active behavior and could flap the check too. Regression of fix-39's own check (check bug, not host state). NOT fixed per read-only mandate (fix: exclude timers whose triggered unit is currently active, or exclude verification*.timer).

MERGED duplicate from host:mini (L9): spent-enabled-timers false-positives on verification.timer by racing its own run (fix-39 check-logic bug) — Today's 10:23 daily run flagged SPENT_ENABLED=verification.timer, but live state shows the timer healthy (NEXT Mon 2026-08-03 10:15:47, LAST Sun 10:15:09). Mechanism: spent-timers.sh flags timers with NEXT=n/a and LAST set; the check executes inside verification.service itself, and while a timer's triggered service is running systemd reports its NEXT as n/a — so the check flags its own parent timer every daily sweep. The only genuine NEXT=n/a timers are stock-Ubuntu dormant ones (apport-autoreport, snapd.snap-repair, ua-timer) which the LAST!=n/a discriminator correctly skips. Needs a self-exclusion (or is-active check on the triggered unit) — a defect in fix-39's check, not a regression of the fixed behavior. NOT fixed per read-only mandate.

MERGED duplicate from flow:monitoring-alerting (L31): spent-enabled-timers false-positives on verification.timer when run from inside the verification sweep itself (fix-39 regression) — This morning's 10:23 warn flagged SPENT_ENABLED=verification.timer, but run live at 13:35 the same script prints SPENT_ENABLED=NONE and list-timers shows verification.timer NEXT=Mon 2026-08-03 10:15 EDT — a healthy daily timer (OnCalendar 07:15 America/Los_Angeles, Persistent=true). Mechanism: while a timer's triggered unit is still active, systemd reports NEXT=n/a (the next elapse isn't scheduled until the unit deactivates), and the check runs inside verification.service, so it sees its own timer as 'spent' whenever the sweep is slow enough to still be running at that point in the check order. Self-observation bug in fix-39's check (fix-39 is in the regression set); fix is to exclude a timer whose service is currently activating. NOT fixed per read-only mandate.

MERGED duplicate from arch:topology (L55): spent-enabled-timers flags verification.timer while that timer is live-healthy — check observes itself mid-run — Today's 10:23 daily reported SPENT_ENABLED=verification.timer (warn, fix-39), but at 13:44 the live timer shows LAST Sun 2026-08-02 10:15:09 and NEXT Mon 2026-08-03 10:15:47 — perfectly scheduled. The check runs inside the very verification.service invocation that verification.timer triggered; while a Type=oneshot service is activating, its timer can transiently report no pending trigger, so the check false-positives on its own run. Regression of fix-39 done work (self-observation edge case), needs an exclusion for the timer that spawned the runner. NOT fixed per read-only mandate.

*Verify note:* CONFIRMED with a clean differential. Fresh probes: (1) live systemctl list-timers — verification.timer healthy (NEXT Mon 2026-08-03 10:15:47, LAST Sun 10:15:09), only dormant stock timers show NEXT=n/a and those have LAST=n/a so the script skips them; (2) read /opt/verification/bin/spent-timers.sh — flags NEXT=n/a && LAST!=n/a && enabled/active, no self-exclusion, matching the auditor's read; (3) results.json 10:23:08 run (inside verification.service, i.e. under verification.timer) = FAIL SPENT_ENABLED=verification.timer, while /tmp/verify-audit/sweep-run.json 13:01:32 (ad-hoc audit runner, outside the timer) = PASS SPENT_ENABLED=NONE, and my standalone run now = NONE — same script, only variable is running under its own parent timer, proving the self-race mechanism (OnCalendar timer reports NEXT=n/a while its triggered unit is active); (4) triage files 07-28/29/30/31/08-02 all contain the failure — it recurs every daily sweep exactly as claimed. Mechanism, framing (check-logic bug in fix-39's M3 class check, not a service regression), and severity=low all correct. Fix direction (exclude the parent timer or gate on is-active of the triggered service) is sound.

<details><summary>Evidence</summary>

```
results.json (10:23 daily): spent-enabled-timers fail 'SPENT_ENABLED=verification.timer'
ssh mini 'systemctl list-timers --all --no-pager | grep verification'
Mon 2026-08-03 10:15:47 EDT 21h left  Sun 2026-08-02 10:15:09 EDT  verification.timer  verification.service
ssh mini 'systemctl cat verification.timer'
OnCalendar=*-*-* 07:15:00 America/Los_Angeles
Persistent=true
spent-timers.sh discriminator: systemctl list-timers --all --no-legend --plain | awk '$1=="n/a" && $3!="n/a"' -> at 10:23 (mid-run) verification.timer matched; at 13:15 it does not
--- (merged lane repo:verification-suite) ---
# fails during the daily run, passes outside it:
results.json (10:23): spent-enabled-timers status=fail output: SPENT_ENABLED=verification.timer (dur 0.03s)
/tmp/verify-audit/sweep-run.json (13:01): spent-enabled-timers not in failed set (pass)
# live listing after the run window:
ssh mini 'systemctl list-timers --all --no-legend --plain | grep -i verif'
Mon 2026-08-03 10:15:47 EDT 20h left  Sun 2026-08-02 10:15:09 EDT 3h 26min ago verification.timer verification.service
n/a                    n/a           Sun 2026-08-02 13:41:01 EDT 31s ago      verification-quick.timer verification-quick.service
# detection logic (spent-timers.sh line 19): list-timers --all | awk '$1=="n/a" && $3!="n/a"' + is-enabled
# chronic: grep -l spent-enabled-timers /var/lib/verification/triage-*.md → every file 2026-07-19 .. 2026-08-02 (14 days)
--- (merged lane host:mini) ---
ssh mini 'systemctl list-timers --all --no-pager | grep -E "n/a|verification"'
Sun 2026-08-02 13:15:19 EDT 6min left  Sun 2026-08-02 13:05:12 EDT verification-fast.timer
Sun 2026-08-02 13:41:00 EDT 31min left Sun 2026-08-02 12:40:40 EDT verification-quick.timer
Mon 2026-08-03 10:15:47 EDT 21h left   Sun 2026-08-02 10:15:09 EDT verification.timer
n/a n/a n/a n/a apport-autoreport.timer
n/a n/a n/a n/a snapd.snap-repair.timer
n/a n/a n/a n/a ua-timer.timer

/opt/verification/bin/spent-timers.sh (read):
done < <(systemctl list-timers --all --no-legend --plain 2>/dev/null | awk '$1=="n/a" && $3!="n/a"')

10:23 daily run output: SPENT_ENABLED=verification.timer (check id spent-enabled-timers, task fix-39)
--- (merged lane flow:monitoring-alerting) ---
ssh mini '/opt/verification/bin/spent-timers.sh'
SPENT_ENABLED=NONE   (13:35 EDT, outside the sweep — passes)

ssh mini 'systemctl list-timers --all | grep verification'
Mon 2026-08-03 10:15:47 EDT 20h left  Sun 2026-08-02 10:15:09 EDT  verification.timer  verification.service

spent-timers.sh selection logic: systemctl list-timers --plain | awk '$1=="n/a" && $3!="n/a"' (NEXT=n/a + LAST set)
10:23 daily run output: SPENT_ENABLED=verification.timer — sweep window 10:15:09-10:25:01 overlaps the check execution
--- (merged lane arch:topology) ---
ssh mini 'systemctl list-timers --all --no-pager | grep verification.timer'
Mon 2026-08-03 10:15:47 EDT 20h left  Sun 2026-08-02 10:15:09 EDT 3h 28min ago  verification.timer  verification.service
today's daily (10:23) failing line: spent-enabled-timers | warn | fix-39 | SPENT_ENABLED=verification.timer
```

</details>

### SM23. Crit-severity fast-tier checks flap: 8+ page/recover cycles overnight (03:06-07:15 EDT) plus a single-try dig false crit at 13:15 — pager-fatigue risk on the crit channel

**Host:** mini · **Component:** verification fast tier (crit checks: pinchflat-plex-visible, radarr-movies-in-plex, sonarr-tv-in-plex, dns-mini-internal) · **Auditor:** svc:monitoring-stack · **Work item:** `fix-61`

ntfy verification-topic history for the last ~12h shows pinchflat-plex-visible, radarr-movies-in-plex and sonarr-tv-in-plex repeatedly cycling NEW-crit-failure -> all-recovered within 10-30 min, at least 8 cycles between 03:06 and 07:15 EDT (correlates with Plex nightly maintenance window; stable during the day). Separately, dns-mini-internal (dig +short +time=3 +tries=1 @192.168.10.2, severity crit) paged at 13:15:29 with 'communications error ... timed out' and my identical probe succeeded moments later — a one-UDP-try 3s probe as a crit check will false-page on any blip. Self-recovering crit pages at this rate train the operator to ignore the crit channel (the channel that carried the real verification-mini dead-man page last night). Tags verify-06/dns-01 territory; needs retry/consecutive-failure damping or nightly-window awareness. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'TOK=$(sudo grep "^NTFY_TOKEN=" /etc/verification/env | cut -d= -f2-); curl -s -H "Authorization: Bearer $TOK" "http://127.0.0.1:8080/verification/json?poll=1&since=48h"'
03:06 fast: NEW (3): pinchflat-plex-visible, radarr-movies-in-plex, sonarr-tv-in-plex (crit) | 03:15 all recovered
03:37 fast: NEW (3) same | 03:45 all recovered | 04:06 NEW radarr-movies-in-plex | 04:15 recovered
04:57 NEW (2) | 05:05 recovered | 05:27 NEW (3) | 05:35 recovered | 06:06/06:46/07:06 sonarr-tv-in-plex | each recovered <10min
13:15:29 fast: NEW (1): dns-mini-internal (crit)
results-tier-fast.json ts=2026-08-02T13:15:29-04:00 fails=1: dns-mini-internal ';; communications error to 192.168.10.2#53: timed out'
dig +short +time=3 +tries=1 @192.168.10.2 home.tabaska.us  (from Mac, ~13:16)
192.168.10.2   exit=0
```

</details>

### SM24. BookLogr registration still OPEN (AUTH_ALLOW_REGISTRATION=True) — planned lockdown never executed

**Host:** mini · **Component:** booklogr (/opt/stacks/booklogr) · **Auditor:** svc:docs-life · **Work item:** `fix-51`

Live-confirmed 2026-08-02 ~13:20 EDT: booklogr-api container env AND /opt/stacks/booklogr/.env both carry AUTH_ALLOW_REGISTRATION=True, and the register route is live through the public vhost (GET https://booklogr-api.tabaska.us/v1/register returns 405 Method Not Allowed = POST route enabled; flask_cors is allow-all per compose). The compose.yaml's own comment documents the plan: 'Registration is OPEN for the initial account signup, then flipped off (AUTH_ALLOW_REGISTRATION=False in .env) and redeployed once the household accounts exist' — container is Up 4 days and the flip never happened. Exposure is LAN/tailnet-only (booklogr.tabaska.us and booklogr-api.tabaska.us have no public DNS record at 1.1.1.1; AdGuard resolves them to mini 192.168.10.2), so anyone on the LAN/tailnet can self-register an account. No open task covers this (sec-11 is the Bookshelf API key, not BookLogr) — needs a work item. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'docker inspect booklogr-api --format "{{range .Config.Env}}{{println .}}{{end}}" | grep -E "^AUTH_ALLOW_REGISTRATION"; sudo grep -E "^AUTH_ALLOW_REGISTRATION" /opt/stacks/booklogr/.env'
AUTH_ALLOW_REGISTRATION=True
AUTH_ALLOW_REGISTRATION=True
for p in v1/register v1/auth/register register; do echo -n "$p -> "; curl -s -m 10 -o /dev/null -w "%{http_code}\n" "https://booklogr-api.tabaska.us/$p"; done
v1/register -> 405
v1/auth/register -> 404
register -> 404
dig +short booklogr.tabaska.us @1.1.1.1        # (empty — no public record)
dig +short booklogr.tabaska.us                  # via AdGuard
192.168.10.2
# compose comment (foss-setup/configs/docker-stack/stacks/booklogr/compose.yaml lines 17-19): registration to be flipped off post-setup
```

</details>

### SM25. Palworld server segfaulted (SIGSEGV) 2026-08-01 ~18:32 EDT; docker auto-restarted it — mid-session player disconnect

**Host:** rig · **Component:** palworld (container /opt/stacks/palworld) · **Auditor:** svc:gaming · **Work item:** `fix-64`

The Palworld engine crashed with Signal=11 on 2026-08-01 (container log 18:32:41, StartedAt=2026-08-01T22:32:42Z = 18:32:42 EDT), the engine's crash handler re-raised the signal, and docker's unless-stopped policy restarted the container (RestartCount=1). Any players online at the time were kicked. It is now Up 19h (healthy) with 2 players online and 59fps, so recovery worked, but nothing watches for crash recurrence below the RestartCount>3 restart-loop threshold, and the crash handler could not attach Pal.log (file missing), so the crash left no engine-side diagnostics. Preflight noted RestartCount=1; this session confirms the cause is an engine segfault, not an operator restart. Single occurrence in 27h of host uptime — watch, don't panic. NOT fixed per read-only mandate; no open task covers Palworld crash monitoring.

<details><summary>Evidence</summary>

```
ssh rig 'docker inspect palworld --format "RestartCount={{.RestartCount}} StartedAt={{.State.StartedAt}} OOMKilled={{.State.OOMKilled}}"; docker logs --since 24h palworld 2>&1 | grep -iE "error|crash|killed|restart" | head -8'
RestartCount=1 StartedAt=2026-08-01T22:32:42.284044791Z OOMKilled=false
unless-stopped
[283:283:20260801,183241.387421:ERROR file_io_posix.cc:145] open /palworld/Pal/Saved/Logs/Pal.log: No such file or directory (2)
[283:283:20260801,183241.387452:ERROR crash_report_exception_handler.cc:284] attachment /palworld/Pal/Saved/Logs/Pal.log couldn't be opened, skipping
CommonUnixCrashHandler: Signal=11
Engine crash handling finished; re-raising signal 11 for the default handler. Good bye.
ssh rig 'docker ps -a --format "table {{.Names}}\t{{.Status}}" | grep palworld'
palworld                  Up 19 hours (healthy)
```

</details>

### SM26. HotD S02E07 wedged at 100% in state=Downloading since Jul 30 — move_completed never fired, file stranded in files/ root, sonarr sees 'downloading' forever

**Host:** seedbox · **Component:** deluge move_completed / state machine · **Auditor:** flow:movies-tv · **Work item:** `fix-54`

House.of.the.Dragon.S02E07 is 100.00% complete in deluge but state=Downloading (seeds=0 peers=0, age 3.4d), so the move_completed relocation to files/tv never triggered; the 2.3GB mkv sits in /home/hd34/btabaska/files/ root (Jul 30 10:52) where sonarr's /seedbox/tv remote path never sees it. Sonarr queue shows it as plain 'downloading | ok' — invisible to the stuck-warning checks. Two more HotD files (S03E05 Jul 23, S03E06 Jul 27) are also stranded unmoved in files/ root — same failure mode, older. NOT fixed per read-only mandate (needs force-recheck/resume of the torrent, or manual import).

<details><summary>Evidence</summary>

```
seedbox deluge RPC: sonarr 100.00% Downloading mc=True mcp=/home/hd34/btabaska/files/tv sp=/home/hd34/btabaska/files/ seeds=0 peers=0 :: House.of.the.Dragon.S02E07.1080p.MAX.WEB-DL.DDP5
ssh seedbox 'ls -la /home/hd34/btabaska/files/ | grep -iE "house|dragon"'
-rw-r--r-- 1 btabaska hd34 2295794517 Jul 30 10:52 House.of.the.Dragon.S02E07.1080p.MAX.WEB-DL.DDP5.1.x264-NTb.mkv
-rw-r--r-- 1 btabaska hd34 4829212556 Jul 23 17:30 House.of.the.Dragon.S03E05.1080p.AMZN.WEB-DL.DDP5.1.H.264-playWEB.mkv
drwxr-xr-x 3 btabaska hd34 4096 Jul 27 03:06 House.of.the.Dragon.S03E06.1080p.WEB.h264-ETHEL
sonarr queue: | downloading | downloading | ok | House.of.the.Dragon.S02E07… | (no warning)
```

</details>

### SM27. bitmagnet-torznab-via-prowlarr TIMEOUT verified: searches take ~23s direct, exceeding 60s under concurrent arr load (seed-12 regression)

**Host:** nas · **Component:** bitmagnet (container, :3333) via prowlarr · **Auditor:** flow:movies-tv · **Work item:** `fix-50`

Reproduced live at ~15:40 EDT: bitmagnet torznab caps answers in 0.49s but a real tvsearch (q=leverage) takes 22.9s directly on the NAS — with both arrs hammering it every 30-60min (see the grab-storm finding) the prowlarr-proxied check plausibly exceeds its 60s limit, matching today's 10:23 'TIMEOUT after 60s'. Containers bitmagnet + bitmagnet-postgres Up 5 days, healthy. Regression of seed-12 (in today's reopen-suggestions). Interacts with the storm finding: the same slow indexer is the arrs' only active grab source right now.

MERGED duplicate from repo:verification-suite (M61): bitmagnet-torznab-via-prowlarr chronically dies at the 60s runner timeout — inner curls are unbounded and a live DHT search cannot fit the default budget — The check performs an ssh to NAS (key scrape), an unbounded 'curl -s' to Prowlarr's indexer list, then an unbounded real Torznab search through Prowlarr into Bitmagnet — with no '-m' on either curl and no per-check 'timeout:' override, all inside the 60s default. It exited 124 'TIMEOUT after 60s' in both today's 10:23 run and the 13:01 audit sweep. Because the kill is external (subprocess timeout), the output is empty of diagnosis: nobody can tell whether Bitmagnet is degraded, Prowlarr is slow, or the search genuinely needs 90s — the consumer-chain check seed-12 built now reports 'state unknown' daily and feeds seed-12 into reopen-suggestions without evidence. NOT fixed per read-only mandate (fix: '-m' per curl with distinct failure strings + 'timeout: 120' on the check so a real answer or a named failing stage always comes back).

<details><summary>Evidence</summary>

```
printf '%s\n' "$PW" | ssh nas 'sudo -S sh -c "curl -s -m 30 -o /dev/null -w \"http=%{http_code} t=%{time_total}s\" http://localhost:3333/torznab/api?t=caps ; curl -s -m 90 -o /dev/null -w … \"http://localhost:3333/torznab/api?t=tvsearch&q=leverage\""'
== caps: http=200 t=0.490297s
== tv-search q=leverage: http=200 t=22.917611s
== container: bitmagnet Up 5 days / bitmagnet-postgres Up 5 days (healthy)
results.json 2026-08-02T10:23: bitmagnet-torznab-via-prowlarr | fail | TIMEOUT after 60s
prowlarr indexer cfg: Bitmagnet baseUrl = http://192.168.10.4:3333/torznab (enabled)
--- (merged lane repo:verification-suite) ---
# results.json 10:23:
==== bitmagnet-torznab-via-prowlarr status=fail exit=124 dur=60.11
TIMEOUT after 60s
# also failing identically in /tmp/verify-audit/sweep-run.json 13:01 (fail_both)
# cmd (media-indexers.yaml lines 40-52): K=$(ssh ... nas grep ApiKey ...); ID=$(curl -s -H "X-Api-Key: $K" http://192.168.10.4:9696/api/v1/indexer | ...); N=$(curl -s ... "/api/v1/search?query=1080p&indexerIds=$ID&limit=5" | ...)
# neither curl carries -m; check has no timeout: field → 60s default (checks_runner.py CHECK_TIMEOUT=60)
```

</details>

### SM28. Preimport-stuck set churned hard since 10:23: 5 of the named 17 removed from deluge entirely; live >48h count now 9 — none are media-09/media-10 known territory

**Host:** seedbox · **Component:** deluge pre-import labels / deluge-preimport-stuck check · **Auditor:** flow:movies-tv · **Work item:** `fix-54`

At 10:23 the check reported PREIMPORT_STUCK 17 naming To.Wong.Foo, Pride.2014, Baby.Driver, Mission.Impossible.Fallout, Bobs Burgers S16E04; by ~15:20 EDT none of those exist in deluge under ANY label (not relabeled — removed), while fresh bitmagnet grabs refill the pre-import set (21 labeled now, 9 at 100% older than 48h: Better.Off.Ted 3.6d, Super Mario/Sinners/Borderlands 3.4d, AKotSK E03 3.3d, Passengers 3.3d, plus lidarr Charli XCX 4.8d and bookshelf 'Adrift' epub 12.7d — those two belong to the music/books lanes). Zero of the 17 match media-09's five unextractable titles (Matrix Resurrections/Animaniacs/Castle in the Sky/Addams Family/Intouchables) and no plain 'readarr' labels remain (media-10 drained), so this is all NEW churn, consistent with the grab-storm + missing-content findings; the removals suggest a concurrent remediation session or arr-side removal worth reconciling. fix-25 regression umbrella.

<details><summary>Evidence</summary>

```
results.json 10:23: deluge-preimport-stuck | fail | PREIMPORT_STUCK 17: [radarr] To.Wong.Foo…; [radarr] Pride.2014…; [radarr] Baby.Driver…; [radarr] Mission.Impossible.Fallout…; [sonarr] www.UIndex.org - Bobs Burgers S16E04…
seedbox deluge RPC ~15:20 EDT (needle search To.Wong.Foo/Pride.2014/Baby.Driver/Mission.Impossible.Fallout/Bobs Burgers S16E04): only leverage.redemption matches returned — the five are gone from the session
live pre-import scan: total_preimport_labeled=21; >48h at 100%: bookshelf Adrift 12.7d; lidarr Charli XCX 4.8d; sonarr Better.Off.Ted 3.6d; radarr Super.Mario/Sinners/Borderlands 3.4d; sonarr AKotSK E03 3.3d; radarr Passengers 3.3d
tasks.json media-09 summary: five residual titles = Matrix Resurrections, Animaniacs S03E01-06, Castle in the Sky, The Addams Family, The Intouchables (no overlap)
```

</details>

### SM29. Soularr failed-import backlog has grown to 6 albums permanently skipped; Camera + Heat Waves cycling >stale threshold (fix-40 regression)

**Host:** nas · **Component:** soularr + lidarr import path · **Auditor:** flow:music · **Work item:** `fix-56`

Check nas-soularr-failed-imports-fresh fails (stale=2 cycling=yes Camera, Heat Waves — fix-40 regression; 'Camera' is the same record from the media-11 history). Live soularr logs at 13:19 EDT today show the skip list is actually 6 albums: Cardi B - AH HA (6048), Lana Del Rey - Born to Die (5333), Charli xcx - Camera (6043), Glass Animals - Heat Waves (6044), Linkin Park - One More Light (5398), Lana Del Rey - Video Games (5323). Three of those are also the lidarr-incomplete-albums partial=3 failures (fix-28 regression: One More Light 9/10, Born to Die 17/24, Video Games 3/4). Additionally the Lidarr queue holds 2 completed-but-importFailed downloads ('One or more tracks expected in this release were not imported'): Daft Punk - Homework (Remixes) and Charli XCX - Brat — pattern #4 grabbed-but-never-imported. Albums are stuck wanted; tracks exist partially on disk; nothing self-heals. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
printf '%s\n' "$PW" | ssh nas 'sudo -S /usr/local/bin/docker logs soularr --tail 60 2>&1 | grep "Skipping failed import"'
[INFO|soularr|L414] 2026-08-02T13:19:21-0400: Skipping failed import album: Cardi B - AH HA (ID: 6048)
[INFO|soularr|L414] 2026-08-02T13:19:21-0400: Skipping failed import album: Lana Del Rey - Born to Die (ID: 5333)
[INFO|soularr|L414] 2026-08-02T13:19:21-0400: Skipping failed import album: Charli xcx - Camera (ID: 6043)
[INFO|soularr|L414] 2026-08-02T13:19:21-0400: Skipping failed import album: Glass Animals - Heat Waves (ID: 6044)
[INFO|soularr|L414] 2026-08-02T13:19:21-0400: Skipping failed import album: Linkin Park - One More Light (ID: 5398)
[INFO|soularr|L414] 2026-08-02T13:19:21-0400: Skipping failed import album: Lana Del Rey - Video Games (ID: 5323)
K=$(ssh mini 'sudo grep "^LIDARR_API_KEY=" /etc/verification/env' | cut -d= -f2)
curl -s -H "X-Api-Key: $K" "http://192.168.10.4:8686/api/v1/queue?pageSize=30" | python3 (parse)
queue total: 2
Daft Punk - Homework (Remixes) (2LP) (2022) [24-96 FLAC | completed | importFailed | ['One or more tracks expected in this release were not importe', '01. Around The World - I-Cube Remix.flac']
Charli XCX - Brat (2024) [FLAC] 88 | completed | importFailed | ['One or more tracks expected in this release were not importe', '01. 360.flac']
results.json 2026-08-02T10:23: lidarr-incomplete-albums | fail | ALBUMS_BAD partial=3 :: 'Linkin Park - One More Light(9/10)' 'Lana Del Rey - Born to Die(17/24)' 'Lana Del Rey - Video Games(3/4)'
```

</details>

### SM30. Three junk Chinese-titled MusicBrainz albums monitored under Charli xcx — soularr grinds and fails on them every 5-minute cycle indefinitely

**Host:** nas · **Component:** lidarr / soularr wanted-list hygiene · **Auditor:** flow:music · **Work item:** `fix-56`

Lidarr wanted/missing contains monitored=True albums '莉查' (id 6046), '呼啸山庄' (6045), '古 惑-狼豪 华版' (6047) attributed to Charli xcx — junk/bootleg MusicBrainz releases attached to the artist (same generator class as musicseerr monitor-everything artifacts, pattern #5 adjacent). Every 5-minute soularr cycle searches Soulseek for each, selects a bogus release, logs 'Failed to enqueue' twice (flac then mp3), and reports '3 releases failed to find a match and are still wanted' — unbounded retry churn with no backoff or dead-letter, wasting Soulseek search quota and polluting logs. No check or open task covers junk-release monitoring; NOT fixed per read-only mandate (fix = unmonitor/delete the 3 albums, add a guard for non-official releases).

<details><summary>Evidence</summary>

```
curl -s -H "X-Api-Key: $K" "http://192.168.10.4:8686/api/v1/wanted/missing?pageSize=40" | python3 (parse)
wanted missing total: 9
'莉查' | artist: Charli xcx | monitored: True | id: 6046
'呼啸山庄' | artist: Charli xcx | monitored: True | id: 6045
'古 惑-狼豪 华版' | artist: Charli xcx | monitored: True | id: 6047
soularr log 2026-08-02T13:19 EDT:
[INFO|soularr|L455] Searching for album: 古 惑-狼豪 华版
[INFO|soularr|L236] Selected release for Charli xcx: Official, [Worldwide], Digital Media, Mediums: 1, Tracks: 16, ID: 21305
[INFO|soularr|L621] Failed to enqueue Charli xcx - 古 惑-狼豪 华版  (repeats for flac then mp3, for all 3 albums)
[INFO|soularr|L1441] 3: releases failed to find a match in the search results and are still wanted.
02/08/2026 13:19:48 - Waiting for 300 seconds before checking again...
```

</details>

### SM31. docker logs calibre-web-automated hangs indefinitely (--since 24h >120s, --tail 400 >90s) while docker ps answers instantly

**Host:** nas · **Component:** docker json-log / calibre-web-automated · **Auditor:** flow:books · **Work item:** `fix-55`

Two consecutive read-only sudo docker logs attempts against calibre-web-automated on 2026-08-02 had to be killed by timeout (--since 24h at 120s, then the much lighter --tail 400 at 90s), while a control sudo docker ps on the same recipe returned instantly showing the container Up 5 days (healthy). A logs-specific hang with a healthy daemon fits the taxonomy #15 json-log corruption / oversized-log-line class and means log-based debugging and any future log-scraping check for CWA is dead. The hung probe is filed as evidence per sweep rules rather than retried further. NOT fixed per read-only mandate (likely needs log file inspection / rotation during a maintenance window).

<details><summary>Evidence</summary>

```
printf '%s\n' "$PW" | ssh nas 'sudo -S -p "" /usr/local/bin/docker logs calibre-web-automated --since 24h 2>&1 | grep -iE "kobo|store|proxy" | tail -15'
-> Command timed out after 2m 0s (exit 143)
printf '%s\n' "$PW" | ssh nas 'sudo -S -p "" /usr/local/bin/docker logs calibre-web-automated --tail 400 2>&1 | grep -iE "error|warn|store|proxy" | tail -12'
-> Command timed out after 1m 30s (exit 143)
printf '%s\n' "$PW" | ssh nas 'sudo -S -p "" /usr/local/bin/docker ps --filter name=calibre --format "{{.Names}} {{.Status}}"'
-> calibre-web-automated Up 5 days (healthy)
-> PS_DONE   (returned in ~3s)
```

</details>

### SM32. Kobo sync payload for BOTH devices contains a stray bare-string element 'ResponseStatus'; kobo metadata endpoint answers in 6.7-23.8s (>15s timeouts observed)

**Host:** nas · **Component:** calibre-web-automated Kobo sync (store passthrough) · **Auditor:** flow:books · **Work item:** `fix-57` · *skeptic-confirmed*

Live GET of both vault-held device sync URLs (cwa.kobo_api_endpoint_admin, cwa.kobo2_api_endpoint) on 2026-08-02 returns a JSON list of 82 elements: 81 proper dicts (4 NewEntitlement + 77 ChangedReadingState) plus one literal string 'ResponseStatus' — the signature of a dict (likely an upstream Kobo-store error object {'ResponseStatus':...} from the proxy=1 store passthrough) being list-extend'ed into the sync results, i.e. the upstream store leg is erroring while local sync stays green. cwa-kobo-sync-consumer passes because it only asserts 200 + json.load succeeds (taxonomy #2 green-but-suspect), and cwa-kobo-proxy-intent only checks the proxy flag, not upstream health. Separately, /v1/library/<uuid>/metadata took 23.8s and 6.7s on consecutive calls and timed out twice at 15s — a real device tapping a book detail/cover sits near client-timeout territory. Root cause (store-proxy merge) is inferred, not proven from code; log confirmation was blocked by the docker-logs hang filed separately. NOT investigated further per read-only mandate.

*Verify note:* CONFIRMED, and mechanism upgraded from inferred to proven. Fresh probes 2026-08-02: both device sync URLs return 200 with 82-element list = 81 ChangedReadingState dicts + bare string 'ResponseStatus' (identical contamination on admin + kobo2). Latency is WORSE than filed: the /v1/library/sync leg itself (not just metadata) took 29.8s/20.7s and timed out twice at a 30s ceiling on first attempt — real devices sync at the edge of the deployed check's own curl -m 30. Root cause proven from deployed code (container /app/calibre-web-automated/cps/kobo.py, generate_sync_response): `sync_results += store_response.json()` — when the upstream Kobo store returns an error dict {'ResponseStatus':...} instead of a list, += iterates dict keys and injects the bare string; the blocking make_request_to_kobo_store call in the same path explains the 20-30s latency (upstream store leg erroring/slow while local sync stays green). Check gap confirmed: reading.yaml cwa-kobo-sync-consumer asserts only 200+json.load (passes through contamination); cwa-kobo-proxy-intent only checks the flag. Severity medium stands; fix should surface upstream-store failure (type-check store_sync_results is a list before merge, log/alert on ResponseStatus) and the consumer check should assert all sync elements are dicts.

<details><summary>Evidence</summary>

```
U=$(python3 -c "...['cwa']['kobo_api_endpoint_admin']")  # vault; URL embeds token, never printed
python3: GET $BASE/v1/library/sync (UA Kobo/4.38)  -> sync_http=200 type=list len=82
  entry kinds: NewEntitlement=4 ChangedReadingState=77 + non_dict_entries=['ResponseStatus']
same probe on cwa.kobo2_api_endpoint -> kobo2_sync: total=82 non_dict_entries=['ResponseStatus']
GET $BASE/v1/library/3790d4c9-e07e-4a34-a6fd-bfb226037101/metadata timeout=15 -> TIMEOUT (twice, both books)
retry timeout=45 -> control_metadata: http=200 elapsed=23.8s CoverImageId=SET Title='How to Do Nothing'
retry book99   -> book99_metadata: http=200 elapsed=6.7s CoverImageId=SET DownloadUrls=1 Title='Wuthering Heights'
10:23 daily run: cwa-kobo-sync-consumer pass KOBO_SYNC_OK; cwa-kobo-proxy-intent pass proxy=1 sync=1
```

</details>

### SM33. Rig booted 2026-08-01 with clock 4h behind (RTC held local time); journal timeline false and all persistent timers delayed until NTP jump

**Host:** rig · **Component:** system clock / RTC (surfaced via abs-ipod-stage.timer) · **Auditor:** flow:audiobooks-ipod · **Work item:** `fix-64` · *skeptic-confirmed*

The Aug 01 boot journal starts at 10:25:27-10:25:38 EDT, then every persistent/periodic timer (abs-ipod-stage, AI-stack watchdog, Bedrock UDP probe, user timers) plus the first user sessions all fire in the same second at 14:26:04 -- a +4h00m clock jump exactly equal to the EDT/UTC offset, meaning the RTC contained local time interpreted as UTC at boot (actual boot was ~14:25 EDT). Consequences: the preflight's 'rig ~23h powered off' window is really ~27h (Jul 31 11:07 -> Aug 01 ~14:25 EDT); the abs-ipod-stage Persistent=true catch-up looked 4h late but actually ran at boot; any early-boot time-dependent logic ran 4h in the past; journal timelines for that boot are unauditable. timedatectl now shows RTC in UTC and synchronized, so something during the off-window (most plausibly a Windows dual-boot session, which writes RTC as localtime by default) skewed the RTC, and NTP has since rewritten it -- recurrence is likely on the next such boot. Not covered by any open task. NOT fixed per read-only mandate (candidate fixes: Windows RealTimeIsUniversal registry key, or accept and document the skew). ORCHESTRATOR CONFIRMATION: the 4h step is visible live in the boot-0 journal (tailscaled 'slept 4h0m14s' at stamped 14:26:08, immediately after avahi re-registration) — every pre-step journal timestamp this boot is 4h early, which also falsified the sweep's own outage forensics until cross-checked against mini. Durable fix direction: RTC localtime/UTC config (timedatectl set-local-rtc 0) + NTP-sync-before-timers ordering.

*Verify note:* CONFIRMED with stronger evidence than the auditor had. Fresh probes on rig boot 2fab5bab (Aug 01): (1) kernel at monotonic 1.61s logged "rtc_cmos: setting system clock to 2026-08-01T14:25:26 UTC" — the RTC held the local (EDT) value interpreted as UTC, the exact claimed mechanism; (2) systemd-timesyncd at monotonic 39.56s logged "Initial clock synchronization to Sat 2026-08-01 14:26:04.600275 EDT" — the +4h00m step, explaining the mass 14:26:04 timer/session stamps (realtime timers whose elapse points fell in the skipped 4h all fired on the step); (3) independent monotonic cross-check: wall 10:25:27→14:26:04 spans monotonic 1.6s→39.6s, proving a clock step, not idle time — the boot journal timeline is genuinely false; (4) efibootmgr shows Boot0000 "Windows Boot Manager" on the rig, making the Windows-localtime-RTC cause and recurrence risk credible; (5) prior boot ended Jul 31 11:07:16 EDT and true boot was ~14:25 EDT Aug 01, so the off-window was ~27.3h as claimed; timedatectl now shows RTC==UTC (NTP rewrote it), so skew recurs after the next Windows session. Nuance: network came up fast this boot so timers were only ~40s late in practice — impact is the falsified journal timeline, miscounted off-window, and recurrence (worse on a boot without network). Severity medium is appropriate; no change.

<details><summary>Evidence</summary>

```
ssh rig 'journalctl --since "2026-08-01 10:25" --until "2026-08-01 14:30" --no-pager | grep -iE "clock"'
Aug 01 10:25:27 cachyos kernel: clocksource: Switched to clocksource tsc   # boot logs 10:25:27-10:25:38, then NOTHING until:
ssh rig 'journalctl --since "2026-08-01 14:25" --until "2026-08-01 14:28" --no-pager | grep -iE "Starting|Started" | head'
Aug 01 14:26:04 cachyos systemd[934]: Starting Timed resync...
Aug 01 14:26:04 cachyos systemd[1]: Starting AI stack watchdog: container->host ollama hop -> healthchecks dead-man...
Aug 01 14:26:04 cachyos systemd[1]: Starting End-to-end Bedrock UDP tunnel probe + playit self-heal (fix-34 M30)...
Aug 01 14:26:04 cachyos systemd[1]: Starting Stage Audiobookshelf audiobooks+podcasts as iPod-ready media (~/Audiobooks .m4b, ~/Podcasts)...
Aug 01 14:26:04 cachyos systemd[1]: Started Session 4 of User btabaska.
ssh rig 'who -b'
         system boot  2026-08-01 10:25
ssh rig 'timedatectl'
               Local time: Sun 2026-08-02 13:23:41 EDT
                 RTC time: Sun 2026-08-02 17:23:41
          RTC in local TZ: no
System clock synchronized: yes
# 14:26:04 - 10:25:38 = 4h00m26s = exactly the EDT/UTC offset; mass simultaneous timer+session start = realtime step, not workload
```

</details>

### SM34. Manga-chain checks green while both ends of the chain are broken — thresholds too shallow (series>=1, host-side mount touch)

**Host:** fleet · **Component:** verification checks suwayomi-feeds-komga / komga-libraries-consumer · **Auditor:** flow:manga-comics · **Work item:** `fix-58`

Both checks passed the 10:23 daily run (SUWAYOMI_OK ... komga_manga_series=1, KOMGA_OK libraries=2 series=3 books=14) while (a) Komga has not scanned the Manga library since 07-23 and (b) the Suwayomi container is disconnected from the CIFS store since 08-01. suwayomi-feeds-komga asserts only series>=1 in the Manga library (the 07-23 Yotsuba&! book satisfies it forever) and touches /mnt/nas-manga from the rig HOST shell, not from inside the container. komga-serves.py streams a page from books?size=1 (default sort, not newest) and never compares newest-on-disk vs newest-indexed. Textbook standing-mandate-1 / pattern #2+#13 masking. Needed: disk-newest-vs-Komga-indexed lag assertion and a container-side (docker exec ls) mount probe. NOT changed per read-only mandate.

<details><summary>Evidence</summary>

```
$ ssh mini 'python3 -c ...' /var/lib/verification/results.json (10:23 EDT run):
komga-libraries-consumer | pass | KOMGA_OK libraries=2 series=3 books=14 page=200 opds=200
suwayomi-feeds-komga | pass | SUWAYOMI_OK suwayomi=v2.3.2243 mount=rw komga_manga_series=1
$ ssh mini 'grep -nE "komga_manga_series|series" /opt/verification/bin/suwayomi-feeds-komga.py'
57:    remote = ("mountpoint -q /mnt/nas-manga "
58:              "&& touch /mnt/nas-manga/%s && rm -f /mnt/nas-manga/%s "   # host-side, not container-side
85:    n = series.get("totalElements", 0)   # passes at >=1 forever
Meanwhile live: 279 cbz on /volume1/manga (newest 07-27 19:50) vs 1 book indexed in Komga Manga lib; container-side downloads dir empty.
```

</details>

### SM35. NAS is I/O-saturated (load 15-20, 78.6% iowait) with no scrub or userland D-state culprit — degrading photo consumers and killing verification checks

**Host:** nas · **Component:** DS920+ storage / IO · **Auditor:** flow:photos · **Work item:** `fix-55` · *skeptic-confirmed*

At 13:28 EDT load average was 20.18/14.64/8.73 with IO-load 18.90 and top showing 78.6% wa, 901 tasks, 4.6GB swap in use. /proc/mdstat sync_action=idle on all arrays (not a scrub), and the only D-state processes are kernel workers (jbd2, md3_raid1, kworkers). This pressure is not momentary: the 10:23 daily run had two NAS-path checks TIMEOUT (nas-immich-backup-freshness, bitmagnet-torznab-via-prowlarr) and my probes 3h later still starved. Consumer impact in this lane: warm smart-search latency measured 13.0s vs the ~225ms warm figure documented in immich-ml-window.sh, and a cold/loaded request exceeded 30s. Source unidentified within read-only budget (candidates: swap thrash on 19.4GB box, a DSM background task, or concurrent sweep lanes) — worth a dedicated look before more checks get raised timeouts to paper over it. ORCHESTRATOR FOLLOW-UP (gap:nas-io-rootcause, ~16:50 EDT): load is back to 2.84 with zero D-state processes, no md resync (mdstat clean), no btrfs scrub running, no SMART self-test in progress — so the 13:2x saturation was partly the sweep's own NAS-heavy lanes (observer effect). The CHRONIC component is real and predates today: 1254 lidarr 'database is locked' errors span 30h, daily 10:23 check TIMEOUTs recur, and bitmagnet is the top steady CPU/IO consumer (11.4% CPU at idle-ish load with its DHT crawler + postgres churn). Root-cause session should measure per-container blkio over a quiet window before changing anything.

<details><summary>Evidence</summary>

```
ssh nas 'uptime'
 13:28:40 up 30 days, 21:50, 0 users, load average: 20.18, 14.64, 8.73 [IO: 18.90, 13.63, 7.89 CPU: 1.28, 1.00, 0.83]
ssh nas 'top -bn1 | head -5'
%Cpu(s):  4.8 us,  6.0 sy,  0.0 ni, 10.7 id, 78.6 wa,  0.0 hi,  0.0 si,  0.0 st
GiB Mem :   19.387 total,    2.869 free,    7.172 used,    9.346 buff/cache
GiB Swap:   13.633 total,    9.010 free,    4.623 used.
ssh nas 'for m in /sys/block/md*/md/sync_action; do echo "$m=$(cat $m)"; done'
all five: sync_action=idle
ssh nas 'ps ax -o pid,stat,etime,args | awk "\$2 ~ /^D/"'
only [kworker/u8:0], [jbd2/md0-8], [md3_raid1], [kworker/u8:2]
curl -s -m 60 -w 'HTTP=%{http_code} time=%{time_total}s' https://immich.tabaska.us/api/search/smart ... -d '{"query":"beach","size":3}'
HTTP=200 time=13.037951s   (an identical earlier attempt with -m 30 returned empty = >30s)
printf .. | ssh nas 'sudo -S sh -c "cat /proc/loadavg; cat /proc/mdstat | head; ps axo pid,stat,pcpu,comm | awk \"\$2 ~ /D/\"; btrfs scrub status /volume1" 2>/dev/null'
2.84 3.87 3.61 3/2559 28317
md2/md3/md4 all [1/1] [U], md0/md1 [4/3] [UUU_] (4-bay chassis, 3 data disks — DSM-normal)
(no D-state processes)
scrub started Fri Sep 26 2025 ... finished (not running)
top CPU now: bitmagnet 11.4%, immich 6.3%, rclone 5.8%, jellyfin 2.1%
```

</details>

### SM36. Second household Immich user has 0 photos and 0 videos ever — her phone backup has never flowed, and no check can catch it

**Host:** nas · **Component:** immich / user Kaelyn Tabaska · **Auditor:** flow:photos · **Work item:** `fix-60` · *skeptic-confirmed*

Server statistics at 13:29 EDT show user Kaelyn Tabaska (userId b6be5585-152e-4330-86d2-f52a397ed706) with photos=0 videos=0 usage=0, and /volume1/photo/upload contains only Brandon's user directory (936853a2..., mtime Jul 22). Taxonomy #13 zero-throughput: the account exists but the backup pipeline for it has never delivered a single asset. The nas-immich-backup-freshness check is global (any file in 7 days) so it structurally cannot detect a single-user stall — Brandon's uploads keep it green forever. Either her mobile app was never configured/logged in, or onboarding was never finished. No open task covers her onboarding (nas-08b is the SD-card immich-go import, a different pipeline).

*Verify note:* CONFIRMED with fresh probes. (1) statistics API re-run: Kaelyn photos=0 videos=0 usage=0 (Brandon 34601/1340); (2) NAS disk: /volume1/photo/upload has exactly 1 dir (Brandon's, Jul 22) — none for b6be5585; (3) independent admin-API probe: her account is active, created 2026-07-14, never deleted — 0 assets in ~19 days of existence; (4) checks.d read confirms nas-immich-backup-freshness asserts only global photos+videos>0 + any file <7d, so Brandon's flow keeps it green regardless of her stall; nas-immich-mobile-paired is retired (enabled:false). Detail correction worth carrying into the fix queue: this is not a silent regression — fix-35 (2026-07-18) recorded pairing as deliberately deferred and nas-31's 2026-07-28 closure noted "re-pairing native app = needs-human", but that note lives in a CLOSED task and never became a tracked item, and it predates Brandon's own (web-upload) flow starting. Remediation frame: file the needs-human Kaelyn-onboarding task + add a per-user freshness/asset-count check, rather than treating it as a fresh outage. Severity medium stands.

<details><summary>Evidence</summary>

```
curl -s -m 20 https://immich.tabaska.us/api/server/statistics -H "x-api-key: $KEY"  # KEY = vault immich.verify_api_key
Brandon Tabaska photos= 34601 videos= 1340
Kaelyn Tabaska photos= 0 videos= 0
ssh nas 'ls -lt /volume1/photo/upload | head'
total 0
drwxrwxrwx+ 1 root root 1024 Jul 22 18:25 936853a2-657c-4796-a90e-2adc27df16d1
(no upload dir for user b6be5585-152e-4330-86d2-f52a397ed706)
```

</details>

### SM37. A #journal tag added by editing a memo after creation is silently never analyzed — real entry (memo 36, 2026-07-23) permanently has no reflection

**Host:** mini · **Component:** n8n journal-analyze workflow (Guard: loop-safe filter node) · **Auditor:** flow:journaling · **Work item:** `fix-67` · *skeptic-confirmed*

The Guard node drops every event that is not memos.memo.created ('if (activity !== "memos.memo.created") return [];') and gates on the memo.tags array carried in that event. Memo 36 (#journal, PRIVATE) was created 2026-07-23 16:44:57Z and edited 43s later (updated_ts 16:45:40Z); both matching executions (85 at creation, 86 at the edit) exited 'success' in ~24ms without analyzing — compare ~3s for genuinely analyzed memos — and memo 36 has zero reflection comments today. Most parsimonious cause: the tag was added by the edit, and update events are dropped by design, so the entry is permanently skipped with no retry/backfill; even if the tag was present at creation, the observed behavior means the loop dropped a tagged entry silently. 1 of 4 real #journal memos in the last 14 days lost its reflection this way. journal-06's e2e only exercises the created-event path so this stays invisible to monitoring. NOT fixed per read-only mandate; not covered by any open task — needs a new work item (handle memo.updated with the same loop guards, or a periodic backfill for tag-bearing memos with zero reflection comments).

*Verify note:* CONFIRMED and mechanism upgraded from "most parsimonious" to proven. Re-probed: (1) Guard code in repo workflow drops activity !== memos.memo.created then gates on tags.includes('journal'); (2) memos_prod.db ro: memo 36 created 16:44:57 / updated 16:45:40 2026-07-23, #journal content, 0 comments, while memos 18/59/62 (created==updated) each have 1 reflection — 1 of 4 lost; (3) independent probe the auditor lacked — n8n execution_data payloads: exec 85 is memos.memo.created with NO tags key and no '#journal' in content (only URL matches; body 970B) so the tag gate correctly dropped it, exec 86 is memos.memo.updated carrying tags:["journal"] + '#journal \nJust got to spend time chatting...' (body 998B, delta = tag added by edit) and was dropped solely by the activity gate; contrast exec 80 (created + tags=journal) shows full LLM analysis. Tag was definitively added by the 43s-later edit; update events are dropped by design with no retry/backfill, so the entry is permanently skipped and journal-06's created-only e2e can never see it. Severity medium stands.

<details><summary>Evidence</summary>

```
repo foss-setup/configs/docker-stack/stacks/journaling/n8n/journal-analyze.workflow.json Guard node:
// 1) only entry-created events (drops memos.memo.comment.created outright)
if (activity !== 'memos.memo.created') return [];
// 2) must be a journal entry ... if (!tags.includes('journal...
ssh mini sudo python3 - # sqlite ro, memos_prod.db:
memo 36: {'created': '2026-07-23 16:44:57', 'updated': '2026-07-23 16:45:40', 'status': 'NORMAL', 'vis': 'PRIVATE'}; tag context: '#journal \nJust got t'; comment_count=0
analyzed memos for comparison: 18/59/62 all created==updated (never edited), each comment_count=1
ssh mini sudo python3 - # sqlite ro, n8n database.sqlite executions (UTC):
(85, 'success', '2026-07-23 16:44:57.561', '2026-07-23 16:44:57.585')  # memo 36 created event, 24ms quick-exit
(86, 'success', '2026-07-23 16:45:40.942', '2026-07-23 16:45:40.966')  # memo 36 edit event, 24ms quick-exit
(80, 'success', '2026-07-23 16:41:27.460', '2026-07-23 16:41:30.252')  # a real analysis for contrast, ~2.8s
```

</details>

### SM38. Alert-fatigue flapping: ~29 pages in 12h on the verification topic, dominated by pinchflat-plex-visible / radarr-movies-in-plex / sonarr-tv-in-plex crit flap cycles

**Host:** mini · **Component:** verification ntfy topic / fast+media tier checks · **Auditor:** flow:monitoring-alerting · **Work item:** `fix-61`

The verification ntfy topic cached 29 messages in the last 12h (~2.4/h sustained), mostly fast-tier NEW-failure/all-recovered pairs for the same three crit checks flapping all night (03:06, 03:37, 04:06, 04:57, 05:27, 06:06, 06:46, 07:06 EDT, plus 13:15 dns-mini-internal and 13:26 again). Each flap pages as crit and self-recovers within ~10 min, which trains the operator to ignore the primary alert topic — classic green-but-noisy masking (#2 adjacent). These checks map to verify-06 (named as reopen candidate in the messages themselves), which is in the regression set; the *-in-plex probes likely need retry/latency tolerance during overnight Plex activity. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
curl -s -u admin:<vault ntfy/admin_password> "https://ntfy.tabaska.us/verification/json?poll=1&since=12h" | python3 (count+bucket)
messages_last_12h_cached: 29
8 | Verification [fast tier]: all recovered
5 | Verification [fast tier]: 1 NEW failure(s)
3 | Verification [fast tier]: 3 NEW failure(s)
2 | Verification [fast tier]: 2 NEW failure(s)

sample cached messages (EDT):
03:37:34 [fast tier]: 3 NEW failure(s): pinchflat-plex-visible, radarr-movies-in-plex, sonarr-tv-in-plex / crit
03:45:50 [fast tier]: all recovered
06:46:13 [fast tier]: 1 NEW failure(s): sonarr-tv-in-plex / crit / reopen candidates: verify-06
06:56:45 [fast tier]: all recovered
13:15:29 [fast tier]: 1 NEW failure(s): dns-mini-internal / crit
13:26:45 [fast tier]: recovered: dns-mini-internal
```

</details>

### SM39. Monitoring gap: no synthetic alert-reached-a-device test — device delivery of pages is unproven (mandate 2)

**Host:** fleet · **Component:** verification/checks.d (alerting domain) · **Auditor:** flow:monitoring-alerting · **Work item:** `fix-63`

The alerting domain checks (foss-setup/verification/checks.d/alerting.yaml) verify ntfy health, the iOS upstream relay env var, Diun containers, Healthchecks state, Kuma and Beszel down-counts — but nothing proves a published message actually reaches an operator device (ntfy app subscription / iOS relay round-trip). Today's evidence shows publishes succeed server-side (subscribers=1 connection observed on the ntfy stats line), yet the last mile is untested; a silently logged-out phone app or broken upstream relay would look identical to today. No open task covers this. A safe design: a dedicated low-priority synthetic topic the phone subscribes to, with a delivery-receipt callback (e.g. ntfy poll from the device automation pinging a Healthchecks dead-man). Filed, not built, per read-only mandate.

<details><summary>Evidence</summary>

```
foss-setup/verification/checks.d/alerting.yaml enumerated: alert-ntfy-healthy, alert-ntfy-upstream-relay, alert-diun-mini-up, alert-diun-nas-up, alert-healthchecks-checks-defined, alert-healthchecks-none-down, alert-dsm-*, alert-kuma-none-down, alert-beszel-none-down — no device-delivery probe.
ssh mini 'docker exec ntfy sh -c "printenv | grep -i UPSTREAM"'
NTFY_UPSTREAM_BASE_URL=https://ntfy.sh
ntfy server stats line: subscribers=1, topics_active=4 (one live subscriber connection, delivery to device unverified)
```

</details>

### SM40. ansible-site-converged perpetual changed=1 root-caused: chezmoi apply task's creates: guard checks /root while running as btabaska (become/HOME mismatch)

**Host:** fleet · **Component:** ansible roles/state — 'Apply dotfiles with chezmoi (glue-04)' task · **Auditor:** flow:git-control-plane · **Work item:** `fix-65`

The daily changed=1 that fails ansible-site-converged-mini (fix-42 regression, in today's failing set) is the task 'state : Apply dotfiles with chezmoi (glue-04)' on BOTH mini (Aug 02 04:23, ok=41 changed=1) and rig (Aug 02 04:47, ok=29 changed=1). Mechanism, verified live: site.yml line 24 sets play-level become: true, so facts are gathered as root and ansible_env.HOME resolves to /root; the task (roles/state/tasks/main.yml lines 51-56) runs become: false as btabaska with creates: "{{ ansible_env.HOME }}/.local/share/chezmoi/.git" — it checks /root/.local/share/chezmoi/.git (does not exist) while the real source lives at /home/btabaska/.local/share/chezmoi/.git (exists since Jul 28). Result: 'chezmoi init --apply git@forgejo:home/dotfiles.git' re-executes every nightly pull, always reporting changed. Consequence: the convergence tripwire is permanently red on mini (masking any real drift it was built to catch) and dotfiles are force-re-applied nightly, silently clobbering any local edit on mini/rig. This is a second-generation fix-42 regression (fix-42 fixed a different phantom-changed in this same task; the repo comment at lines 36-41 documents that earlier fix). NOT fixed per read-only mandate; fix is resolving the user home correctly (e.g. lookup of the run user's passwd home) in the creates: guard.

<details><summary>Evidence</summary>

```
ssh mini 'journalctl -u ansible-pull.service --since "2026-08-02 04:00"' | awk '/TASK \[/{task=$0} /changed:/{print "CHANGED under -> " task; print} /ok=/{print}'
CHANGED under -> Aug 02 04:23:51 macmini bash[3599937]: TASK [state : Apply dotfiles with chezmoi (glue-04)] ***
Aug 02 04:23:51 macmini bash[3599937]: changed: [macmini]
macmini : ok=41 changed=1 unreachable=0 failed=0 skipped=13
ssh rig 'journalctl -u ansible-pull.service --since 2026-08-01' | (same awk)
CHANGED under -> Aug 02 04:47:07 cachyos bash[588144]: TASK [state : Apply dotfiles with chezmoi (glue-04)] ***
cachyos : ok=29 changed=1 unreachable=0 failed=0 skipped=25
grep -n 'become: true' foss-setup/configs/ansible/site.yml -> 24:  become: true
sed -n 51,56p foss-setup/configs/ansible/roles/state/tasks/main.yml
- name: Apply dotfiles with chezmoi (glue-04)
  become: false
  when: dotfiles_repo.rc == 0
  ansible.builtin.command:
    cmd: "chezmoi init --apply {{ chezmoi_repo }}"
    creates: "{{ ansible_env.HOME }}/.local/share/chezmoi/.git"
ssh mini 'systemctl cat ansible-pull.service | grep ^User; sudo ls -ld /root/.local/share/chezmoi/.git; ls -ld /home/btabaska/.local/share/chezmoi/.git'
User=btabaska
ls: cannot access '/root/.local/share/chezmoi/.git': No such file or directory
drwxr-xr-x 8 btabaska btabaska 4096 Jul 28 09:44 /home/btabaska/.local/share/chezmoi/.git
```

</details>

### SM41. Mac ssh-config three-layer drift: live config (tailnet + forgejo/rig-code hosts) ahead of a 25-day-uncommitted source edit, ahead of the committed template (LAN IPs, missing hosts)

**Host:** device · **Component:** chezmoi dotfiles — Mac ~/.ssh/config vs source template · **Auditor:** flow:git-control-plane · **Work item:** `fix-65`

Verified live 2026-08-02: chezmoi diff on the Mac shows two content-hunk files (not mode-bit flap): .config/nvim/lazy-lock.json and .ssh/config. The committed dotfiles template (forgejo/main 394188f) would revert the live Mac ssh config from tailnet hostnames (nas/macmini/cachyos.tailb31641.ts.net) back to LAN IPs and DROP the 'Host forgejo' and 'Host rig-code' entries entirely — and the Home repo's forgejo remote is git@forgejo:home/homelab.git, so a blanket chezmoi apply would break publish-deploy.sh's Forgejo push and the remote-coding alias. Additionally the source working tree has an uncommitted edit to private_dot_ssh/private_config (mtime Jul 8, 23+/29-) that survived two later commits (Jul 22) without being committed — so Forgejo's template, the Mac source tree, and the live config are three different states. The lazy-lock drift runs the other direction (source has newer nvim plugin pins, e.g. neo-tree v3.x, than live) but the Mac can never safely converge because the ssh-config clobber hazard blocks all applies. Not covered by any open task (glue-04 is done); the documented memory hazard mitigates accidental apply but the drift itself is unresolved. NOT fixed per read-only mandate.

MERGED duplicate from repo:live-drift (M57): Mac chezmoi source for .ssh/config is stale by 31 lines — an apply would delete the rig, rig-code, and forgejo SSH aliases — chezmoi diff on the operator Mac (2026-08-02 ~13:50 EDT) shows 31 changed content lines in .ssh/config: applying the source state would REMOVE Host rig, Host rig-code (the VSCodium remote-coding alias), and the forgejo push alias, and revert mini/nas HostNames from tailnet names back to LAN IPs. Live is correct; the chezmoi source in the dotfiles repo (Forgejo home/dotfiles) predates the remote-AI-coding and forgejo-key setup — a Mac rebuild from dotfiles would silently break rig remote coding and forgejo pushes. .config/nvim/lazy-lock.json also drifts by 38 lines. rig chezmoi diff is clean. This is the previously-noted 'never blanket chezmoi apply on Mac' hazard, now quantified as real source-side drift; no open task covers re-syncing the source. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
chezmoi diff | grep -E '^diff --git'
diff --git a/.config/nvim/lazy-lock.json b/.config/nvim/lazy-lock.json
diff --git a/.ssh/config b/.ssh/config
chezmoi diff | sed -n '/a\/.ssh\/config/,$p' | grep -E '^[-+]Host |^[-+] *HostName' | head -12
-    HostName nas.tailb31641.ts.net
+    HostName 192.168.10.4
-Host mini server
-    HostName macmini.tailb31641.ts.net
+Host server
+    HostName 192.168.10.2
-Host rig-code
-    HostName cachyos.tailb31641.ts.net
-Host forgejo
-    HostName macmini.tailb31641.ts.net
chezmoi git -- status --porcelain ->  M private_dot_ssh/private_config
chezmoi git -- diff --stat -> private_dot_ssh/private_config | 52 +++---- (23 insertions, 29 deletions)
stat -f '%Sm %N' ~/.local/share/chezmoi/private_dot_ssh/private_config -> Jul  8 08:11:46 2026
chezmoi git -- log -1 --format='%ci %h' -> 2026-07-22 21:51:45 -0400 394188f
cd ~/GitHub/Home && git remote -v | grep forgejo -> forgejo git@forgejo:home/homelab.git (push)
--- (merged lane repo:live-drift) ---
chezmoi diff | awk '/^diff --git/{f=$3} /^[+-][^+-]/{c[f]++} END{for(k in c) print k, c[k]" changed lines"}'
a/.config/nvim/lazy-lock.json 38 changed lines
a/.ssh/config 31 changed lines
chezmoi diff (target->source hunks, - = would be removed from live):
-Host rig
-    HostName cachyos.tailb31641.ts.net
-Host rig-code
-    HostName cachyos.tailb31641.ts.net
-Host mini server
-    HostName macmini.tailb31641.ts.net
+Host mini
+    HostName 192.168.10.2
-    HostName nas.tailb31641.ts.net
+    HostName 192.168.10.4
ssh rig 'which chezmoi && chezmoi diff | head -5; echo rig-chezmoi-diff-end'
/usr/bin/chezmoi
rig-chezmoi-diff-end
```

</details>

### SM42. HA offsite backup tars grant full write+delete to every NAS group including http and household

**Host:** nas · **Component:** /volume1/backups (HA offsite tars) · **Auditor:** flow:backups · **Work item:** `fix-53`

The Synology ACL on the newest HA backup (Automatic_backup_2026.7.2_2026-08-02_04.45_00003109.tar) allows rwxpdD (including write and delete) to groups administrators, media, users, http, and household — any NAS account or a compromised web service could silently delete or replace the only off-eMMC HA backup leg. Read exposure is mitigated because the tars are client-side encrypted (key at vault hosts.ha.backup_password), but integrity/availability is not. This is almost certainly among today's failing nas-worldwritable-sweep (warn, count=5) — a regression of fix-23 that needs a new work item. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh nas 'ls -la /volume1/backups/ | tail -6'
-rwxrwxrwx+ 1 ha-backup users 23562240 Aug  2 04:45 Automatic_backup_2026.7.2_2026-08-02_04.45_00003109.tar
printf '%s\n' "$PW" | ssh nas 'sudo -S -p "" sh -c "/usr/syno/bin/synoacltool -get /volume1/backups/Automatic_backup_2026.7.2_2026-08-02_04.45_00003109.tar"'
 [0] group:administrators:allow:rwxpdDaARWc--:----
 [1] user:ha-backup:allow:rwxpdDaARWc--:----
 [2] group:media:allow:rwxpdDaARWc--:----
 [3] group:users:allow:rwxpdDaARWc--:----
 [4] group:http:allow:rwxpdDaARWc--:----
 [5] group:household:allow:rwxpdDaARWc--:----
```

</details>

### SM43. No restore drill has ever been run on any backup leg — every leg is write-verified only `known-issue`

**Host:** fleet · **Component:** backup restore drills (all legs) · **Auditor:** flow:backups

All six legs (restic mini/rig -> B2, NAS Hyper Backup -> B2, Immich pg dump, HA -> NAS tars, AMP zips, ludusavi/Syncthing saves) are verified fresh today, and restic additionally runs a structural 'restic check' after each backup (no errors, both hosts, 2026-08-02). But no leg has a documented restore-to-file drill: the Hyper Backup client-side-encrypted set, the encrypted HA tars, and the Immich dumps have never been restore-tested, so key custody and archive integrity at the consumer end are unproven. Covered by open task sbom-05 (restore runbooks + rebuild drill; glue-06 is the capstone).

<details><summary>Evidence</summary>

```
ssh mini 'journalctl -u restic-backup --since -48h --no-pager | tail'
Aug 02 01:41:09 macmini restic-backup.sh[3339702]: check snapshots, trees and blobs
Aug 02 01:41:12 macmini restic-backup.sh[3339702]: [0:03] 100.00%  11 / 11 snapshots
Aug 02 01:41:12 macmini restic-backup.sh[3339702]: no errors were found
(structural check only — no restore drill exists for any leg; sbom-05 open)
```

</details>

### SM44. No e2e check for /api/conversation/process — Assist rig-LLM agent path is green-but-unverified (monitoring gap, mandate 2)

**Host:** ha · **Component:** verification/checks.d/ha.yaml + HA Assist pipeline · **Auditor:** flow:ha-consumer · **Work item:** `fix-62`

ha.yaml has 11 checks (ha-http, ha-proxy-e2e, ha-api-auth, ha-hue-lights, ha-lights-available, ha-updates-pending, ha-availability-drift, ha-iphone-presence, ha-backup-offsite-fresh, ha-assist-rig-llm-reachable, ha-hacs-loaded) and none exercises /api/conversation/process. ha-assist-rig-llm-reachable only curls rig Ollama :11434/api/tags for the configured model (llama3.2:3b) — taxonomy #2 exposure: Ollama up + model listed would still pass while the HA-side conversation agent (conversation.rig_ollama_assist) is misconfigured or broken. My one-shot live probe (2026-08-02 ~13:36 EDT) succeeded but via the default built-in intent agent (response_type action_done), so the LLM agent path specifically remains unverified end to end. Notably ha-assist-rig-llm-reachable failed yesterday (rig ~23h powered off) and recovered today — during that outage nothing measured whether user Assist queries actually failed or degraded gracefully. NOT fixed per read-only mandate; needs a new check that POSTs /api/conversation/process (cheap, agent-targeted).

<details><summary>Evidence</summary>

```
cd /Users/brandontabaska/GitHub/Home && grep -E "id: " foss-setup/verification/checks.d/ha.yaml
  - id: ha-http ... ha-proxy-e2e ... ha-api-auth ... ha-hue-lights ... ha-lights-available ... ha-updates-pending ... ha-availability-drift ... ha-iphone-presence ... ha-backup-offsite-fresh ... ha-assist-rig-llm-reachable ... ha-hacs-loaded
# grep conversation foss-setup/verification/checks.d/ha.yaml → only comments; check body:
  - id: ha-assist-rig-llm-reachable
    cmd: >-
      curl -sm 15 http://192.168.10.12:11434/api/tags | python3 -c ...
# live one-shot probe (TOK from vault hosts.ha.api_token):
curl -s -m 30 -X POST http://192.168.10.50:8123/api/conversation/process -H "Authorization: Bearer $TOK" -H "Content-Type: application/json" -d '{"text":"what time is it","language":"en"}'
response_type: action_done
speech: {"plain": {"speech": "1:36 PM", "extra_data": null}}
```

</details>

### SM45. BedrockConnect console-player path has ZERO verification coverage (mandate-2 monitoring gap) — path itself verified working

**Host:** mini · **Component:** bedrock-connect (mini:19132) · **Auditor:** flow:game-servers · **Work item:** `fix-62`

The BedrockConnect serverlist on mini:19132 is the entry path for console Bedrock players, and grep of foss-setup/verification/ (checks.d + coverage) finds no reference to 19132 or bedrock-connect anywhere — only the public playit-edge Bedrock checks (game-playit-bedrock-udp, playit-bedrock-public) exist, which do not traverse this service. The container has only docker liveness (Up 2 weeks (healthy)). I verified the consumer path live this session: a RakNet unconnected ping from the Mac got the serverlist pong with MOTD 'Join To Open Server List'. Per standing mandate 2 (100% monitoring coverage) this needs a check probing the RakNet serverlist response, mirroring game-playit-bedrock-udp. NOT added per read-only mandate.

MERGED duplicate from svc:gaming (L18): BedrockConnect has container-liveness coverage only — zero functional checks despite serving the console-player join path — bedrock-connect appears in foss-setup/verification/coverage/mini.containers (line 2) so a dead container would be noticed, but no check in verification/checks.d/ probes its actual function: serving the Minecraft serverlist on UDP 19132 that console Bedrock players use to reach the server. This is exactly the green-but-broken liveness-masking class (mandate 1) — the container has been Up 2 weeks (healthy) but nothing would notice if the RakNet listener wedged. A one-shot live probe this session succeeded (pong 'Join To Open Server List', v1.26.30), so the service itself is currently working end-to-end. The gaming.yaml RakNet check pattern (game-playit-bedrock-udp) is directly reusable for a bedrockconnect-serverlist check. NOT fixed per read-only mandate; no open task covers this.

<details><summary>Evidence</summary>

```
cd /Users/brandontabaska/GitHub/Home && grep -rn "19132" foss-setup/verification/checks.d/ foss-setup/verification/coverage/ ; grep -rn -il "bedrockconnect" foss-setup/verification/
(no output — zero matches)
ssh mini 'docker ps --format "{{.Names}}\t{{.Status}}" | grep -iE "bedrock|connect"'
bedrock-connect	Up 2 weeks (healthy)
python3 RakNet unconnected ping -> 192.168.10.2:19132 (same packet as check game-playit-bedrock-udp)
PONG from 192.168.10.2 motd: MCPE;Join To Open Server List;1001;1.26.30;1;20;0;BedrockConnect Server List;Survival;1;19132;-1;
--- (merged lane svc:gaming) ---
grep -rniE "bedrockconnect|19132" foss-setup/verification/checks.d/ foss-setup/verification/coverage/
foss-setup/verification/coverage/mini.containers:2:bedrock-connect
(no hits in checks.d/ — zero functional checks)
ssh mini 'docker ps --format "{{.Names}}\t{{.Status}}" | grep bedrock'
bedrock-connect	Up 2 weeks (healthy)
python3 foss-setup/scripts/gaming/mc-bedrock-ping.py 192.168.10.2 19132
{'motd': 'Join To Open Server List', 'version': '1.26.30'}
BC_EXIT=0
```

</details>

### SM46. Django 5.2 shell auto-import banner ('18 objects imported automatically') masks the crit check's real payload in summaries — but it is NOT a write, and the check logic still works

**Host:** mini · **Component:** alert-healthchecks-none-down (checks.d/alerting.yaml) / healthchecks container · **Auditor:** repo:verification-suite · **Work item:** `fix-61`

Investigated the suspicious '18 objects imported automatically' output: it is the Django 5.2+ 'manage.py shell' auto-import banner (models imported into the shell namespace, read-only), not loaddata — no fixture write or state mutation occurs; the hypothesis of a check mutating Healthchecks state is disproven. The check's expect regex still matches correctly (re.M against stdout; the 13:01 audit sweep passed this check with the banner present). The real defect: the banner is stdout line 1, so last-summary.md's first-line failure table and today's triage input showed the banner instead of 'down_checks=verification-mini' during a genuine crit — directly defeating the check's documented purpose ('NAMES the down dead-mans ... so the daily re-page + last-summary say WHICH monitoring subsystem is dark'). alert-healthchecks-checks-defined and alert-kuma-none-down-style docker-exec checks share the exposure. Introduced by a healthchecks image upgrade to a Django 5.2 base. NOT fixed per read-only mandate (fix: add '-v 0' to the manage.py shell invocations).

MERGED duplicate from arch:topology (M71): Crit check alert-healthchecks-none-down is a permanent false positive: Django shell banner breaks the anchored expect regex (real state is down_checks=NONE) — Reproduced live 2026-08-02: 'docker exec healthchecks python3 /opt/healthchecks/manage.py shell -c ...' now prints '18 objects imported automatically (use -v 2 for details).' as the first stdout line (Django shell auto-import banner, presumably after a healthchecks image update), then a blank line, then 'down_checks=NONE'. The check's expect '^down_checks=NONE$' no longer matches, so a crit-severity check fails every daily run while the actual dead-man state is clean — and, worse, the check output is now identical whether or not a real dead-man is down, so it can no longer detect the condition it exists for. This is a regression of sec-03 done work (today's 10:23 run: alert-healthchecks-none-down crit FAIL '18 objects imported automatically'). NOT fixed per read-only mandate.

MERGED duplicate from svc:monitoring-stack (L16): Django 5.2 shell auto-import banner ('18 objects imported automatically') now prefixes every manage.py-shell check output — cosmetic, but it misled today's triage — Both alert-healthchecks-checks-defined and alert-healthchecks-none-down exec 'manage.py shell -c' in the healthchecks container (image healthchecks/healthchecks:v3.10, Django 5.2.1), which now prints '18 objects imported automatically (use -v 2 for details).' before the real output. No functional impact — checks_runner.py matches expect with re.search(..., re.M), and both checks pass/fail correctly on the down_checks=/checks= line — but the banner is the FIRST line captured in results.json, and today's sweep preflight read the crit failure as possible check breakage when the real signal (down_checks=verification-mini) was on line 3. Silencing it (e.g. manage.py shell -v 0 or piping the script via stdin) would keep triage output clean. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
# stored output of the failing crit (results.json 10:23):
==== alert-healthchecks-none-down status=fail exit=0 dur=1.17
18 objects imported automatically (use -v 2 for details).

down_checks=verification-mini
# last-summary.md rendered only the first line:
alert-healthchecks-none-down | crit | sec-03 | "18 objects imported automatically"
# check cmd (alerting.yaml): docker exec healthchecks python3 /opt/healthchecks/manage.py shell -c "...print('down_checks='+...)"
# proof the regex survives the banner: 13:01 audit sweep-run.json → alert-healthchecks-none-down PASS (dead-man back up after 10:25 ping)
# runner matches expect on stdout with re.M (checks_runner.py line 102): ok = re.search(check["expect"], stdout, re.M)
--- (merged lane arch:topology) ---
ssh mini 'docker exec healthchecks python3 /opt/healthchecks/manage.py shell -c "from hc.api.models import Check; d=[c.name for c in Check.objects.all() if c.get_status()==\"down\"]; print(\"down_checks=\"+(\",\".join(sorted(d)) if d else \"NONE\"))"'
18 objects imported automatically (use -v 2 for details).

down_checks=NONE
grep -A6 "id: alert-healthchecks-none-down" foss-setup/verification/checks.d/alerting.yaml
    expect: '^down_checks=NONE$'
    severity: crit
    task_id: sec-03
--- (merged lane svc:monitoring-stack) ---
ssh mini 'docker exec healthchecks python3 /opt/healthchecks/manage.py shell -c "from hc.api.models import Check; d=[c.name for c in Check.objects.all() if c.get_status()==...down...]; print(...)"'
18 objects imported automatically (use -v 2 for details).

down_checks=NONE
ssh mini 'docker exec healthchecks python3 -c "import django; print(django.get_version())"'
5.2.1
foss-setup/verification/bin/checks_runner.py:102: ok = re.search(check["expect"], stdout, re.M) is not None  (banner cannot break matching)
```

</details>

### SM47. The reopen bridge is write-only in practice: docs claim 'the AI session-start protocol consumes this file' but nothing at session start references it — 21 regressed done-tasks sit unprocessed

**Host:** repo · **Component:** reopen-suggestions.json bridge (verify-05) / tracker docs · **Auditor:** repo:verification-suite · **Work item:** `fix-61`

verification/README.md ('The AI session-start protocol consumes this file: at the start of a session it reads the list and proposes reopening those tasks') and wiki tracker.md ('session-start protocol is to process that file first') both assert automatic consumption. Verified false in the repo: CLAUDE.md — the only content actually auto-loaded at session start — never mentions reopen-suggestions.json; the sole consumer is the manual /fleet-sweep command (.claude/commands/fleet-sweep.md line 47). Measured consequence: today's file names 21 task_ids marked done (ai-03, fix-23/24/25/27/28/35/37/38/39/40/42/43/45, glue-03, ha-19, nas-01, net-05, sec-03, seed-12, verify-06, wiki-05), several failing daily since at least 07-19 (triage history), with none reopened in progress.json — the tracker's checkmarks drifted exactly the way verify-05 was built to prevent, until this sweep manually consumed the file. Compounding: the spent-enabled-timers false positive (separate finding) injects fix-39 into the file every day, training the operator to ignore it. NOT fixed per read-only mandate (fix options: add the consumption step to CLAUDE.md, or correct the two docs to describe /fleet-sweep as the consumer).

<details><summary>Evidence</summary>

```
grep -rn 'reopen-suggestions' CLAUDE.md → no matches
grep -rn 'reopen-suggestions' foss-setup/ .claude/ →
foss-setup/verification/README.md:121: 'The AI session-start protocol consumes this file...'
foss-setup/wiki/docs/operations/tracker.md:48: 'session-start protocol is to process that file first'
.claude/commands/fleet-sweep.md:47: (manual sweep reads it)
# live file (mini /var/lib/verification/reopen-suggestions.json, generated 2026-08-02T10:23:08):
task_ids: 21 entries incl. fix-23 fix-24 fix-25 fix-27 fix-28 fix-35 fix-37 fix-38 fix-39 fix-40 fix-42 fix-43 fix-45 glue-03 ha-19 nas-01 net-05 sec-03 seed-12 verify-06 wiki-05 — all marked done in docs/progress.json
# note field written by checks_runner.py line 266: 'consumed by the AI session-start protocol; the runner never commits to git by design'
```

</details>

### SM48. wiki-drift reproduced: checks pages stale because ai-04 commit 554c560 added a check without same-commit wiki regen (wiki-05 regression)

**Host:** repo · **Component:** foss-setup/wiki/docs/reference/checks/ (generated) vs verification/checks.d/git-hygiene.yaml · **Auditor:** repo:tracker-wiki · **Work item:** `fix-68`

Reproduced today's failing wiki-drift check locally: ran all 5 generators (gen-todo.py, gen-roadmap-pages.py, gen-wiki-services.py, gen-checks-pages.py, gen-script-pages.py) on a clean tree; exactly 2 committed generated pages are stale — reference/checks/git-hygiene.md (missing the ai-tooling-env-example-parity check, 12 vs 13 checks) and reference/checks/index.md (total 301 vs 302). Source drift: commit 554c560 (ai-04, 2026-07-29) added the 13th check to checks.d/git-hygiene.yaml but the checks pages were last regenerated at 69a5d86 (ai-03). This is the known 'deploys skip same-commit wiki regen' process gap recurring, and a regression of wiki-05 (wiki-in-the-loop). The published wiki undercounts and omits a live tripwire's documentation. Working tree restored with git checkout -- (local scratch revert only); NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
cd /Users/brandontabaska/GitHub/Home && for s in gen-todo.py gen-roadmap-pages.py gen-wiki-services.py gen-checks-pages.py gen-script-pages.py; do python3 foss-setup/scripts/docs/$s; done
gen-checks-pages: generated 302 checks across 35 domains
git status --porcelain
 M foss-setup/wiki/docs/reference/checks/git-hygiene.md
 M foss-setup/wiki/docs/reference/checks/index.md
git diff (trimmed):
-...git-hygiene.yaml` — 12 check(s)   +...13 check(s)
+## `ai-tooling-env-example-parity`  (guards task ai-04, expects ENV-EXAMPLE-PARITY-OK)
-_Total: 301 checks._  +_Total: 302 checks._
git log --oneline -2 -- foss-setup/verification/checks.d/git-hygiene.yaml
554c560 ai-04: vault-map local-ai-tooling docker/.env + .env.example key parity
69a5d86 ai-03: clean+pushed-to-both tripwire for the rig local-ai-tooling repo
git log --oneline -1 -- foss-setup/wiki/docs/reference/checks/git-hygiene.md
69a5d86 ai-03: clean+pushed-to-both tripwire...
git checkout -- <both files>; git status --porcelain | wc -l -> 0
```

</details>

### SM49. Service catalog (axis 6) lags the fleet: 6 live services missing, retired readarr still listed as live with a dead URL

**Host:** repo · **Component:** foss-setup/configs/docker-stack/service-catalog.yaml · **Auditor:** repo:tracker-wiki · **Work item:** `fix-68`

The 71-row catalog is missing live, user-facing services that both the coverage manifest and Homepage already know about: bookshelf (nas — readarr's replacement), shelfmark (nas, has a Homepage tile), whisparr (nas, has a tile), syncthing (live on mini+nas+seedbox mesh, has a tile), bgutil-pot (mini), bug-triage-evidence (mini). Inverted: retired readarr still has a live-looking row ('Book automation', url https://readarr.tabaska.us -> curl 000), and the libreseerr row's notes still say 'feeds Readarr'. Concrete consequence: gen-wiki-services.py takes URL+category from this catalog (it emitted only '51 stacks'), so missing rows mean missing/mis-categorized wiki service pages — the exact failure mode previously hit with audiobookshelf. Homepage tiles and coverage manifests are current, proving the catalog is the single lagging artifact. media-10 covers seedbox readarr labels only, not this catalog row. NOT fixed per read-only mandate.

MERGED duplicate from flow:edge-dns (M54): service-catalog.yaml drifted from live edge: retired readarr still listed as live (dead URL), while live vhosts bookshelf/shelfmark/whisparr/syncthing have no catalog entry — Cross-diff of the 62 live Caddy vhosts vs service-catalog.yaml on 2026-08-02: the catalog still carries readarr (lines 100-104, 'Book automation', url https://readarr.tabaska.us) with no decommission note, but readarr is retired (replaced by Bookshelf) and its vhost is gone — curl returns 000/TLS-fail. Meanwhile bookshelf.tabaska.us (NAS:8790), shelfmark.tabaska.us (NAS:8084), whisparr.tabaska.us (NAS:6969), and syncthing/syncthing-rig vhosts are live through Caddy but absent from the catalog entirely (grep finds only 'audiobookshelf'). gen-wiki-services takes URL+category from service-catalog.yaml, so missing entries yield wrong-URL/Uncategorized wiki pages and the stale readarr entry yields a dead wiki link — consistent with the wiki-drift check failing today (wiki-05 regression context). Violates mandate 3 (docs mirror the live stack) and the coverage tripwire habit. meme-review's entry is properly annotated DECOMMISSIONED and is fine. Not covered by media-10 (seedbox labels only) or sec-11 (key rotation only). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
python3 parse service-catalog.yaml -> count: 71
coverage-not-in-catalog(exact) nas: ['bookshelf','shelfmark','whisparr','syncthing',...]
coverage-not-in-catalog(exact) mini: ['bgutil-pot','bug-triage-evidence','syncthing',...]
grep -E '^  - name: (bookshelf|syncthing|whisparr|shelfmark)' service-catalog.yaml -> (no matches)
grep live lists: live-nas.txt:bookshelf  live-nas.txt:shelfmark(coverage:25)  live-nas.txt:whisparr(coverage:31)
catalog row: readarr | host: nas | url: https://readarr.tabaska.us | notes: Book automation.
curl -s -o /dev/null -w '%{http_code}' -m 8 https://readarr.tabaska.us -> 000
catalog row: libreseerr | notes: Book request portal (feeds Readarr). Container port 5000.
Homepage /api/services tiles include: Shelfmark, Whisparr, Syncthing (62 tiles; no Bookshelf tile either)
python3 foss-setup/scripts/docs/gen-wiki-services.py -> [gen-wiki-services] 51 stacks -> wiki/docs/services (PyYAML, catalog)
--- (merged lane flow:edge-dns) ---
sed -n '100,104p' foss-setup/configs/docker-stack/service-catalog.yaml
  - name: readarr
    category: Media Automation
    host: nas
    port: 8787
    url: https://readarr.tabaska.us
curl -s -o /dev/null -w "%{http_code} ssl_verify_result=%{ssl_verify_result}" -m 10 https://readarr.tabaska.us/
000 ssl_verify_result=1
grep -niE "bookshelf|shelfmark|whisparr|syncthing" foss-setup/configs/docker-stack/service-catalog.yaml
231:  - name: audiobookshelf
# live Caddy vhosts (mini /opt/stacks/caddy/caddy/Caddyfile): bookshelf->NAS:8790, shelfmark->NAS:8084, whisparr->NAS:6969, syncthing->NAS:8384, syncthing-rig->RIG:8384 — all curl 200/302 through proxy
```

</details>

### SM50. 22 checks carry task_id verify-06 which does not exist in tasks.json; reopen ledger also mis-includes open task ha-19 as done

**Host:** repo · **Component:** foss-setup/verification/checks.d/ task_id namespace + reopen-suggestions.json · **Auditor:** repo:tracker-wiki · **Work item:** `fix-61`

checks.d/docker-fleet.yaml (9 checks) and media.yaml (13 checks) reference task_id: verify-06, but tasks.json only defines verify-01..verify-05 — verify-06 appears nowhere in tasks.json or progress.json. Four of today's 29 failing checks (soularr-not-crashlooping, systemd-failed-mini, sonarr-queue-stuck, radarr-queue-stuck) therefore point at a task that cannot be reopened or routed through /resolve-finding. tracker-integrity.py passes because it only validates progress.json ids against tasks.json, not checks.d task_ids — a validation gap. Separately, reopen-suggestions.json includes ha-19 in its 'done tasks to reopen' list, but ha-19 is an OPEN task (absent from done/retired/deferred), so its failing check sys-docker-subnet-squat is already covered by open work — the reopen generator does not filter by done-status. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
python3 -c "..." # verify-* ids in tasks.json
verify-* task ids in tasks.json: ['verify-01','verify-02','verify-03','verify-04','verify-05']
grep -c 'task_id: verify-06' foss-setup/verification/checks.d/*.yaml
docker-fleet.yaml:9  media.yaml:13   (total 22)
grep -rn verify-06 foss-setup/docs/tasks.json foss-setup/docs/progress.json -> (no matches)
python3 cross-ref: ha-19: <NOT IN done>; progress.json retired(15)/deferred(18) do not contain ha-19
tasks.json: {'id':'ha-19','title':'IoT VLAN migration: move every WiFi IoT device onto VLAN 20 + firewall groups'}
reopen-suggestions.json task_ids includes both 'verify-06' and 'ha-19'
python3 foss-setup/scripts/verification/tracker-integrity.py
tracker coherent: 330 tasks = 251 done + 46 open + 18 deferred + 15 retired; all status ids resolve
```

</details>

### SM51. stacks-orphan-dirs check and decommission policy contradict on meme-review: check allowlists frigate+recyclarr but not the deliberately-retained meme-review dir

**Host:** mini · **Component:** /opt/stacks/meme-review + verification/checks.d/host-hygiene.yaml (stacks-orphan-dirs) · **Auditor:** repo:junk-deadpaths · **Work item:** `fix-69`

Check stacks-orphan-dirs (foss-setup/verification/checks.d/host-hygiene.yaml, task_id fix-43) hardcodes allowlist ' backups wiki frigate recyclarr ' and has flagged orphans=meme-review in today's 10:23 run. The live dir /opt/stacks/meme-review (last mtime 2026-07-27/28) holds compose.yaml, Dockerfile, .env, data/ — deliberately retained at the 2026-07-28 decommission, and the stack config is also still tracked in the repo mirror foss-setup/configs/docker-stack/stacks/meme-review/. Either the check needs meme-review in its allowlist (as was done for frigate, also a never-ran staged dir) or the data needs archiving off /opt/stacks; until then this warn is standing noise that erodes the check's signal. Regression context: fix-43 is marked done; this is a check-accuracy regression, NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ grep -A12 'id: stacks-orphan-dirs' foss-setup/verification/checks.d/host-hygiene.yaml
      allow=" backups wiki frigate recyclarr "; bad="";
      ...
      echo "orphans=${bad:-NONE} junk=${junk:-NONE}"
    expect: '^orphans=NONE junk=NONE$'
    severity: warn
    task_id: fix-43
$ ssh mini 'ls -la /opt/stacks/meme-review | head -8; ls -1 /opt/stacks'
drwxr-xr-x  5 btabaska btabaska  4096 Jul 27 17:17 .
-rw-r--r--  1 btabaska btabaska  1038 Jul 27 17:17 compose.yaml
drwxr-xr-x  5 btabaska btabaska  4096 Jul 27 17:14 data
-rw-r--r--  1 btabaska btabaska   600 Jul 27 17:16 Dockerfile
-rw-------  1 btabaska btabaska   383 Jul 27 17:17 .env
(live /opt/stacks contains meme-review; today's daily run: stacks-orphan-dirs orphans=meme-review)
$ ls -1 foss-setup/configs/docker-stack/stacks/ | grep meme
meme-review
```

</details>

### SM52. NAS 'docker system df' hung past a 2-minute timeout — docker disk-usage probe inconclusive, consistent with today's two other NAS TIMEOUT checks

**Host:** nas · **Component:** docker system df · **Auditor:** repo:junk-deadpaths · **Work item:** `fix-55` · *skeptic-confirmed*

The read-only cruft probe 'sudo /usr/local/bin/docker system df' on the NAS (password via vault sudo.nas_password) produced no output and was killed by the 2-minute shell timeout at ~13:50 EDT. docker system df walks image/volume layers and is known slow on DSM, but a >120s hang correlates with today's 10:23 run where nas-immich-backup-freshness (fix-35) and bitmagnet-torznab-via-prowlarr (seed-12) both hit TIMEOUT after 60s — three independent slow-I/O signals on the NAS today. Filed as evidence per sweep rules rather than retried; NAS docker cruft numbers therefore not collected.

*Verify note:* CONFIRMED and worse than filed. Fresh re-run at ~13:58 EDT: 'sudo /usr/local/bin/docker system df' on NAS gave zero output for 240s before alarm-kill (RC=142) — double the original 120s hang. Independent probe: NAS load 16.44 with IO component 14.27 (CPU 2.16) on a 4-core DS920+ = live I/O saturation ~3.5h after the 10:23 run; kswapd0 also shows heavy accumulated time (memory pressure). Corroboration verified in mini /var/lib/verification/results.json (2026-08-02T10:23:08-04:00): nas-immich-backup-freshness and bitmagnet-torznab-via-prowlarr both fail | TIMEOUT after 60s. Not on the known-normal list. Severity bumped low→medium: mechanism is a sustained NAS-wide I/O saturation degrading multiple monitoring consumers (incl. a backup-freshness check), not merely one inconclusive cruft probe. Suspects worth a follow-up look (not proven causal): rclone seedbox mount VFS cache on /volume1 and md2 I/O counters.

<details><summary>Evidence</summary>

```
$ PW=$(python3 -c "...['sudo']['nas_password']") ; printf '%s\n' "$PW" | ssh -o ConnectTimeout=10 nas 'sudo -S /usr/local/bin/docker system df 2>/dev/null | tail -5'
(no output; killed: Command timed out after 2m 0s)
Corroboration from 10:23 daily run:
nas-immich-backup-freshness | warn | fix-35 | TIMEOUT after 60s
bitmagnet-torznab-via-prowlarr | warn | seed-12 | TIMEOUT after 60s
```

</details>

### SM53. Rig 23h outage root cause: physical power-key press — logind still honors HandlePowerKey=poweroff on a 24/7-mandate host

**Host:** rig · **Component:** systemd-logind / power policy · **Auditor:** arch:topology · **Work item:** `fix-64`

The 07-31 11:07 -> 08-01 10:25 rig outage was not software: journal boot -1 shows 'Power key pressed short' at 11:07:09 followed by an orderly poweroff ('The system will power off now!'). Suspend is masked (game-08) but the power key path is not neutralized, so one accidental button press takes down the AI stack, game servers, Suwayomi->Komga feed, journaling coach and syncthing node for as long as nobody notices. Rig came back at 08-01 10:25 (who -b), 18 minutes BEFORE the daily tier's WoL attempt at 10:43, i.e. almost certainly a human power-on. Obvious hardening (logind.conf HandlePowerKey=ignore, mirrored to foss-setup/configs/host/rig/) NOT applied per read-only mandate. No open task covers power-key policy.

<details><summary>Evidence</summary>

```
ssh rig 'journalctl -b -1 --no-pager | grep -iE "power key|will power off" | tail -3'
Jul 31 11:07:09 cachyos systemd-logind[822]: Power key pressed short.
Jul 31 11:07:11 cachyos systemd-logind[822]: The system will power off now!
ssh rig 'who -b; date'
         system boot  2026-08-01 10:25
Sun Aug  2 01:42:42 PM EDT 2026
ssh rig 'journalctl -b -1 --no-pager -n 12'  # clean docker/container teardown at 11:07:15-16, no panic, no BTRFS errors
```

</details>

### SM54. Rig auto-recovery (WoL) only exists in the daily tier — detection is 10-minute but recovery latency is up to 24h

**Host:** fleet · **Component:** verification tiers / WoL self-heal · **Auditor:** arch:topology · **Work item:** `fix-63`

During the rig outage the fast tier detected and paged within 12 minutes (11:19 07-31), then re-ran every ~10 min showing the same 13 failures for ~23h — but the 'rig should be 24/7, this is an incident; attempting WoL recovery' logic only runs inside the daily verification.service LLM-triage phase. The previous daily had completed 52 minutes before the poweroff, so no automated recovery attempt happened for the entire outage; the 08-01 10:43 WoL fired after the rig was already back (10:25, human power-on). Design gap: WoL self-heal should live in the fast tier (or a dedicated rig-down handler), and a host-down condition persisting >1h deserves a re-page/escalation rather than first-page-then-dedup-silence. NOT changed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'sudo journalctl -u verification-fast.service --since "2026-07-31 11:07" --until "2026-08-01 10:20" --no-pager | grep -iE "FAIL|NEW|ntfy" | head'
Jul 31 11:19:07 run-checks.sh[3816796]: ntfy: sent (Verification [fast tier]: 13 NEW failure(s))
Jul 31 11:19:07 run-checks.sh[3816796]: 29/42 passed, 13 failed (2 crit), 3 skipped
Jul 31 11:28:21 run-checks.sh[3832898]: 29/42 passed, 13 failed (2 crit), 3 skipped   # repeats ~every 10 min, no further page
ssh mini 'sudo journalctl -u verification.service --since "2026-08-01 10:00" --until "2026-08-01 11:00" --no-pager | grep -i wol'
Aug 01 10:43:26 verify-cycle.sh[1897958]: LLM endpoint http://cachyos.tailb31641.ts.net:9292/v1 down — rig should be 24/7, this is an incident; attempting WoL recovery
ssh rig 'who -b'  ->  system boot 2026-08-01 10:25   (before the 10:43 WoL attempt)
```

</details>

### SM55. Stash self-heal is a no-op loop paging every 15 minutes: 'compose up' cannot fix an Up-but-dead container, 35+ identical pages in 12h

**Host:** nas · **Component:** stash self-heal / homelab-alerts topic · **Auditor:** arch:topology · **Work item:** `fix-62` · *skeptic-confirmed*

The stash container reports 'Up 3 weeks' while the service is dead at the HTTP level (stash-serving check empty output — regression of nas-01, in today's signal). A self-heal job runs 'compose up' every 15 minutes; since the container is already Up, compose does nothing, the health probe fails again, and 'NAS services down: Still down after compose up: stash' is paged to homelab-alerts every 15 minutes — every cached ntfy message slot from 01:45 to 10:15+ on 08-02. This is failure-pattern #7 (retry storm nobody reads): the channel that carries real host-down pages is being flooded. The remediation needs restart-not-up semantics plus page dedup/backoff; NOT fixed per read-only mandate. The stash outage itself is the nas-01 regression already on the reopen list; this finding is the self-heal/alert design flaw. ORCHESTRATOR FOLLOW-UP (gap:stash-import-outcome): the page storm is bounded — ntfy cache shows the identical page every ~15min 01:45→10:15 EDT, but a live poll of homelab-alerts at ~16:50 EDT found only 1 message in the prior 6h, and no stash-referencing .task exists in the NAS root scheduler — the self-heal job lives elsewhere (likely mini or a non-root DSM task) and either has a schedule window or stopped; the resolve session must locate it. Reconciliation with the svc:nas-apps finding: Stash the APP is healthy (auth added ~07-22; ApiKey'd GraphQL answers in ms) — the self-heal and the stash-serving check are both probing unauthenticated and reacting to their own 401s.

<details><summary>Evidence</summary>

```
ssh mini sudo python3 (sqlite ro) /opt/stacks/ntfy/cache/cache.db: select time,topic,title,msg from messages ...
2026-08-02T01:45:04 homelab-alerts | NAS services down | Still down after compose up: stash
2026-08-02T02:00:07 homelab-alerts | NAS services down | Still down after compose up: stash
... (identical every ~15 min through) ...
2026-08-02T10:15:03 homelab-alerts | NAS services down | Still down after compose up: stash
printf '%s\n' "$PW" | ssh nas 'sudo -S /usr/local/bin/docker ps -a --format "{{.Names}}\t{{.Status}}" | grep -i stash'
stash	Up 3 weeks
```

</details>

### SM56. Orphaned 'nc -lvnp 9999' listening on 0.0.0.0 for 17 days on mini

**Host:** mini · **Component:** stray process nc pid 2825993 · **Auditor:** arch:topology · **Work item:** `fix-51`

A bare netcat listener (nc -lvnp 9999, pid 2825993, user btabaska, cwd /home/btabaska) has been bound to 0.0.0.0:9999 for 17d 3h 48m — start time works out to ~2026-07-16, the day of the quality-gate audit, so it is almost certainly a leftover debug listener from that session. Plain nc without -e is not a shell, but it is an undocumented open port on all interfaces, it will accept exactly one connection from anything on the LAN/tailnet, and it demonstrates a gap: no check flags unexpected listening sockets vs an expected-ports manifest. Process NOT killed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'sudo ss -tlnp | grep ":9999 "'
LISTEN 1 1 0.0.0.0:9999 0.0.0.0:* users:(("nc",pid=2825993,fd=3))
ssh mini 'ps -o pid,ppid,etime,user,args -p 2825993; ls -l /proc/2825993/cwd'
    PID    PPID     ELAPSED USER     COMMAND
2825993 2825992 17-03:48:06 btabaska nc -lvnp 9999
lrwxrwxrwx 1 btabaska btabaska 0 Aug  2 13:46 /proc/2825993/cwd -> /home/btabaska
```

</details>

### SM57. Secrets vault remains a single copy on the operator Mac — fleet recovery depends on one laptop SSD `known-issue`

**Host:** repo · **Component:** foss-setup/.handoff-secrets.yaml · **Auditor:** arch:topology

Confirmed live: the vault is one 17KB chmod-600 file on the Mac (last modified Jul 29), gitignored by design, with no replica. Every credential needed to rebuild or even administer the fleet (NAS sudo, rig sudo, HA token, all API keys, B2 restic passwords) lives only there; losing the laptop loses the ability to execute glue-06/sbom-05 rebuild drills at all. Fully covered by open task handoff-12 (vault-delete + key-rotation custody work).

<details><summary>Evidence</summary>

```
cd /Users/brandontabaska/GitHub/Home && ls -l foss-setup/.handoff-secrets.yaml
.rw-------@ 17k brandontabaska 29 Jul 09:40 foss-setup/.handoff-secrets.yaml
(referenced by path only; git ls-files does not show it — gitignored per CLAUDE.md)
```

</details>

### SM58. Flat-LAN exposure: ~30 mini + ~20 rig + ~35 NAS service ports bound 0.0.0.0, including unauthenticated GPU/AI endpoints that bypass the Caddy auth gate

**Host:** fleet · **Component:** listening-socket posture (mini/rig/NAS) · **Auditor:** arch:topology · **Work item:** `fix-51` · *skeptic-confirmed*

Live socket sweep 2026-08-02: nearly every containerized service publishes on 0.0.0.0 via docker-proxy, so Caddy basic_auth/forward-auth is bypassable by any LAN device (Marinara-class hole, previously seen). Most exposed on rig: ollama *:11434, llama-swap 0.0.0.0:9292, ComfyUI 0.0.0.0:8188-8189 (arbitrary workflow execution = file read/write in container), Sunshine 47984-48010; on mini additionally rpcbind :111 and unpackerr *:5656 run at host level; NAS adds NFS (2049/892/662), SMB, and every arr/media UI. Until IoT-VLAN segmentation (ha-19, open; net-05 gateway check also failing today) any compromised LAN/IoT device reaches these directly. Design finding: define an expected-listeners manifest per host and either bind LAN-only services to specific IPs/loopback or gate them; not covered by an open task for the trusted VLAN itself.

*Verify note:* CONFIRMED via fresh probes. (1) Re-ran ss on rig: *:11434 (ollama), 0.0.0.0:9292 (llama-swap), 0.0.0.0:8188 + 0.0.0.0:8189 (ComfyUI), 0.0.0.0:47984/47989/47990/48010 (Sunshine), 0.0.0.0:8212, 0.0.0.0:4000 (litellm), 0.0.0.0:25565 all present — matches evidence. (2) Re-ran sudo ss on mini: 0.0.0.0:111 (rpcbind) and *:5656 (unpackerr) confirmed at host level, plus ~30 docker-proxy 0.0.0.0 binds (3010/4533/5055/5678/8000-9000). (3) Re-ran sudo netstat on NAS: 0.0.0.0:2049+892+662 (NFS), 0.0.0.0:445+139 (SMB), 0.0.0.0:2283 (immich), 8989/7878/8686/6767/13378/25600 all 0.0.0.0 — matches. (4) INDEPENDENT PROBE from this Mac (an arbitrary LAN device, NOT via Caddy): ollama http://192.168.10.12:11434/api/tags returned 3 models unauthenticated; ComfyUI http://192.168.10.12:8188/system_stats returned full host info (RAM 64GB, comfyui 0.28.0) with NO auth; llama-swap :9292 answered 302. This directly demonstrates the Caddy basic_auth/forward-auth gate is bypassable on the flat LAN — the load-bearing claim holds. Tracker: ha-19 (IoT VLAN 20 migration) is OPEN, confirming no segmentation yet; no expected-listeners-manifest task exists (0 hits in worklist). Two minor imprecisions that do NOT change the verdict: (a) the finding says 'net-05 gateway check also failing today' but net-05 is marked done in progress.json — irrelevant to the socket exposure; (b) ha-19 covers the IoT VLAN, not the trusted-VLAN listener manifest the finding recommends, which the detail already acknowledges. Severity medium is right: it's a real defense-in-depth/design gap (any compromised LAN/IoT device reaches unauthenticated GPU/AI endpoints = the previously-seen Marinara-class hole), but these are LAN-bound not WAN-exposed, so not high. No severity change.

<details><summary>Evidence</summary>

```
ssh rig 'ss -tlnp | awk "{print \$4}" | sort -u' (trimmed)
0.0.0.0:4000 0.0.0.0:8188 0.0.0.0:8189 0.0.0.0:8212 0.0.0.0:9292 *:11434 0.0.0.0:47984 0.0.0.0:47989 0.0.0.0:48010 0.0.0.0:25565
ssh mini 'sudo ss -tlnp | awk ...' (trimmed)
0.0.0.0:111 0.0.0.0:2222 0.0.0.0:3030 0.0.0.0:4533 0.0.0.0:5055 0.0.0.0:5678 0.0.0.0:8000..9000 *:5656(unpackerr)
printf '%s\n' "$PW" | ssh nas 'sudo -S sh -c "netstat -tlnp | grep LISTEN ..."' (trimmed)
0.0.0.0:2049(nfs) 0.0.0.0:445(smbd) 0.0.0.0:2283(immich) 0.0.0.0:8989 0.0.0.0:7878 0.0.0.0:8686 0.0.0.0:6767 0.0.0.0:13378 0.0.0.0:25600 (all docker-proxy)
```

</details>


---

## LOW (46)

### SL1. DSM abnormal-login geo-lookup fails on every tailnet-source login, flooding /var/log/messages (7,156 lines in current file)

**Host:** nas · **Component:** synologand / /var/log/messages · **Auditor:** host:nas · **Work item:** `fix-69`

The current /var/log/messages contains 7,156 'synologand abnormal_login.cpp:112 Failed to get the info whose ip address is [100.x.x.x]' lines (tailnet CGNAT IPs 100.97.245.80 and 100.81.199.6 — the verification runner on mini and operator sessions), many per minute during SSH activity, repeatedly suppressed by syslog-ng. Failure pattern #7 retry-storm: in the last 400 log lines the ONLY non-flood content was 2 session-timeout lines, so any real DSM signal is drowned. Benign per-event (successful logins whose source IP has no geo info), but it makes /var/log/messages effectively unreadable and today's sweep amplifies it further. Not covered by an open task.

<details><summary>Evidence</summary>

```
printf '%s\n' "$PW" | ssh nas 'sudo -S sh -c "grep -c abnormal_login /var/log/messages; tail -400 /var/log/messages | grep -vE \"synologand|abnormal_login|suppressed by syslog-ng|coredump|ffmpeg\" | tail -5" 2>/dev/null'
7156
2026-08-02T03:39:11-04:00 TabaskaNAS synocgid[13489]: session/timeout.cpp:74 btabaska has session timeout.
2026-08-02T03:39:11-04:00 TabaskaNAS synocgid[13489]: session/timeout.cpp:74 btabaska has session timeout.
# sample flood lines:
2026-08-02T12:55:13-04:00 TabaskaNAS synologand[11778]: abnormal_login.cpp:112 Failed to get the info whose ip address is [100.97.245.80]
2026-08-02T13:07:14-04:00 TabaskaNAS synologand[11778]: abnormal_login.cpp:112 Failed to get the info whose ip address is [100.81.199.6]
2026-08-02T12:59:42-04:00 TabaskaNAS synologand[6638]: SYSTEM: Last message 'abnormal_login.cpp:1' repeated 9 times, suppressed by syslog-ng on TabaskaNAS
```

</details>

### SL2. Zero-byte DSM scheduled-task file 6.task — a scheduler slot with no definition since Jul 7

**Host:** nas · **Component:** /usr/syno/etc/synoschedule.d/root/6.task · **Auditor:** host:nas · **Work item:** `fix-69`

Of the 15 root scheduled-task files, 6.task is 0 bytes (root:root, mtime Jul 7 21:36) — whatever task once occupied slot 6 has no name, schedule, or command and silently cannot run (failure pattern #6 class). All other tasks are intact and named (DSM Auto Update, beets YouTube import, 2x 'S3 Backup enc' at slots 11/12 — apparently a deliberate pair, Tailscale TUN reconfigure fix-21, recycle-bin purge, Shelfmark rshared persist fix, security advisor, Mount watchdog, Manual Copy, Docker health check, Immich DB dump). Worth confirming in DSM Task Scheduler UI whether slot 6 corresponds to a ghost entry and deleting/recreating it. NOT touched per read-only mandate.

<details><summary>Evidence</summary>

```
printf '%s\n' "$PW" | ssh nas 'sudo -S sh -c "ls -la /usr/syno/etc/synoschedule.d/root/ | grep 6.task; wc -c /usr/syno/etc/synoschedule.d/root/6.task; for f in /usr/syno/etc/synoschedule.d/root/*.task; do printf \"%s : \" \$f; grep -E \"^name\" \$f; done" 2>/dev/null'
-rw-r--r-- 1 root root 0 Jul  7 21:36 6.task
0 /usr/syno/etc/synoschedule.d/root/6.task
1.task : name=DSM Auto Update
10.task : name=beets YouTube import
11.task : name=S3 Backup enc
12.task : name=S3 Backup enc
13.task : name=Tailscale TUN reconfigure (fix-21)
14.task : name=Empty recycle bins (30d retention)
15.task : name=Shelfmark seedbox mount rshared (MAM path persist)
6.task : (no name line — file empty)
```

</details>

### SL3. Radarr repeatedly failing ffprobe/mediainfo on a Professor Layton PAL file + NRE in ExistingExtraFileService

**Host:** nas · **Component:** radarr (:7878) media analysis · **Auditor:** svc:arr-stack · **Work item:** `fix-54`

Error log shows 7x 'Failed to get runtime from the file, make sure ffprobe is available' and 2x 'Unable to parse media info from file: /movies/Professor.Layton.and.the.Eternal.Diva.2010.PAL...' (last 2026-08-01T21:24Z), plus 4x 'ExistingExtraFileService failed while processing [MovieScannedEvent]: Object reference not set' — an unparseable/likely-junk media file (taxonomy #8 flavor) that re-errors on every scan. Cosmetically noisy, and the NRE suggests the file also trips a Radarr bug. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
curl -sm 15 -H "X-Api-Key: $RADARR_KEY" http://192.168.10.4:7878/api/v3/log?level=error&pageSize=30
 7x last=2026-08-01T21:24:46 Failed to get runtime from the file, make sure ffprobe is available
 4x last=2026-08-01T21:25:08 ExistingExtraFileService failed while processing [MovieScannedEvent]: Object reference not set
 2x last=2026-08-01T21:24:46 Unable to parse media info from file: /movies/Professor.Layton.and.the.Eternal.Diva.2010.PAL.Mu
```

</details>

### SL4. cwa-library-covers nocover=1 identified: book id 99 'Wuthering Heights' (Emily Bronte), added 2026-07-21, has no cover

**Host:** nas · **Component:** calibre-web-automated library (/volume1/books/metadata.db) · **Auditor:** svc:nas-apps · **Work item:** `fix-67`

Re-ran the check's query read-only on the NAS: exactly one book has has_cover=0 — id 99, 'Wuthering Heights', author_sort 'Bronte, Emily Jane', timestamp 2026-07-21 20:48 UTC. This is the fix-38 regression flagged by today's cwa-library-covers warn (nocover=1); the book was ingested after fix-38 closed, so the cover-repair work needs a new item (or a cover upload for this one title). NOT fixed per read-only mandate.

MERGED duplicate from svc:reading (L19): cwa-library-covers regression reproduced: book 99 'Wuthering Heights' has no cover (fix-38 regression) — Today's 10:23 daily run fails cwa-library-covers (nocover=1, task fix-38, in the regression set). Reproduced live 2026-08-02 ~13:05 EDT with the same read-only sqlite query: book id 99 'Wuthering Heights', added 2026-07-21 20:48 UTC, has_cover=0. Every other cover/library check passes (author-split, dup-titles, ingest-automerge-guard). Consumer impact: coverless tile in CWA UI and on Kobo sync. Obvious fix is a one-book cover fetch — NOT fixed per read-only mandate; needs a new work item since fix-38 is marked done.

MERGED duplicate from flow:books (L23): cwa-library-covers nocover=1 confirmed at consumer end: 'Wuthering Heights' (book 99) has no cover asset on disk; Kobo still advertises CoverImageId so devices render a blank/placeholder tile — book itself readable — The 10:23 daily failure cwa-library-covers nocover=1 (fix-38 regression) is book id 99 'Wuthering Heights' (path 'Emily Jane Bronte/Wuthering Heights (99)', added 2026-07-21 — one day after libreseerr's author-gate correctly refused the same title 3x on 07-20, so it entered via the manual/Shelfmark path without artwork). On-disk listing confirms EPUB + KEPUB + metadata.opf but no cover file; has_cover=0. Consumer impact verified via the tokened Kobo API: the book is present in the device sync stream and its metadata answers with DownloadUrls=1 (readable/downloadable) but calibre-web sets CoverImageId unconditionally, so the device will request cover art that does not exist — cosmetic-only degradation (artless tile). Regression of done work fix-38; NOT fixed per read-only mandate (needs a cover embedded/fetched for book 99).

<details><summary>Evidence</summary>

```
ssh nas 'sqlite3 "file:/volume1/books/metadata.db?mode=ro" "select id, title, author_sort, timestamp from books where has_cover=0;"'
99|Wuthering Heights|Bronte, Emily Jane|2026-07-21 20:48:39.336763+00:00

results.json 2026-08-02T10:23: cwa-library-covers fail 'nocover=1'
--- (merged lane svc:reading) ---
printf '%s\n' "$PW" | ssh nas 'sudo -S sh -c '\''sqlite3 "file:/volume1/books/metadata.db?mode=ro" "select id,title,timestamp from books where has_cover=0;"'\'' 2>/dev/null'
99|Wuthering Heights|2026-07-21 20:48:39.336763+00:00
# 10:23 sweep: cwa-library-covers | fail | nocover=1 (task fix-38, expect ^nocover=0$)
--- (merged lane flow:books) ---
ssh nas 'sqlite3 "file:/volume1/books/metadata.db?mode=ro" "select id,title,path,timestamp from books where has_cover=0;"'
-> 99|Wuthering Heights|Emily Jane Bronte/Wuthering Heights (99)|2026-07-21 20:48:39
ssh nas 'ls /volume1/books/"Emily Jane Bronte"/"Wuthering Heights (99)"/'
-> Wuthering Heights - Emily Jane Bronte.epub / .kepub / metadata.opf   (no cover.jpg)
Kobo API (vault cwa.kobo_api_endpoint_admin): sync payload contains uuid 5d837b41-f0b1-471e-9e0f-4de05be9d48d (wuthering_in_shelf=True)
GET $BASE/v1/library/5d837b41-.../metadata -> http=200 CoverImageId=SET DownloadUrls=1 Title='Wuthering Heights'
10:23 run: cwa-library-covers fail nocover=1 (task fix-38)
```

</details>

### SL5. One Immich asset carries a bogus future capture date (fileCreatedAt 4501-01-01) and permanently tops date-descending views

**Host:** nas · **Component:** immich asset metadata · **Auditor:** svc:nas-apps · **Work item:** `fix-60`

POST /api/search/metadata {size:1, order:desc} returns as the 'newest' asset an IMAGE with fileCreatedAt=4501-01-01T08:00:00Z (uploaded 2026-07-24) — corrupt EXIF capture date. A read-only DB count confirms exactly 1 asset with fileCreatedAt more than a year in the future, so it is an isolated data-hygiene defect, but it sits on top of the timeline/date-ordered API results and skews any newest-asset freshness probe that sorts by capture date. NOT fixed per read-only mandate (fix = correct the date in Immich UI).

MERGED duplicate from flow:photos (L27): One asset (Pic 127.jpg) carries an impossible fileCreatedAt of 4501-01-01, hijacking date-descending sort order — A metadata search sorted date-descending returns Pic 127.jpg (uploaded 2026-07-24) first because its fileCreatedAt is 4501-01-01T08:00:00Z — broken EXIF from the 2026-07-24 bulk import. A takenAfter=2027-01-01 query confirms exactly 1 future-dated asset, so it also sits permanently at the top of the app timeline. One-asset date fix in the Immich UI would clear it; NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
curl -s -H "x-api-key: $IK" -X POST http://192.168.10.4:2283/api/search/metadata -d '{"size":1,"order":"desc"}'
newest fileCreatedAt 4501-01-01T08:00:00.000Z createdAt 2026-07-24T15:25:31.898Z type IMAGE

sudo docker exec immich_postgres psql -U postgres -d immich -tAc "SELECT count(*) FROM asset WHERE \"fileCreatedAt\" > now() + make_interval(years => 1)"
1
--- (merged lane flow:photos) ---
curl -s -m 30 https://immich.tabaska.us/api/search/metadata -H "x-api-key: $KEY" -d '{"size":1,"order":"desc"}'
newest_asset createdAt= 2026-07-24T15:25:31.898Z fileCreatedAt= 4501-01-01T08:00:00.000Z type= IMAGE path= Pic 127.jpg
curl -s -m 30 .../api/search/metadata -d '{"takenAfter":"2027-01-01T00:00:00Z","size":5}'
future_dated_total= 1
Pic 127.jpg 4501-01-01T08:00:00.000Z uploaded= 2026-07-24
```

</details>

### SL6. Stale failed unit snap-lxd-38800.mount left over from lxd snap refresh keeps failed-units checks red

**Host:** mini · **Component:** snap-lxd-38800.mount · **Auditor:** host:mini · **Work item:** `fix-69`

snap refreshed lxd from rev 38800 to 40338 on Aug 01 13:12:47; the old revision's mount unit failed its unmount (already not mounted, status 32) and now sits LOAD=not-found ACTIVE=failed. Purely cosmetic, but it is one of the two failed units tripping systemd-failed-mini (verify-06) and contributing to sys-failed-units (glue-03) in today's 10:23 run — regression-set noise that masks future real failures. Fix is a one-line systemctl reset-failed — NOT run per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'systemctl --failed --no-pager'
● snap-lxd-38800.mount  not-found failed failed snap-lxd-38800.mount
● ntfy-notify@lidarr-artist-monitor-reconcile.service.service loaded failed failed

ssh mini 'systemctl status snap-lxd-38800.mount --no-pager | head -8; snap list lxd'
Loaded: not-found (Reason: Unit snap-lxd-38800.mount not found.)
Active: failed (Result: exit-code) since Sat 2026-08-01 13:12:47 EDT
Aug 01 13:12:47 macmini umount[2138510]: umount: /snap/lxd/38800: not mounted.
Aug 01 13:12:47 macmini systemd[1]: snap-lxd-38800.mount: Mount process exited, code=exited, status=32/n/a
Name  Version        Rev    Tracking
lxd   5.0.8-46bcfa0  40338  5.0/stable/…
```

</details>

### SL7. Reboot-required pending 24 days: kernel 5.15.0-186 + libc6 installed but host still running 5.15.0-185

**Host:** mini · **Component:** kernel / apt · **Auditor:** host:mini · **Work item:** `fix-69`

/var/run/reboot-required exists (linux-image-5.15.0-186-generic, linux-base, libc6) while uptime is 24 days on 5.15.0-185-generic — installed kernel and libc security updates are not active until a reboot. unattended-upgrades is enabled and working (last run 06:43 today), but ubuntu-advantage-tools is held back with a conffile prompt needing manual attention, and 95 non-security packages are upgradable. A reboot of the 38-container Docker host is disruptive — belongs in the 4-7AM EST window per mandate. NOT rebooted per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'ls /var/run/reboot-required*; cat /var/run/reboot-required.pkgs; uptime; uname -r'
/var/run/reboot-required
/var/run/reboot-required.pkgs
linux-image-5.15.0-186-generic
linux-base
libc6
 13:08:31 up 24 days,  5:13,  load average: 0.79, 0.78, 0.78
5.15.0-185-generic

ssh mini 'sudo tail -5 /var/log/unattended-upgrades/unattended-upgrades.log; sudo apt-get -s upgrade | grep upgraded'
2026-08-02 06:43:25 WARNING Package ubuntu-pro-client has conffile prompt and needs to be upgraded manually
2026-08-02 06:43:26 INFO No packages found that can be upgraded unattended and no pending auto-removals
95 upgraded, 0 newly installed, 0 to remove and 6 not upgraded.
```

</details>

### SL8. ansible-site-converged-mini changed=1 is solely the known-normal chezmoi mode-bit flap — check contradicts stated policy

**Host:** mini · **Component:** verification check ansible-site-converged-mini · **Auditor:** host:mini · **Work item:** `fix-65`

Reproduced live: ansible-playbook --check --diff on mini shows exactly one changed task, 'state : Apply dotfiles with chezmoi (glue-04)', and chezmoi diff contains only mode-bit hunks (644->664, 755->775 group-write from umask) with zero content changes. Sweep policy explicitly treats the chezmoi mode-bit flap as known-normal ('content hunks only count'), yet the fix-42 check fires warn on it and lands in the regression set every run. Needs the check (or the chezmoi task) made mode-bit-tolerant so real convergence drift isn't buried. NOT fixed per read-only mandate.

MERGED duplicate from flow:backups (L36): Today's ansible-site-converged-mini fail (changed=1) is a false positive: chezmoi mode-bit flap only, zero content drift — Reproduced the --check run live at 13:36 EDT: the single changed task is 'state : Apply dotfiles with chezmoi (glue-04)', and chezmoi diff on mini shows exclusively mode changes (0644->0664, 0755->0775) with no content hunks — the documented known-normal chezmoi mode-bit flap. The backup role it guards is separately proven converged (restic-role-matches-source-mini RESTIC-ROLE-OK, pass today). So this is not a real fix-42 regression; the check needs a mode-flap-tolerant reformulation or it will warn daily and mask real convergence drift. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'cd $HOME/.ansible-pull/foss-setup/configs/ansible && timeout 100 ansible-playbook -i inventory.ini --connection local --limit macmini --check --diff site.yml 2>&1 | grep -B3 -A10 "^changed:"'
TASK [state : Apply dotfiles with chezmoi (glue-04)] ***
changed: [macmini]
macmini : ok=40 changed=1 unreachable=0 failed=0 skipped=14

ssh mini 'chezmoi diff | head -12'
diff --git a/.config b/.config
old mode 40755
new mode 40775
diff --git a/.config/fish/config.fish b/.config/fish/config.fish
old mode 100644
new mode 100664
diff --git a/.zshrc b/.zshrc
old mode 100644
new mode 100664
(all hunks are mode-only; no content hunks)
--- (merged lane flow:backups) ---
ssh mini 'cd $HOME/.ansible-pull/foss-setup/configs/ansible && ansible-playbook -i inventory.ini --connection local --limit macmini --check site.yml 2>&1 | grep -B3 -E "^changed:"'
TASK [state : Apply dotfiles with chezmoi (glue-04)] ***
changed: [macmini]
ssh mini 'chezmoi diff | head -30'
diff --git a/.zshrc b/.zshrc
old mode 100644
new mode 100664
(all 7 hunks are mode-only; no content hunks)
results.json 10:23: ansible-site-converged-mini | fail | macmini : ok=40 changed=1 failed=0
results.json 10:23: restic-role-matches-source-mini | pass | RESTIC-ROLE-OK
```

</details>

### SL9. PalServer segfaulted twice in 4 days (07-29 19:27, 08-01 18:32); docker restart policy recovered it both times

**Host:** rig · **Component:** palworld container · **Auditor:** host:rig · **Work item:** `fix-64`

The preflight 'palworld RestartCount=1' is explained: PalServer-Linux-Shipping terminated with SIGSEGV at Sat 08-01 18:32:41 EDT (no coredump generated) and docker restarted the container (started 18:32:42 EDT, now Up 19 hours, healthy). An earlier identical SEGV occurred Wed 07-29 19:27:25. Any connected players get dropped at crash time; recovery is automatic and current state is healthy. Known Palworld-server flakiness rather than a host problem; frequency (~2 per 4 days of uptime) is worth a passive watch, not a work item yet.

<details><summary>Evidence</summary>

```
ssh rig 'coredumpctl list | grep -i pal'
Wed 2026-07-29 19:27:25 EDT 11343 1000 1000 SIGSEGV none /palworld/Pal/Binaries/Linux/PalServer-Linux-Shipping -
Sat 2026-08-01 18:32:41 EDT 9826 1000 1000 SIGSEGV none /palworld/Pal/Binaries/Linux/PalServer-Linux-Shipping -
ssh rig 'journalctl -p err --since -24h | tail -1'
Aug 01 18:32:41 systemd-coredump[179055]: Process 9826 (PalServer-Linux) of user 1000 terminated abnormally without generating a coredump.
ssh rig 'docker inspect palworld --format "status={{.State.Status}} rc={{.RestartCount}} started={{.State.StartedAt}}"'
status=running rc=1 started=2026-08-01T22:32:42.284044791Z
docker ps: palworld  Up 19 hours (healthy)
```

</details>

### SL10. Persistent timer catch-up ran the NIGHT(on) unit at 14:26 in the daytime after the outage and failed; self-corrected at the next real window

**Host:** rig · **Component:** immich-ml-window@on.service · **Auditor:** host:rig · **Work item:** `fix-64`

After the 08-01 10:25 power-on, the immich-ml-window-on timer's catch-up fired the night unit at 14:26 EDT (daytime): the ML container did not answer /ping within 60s (day-window VRAM policy) so the unit exited 1, after resuming the smartSearch/faceDetection/ocr queues (harmless — NAS iGPU fallback serves them). The real 01:00 run on 08-02 succeeded in 4s and the 07:00 off run was clean, and the container ran exactly 01:00-07:00 EDT, so glue-14 behavior is intact. Design nit: the on-unit should no-op when invoked outside the window (Persistent catch-up after any outage will always produce this spurious failed unit + error-journal entry). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh rig 'journalctl -u immich-ml-window@on.service --since "2026-08-01" | head -8'
Aug 01 14:26:48 immich-ml-window.sh[4343]: [immich-ml-window] NIGHT: WARNING immich_machine_learning not answering /ping after 60s
Aug 01 14:26:48 immich-ml-window.sh[4343]: [immich-ml-window] queue smartSearch resume -> 200
Aug 01 14:26:48 systemd[1]: immich-ml-window@on.service: Failed with result 'exit-code'.
Aug 02 01:00:04 immich-ml-window.sh[436806]: [immich-ml-window] NIGHT: immich_machine_learning answering /ping
Aug 02 01:00:04 systemd[1]: Finished Immich ML rig-GPU night window (on).
Aug 02 07:00:02 immich-ml-window.sh[688569]: [immich-ml-window] DAY: immich_machine_learning stopped — Immich now uses the NAS iGPU fallback
ssh rig 'docker inspect immich_machine_learning --format "{{.State.Status}} started={{.State.StartedAt}} finished={{.State.FinishedAt}}"'
exited started=2026-08-02T05:00:00Z finished=2026-08-02T11:00:02Z  (= 01:00-07:00 EDT)
```

</details>

### SL11. Proton Mail Bridge user unit failed; protonmail-bridge also SEGV'd during the 07-31 shutdown `known-issue`

**Host:** rig · **Component:** app-proton-bridge (user unit) · **Auditor:** host:rig

systemctl --user --failed shows app-proton\x2dbridge@aad1215d....service in failed state this boot, and during the 07-31 shutdown systemd-coredump caught protonmail-brid terminating with SIGSEGV. Desktop-app hygiene on the rig workstation side; if bridge-dependent mail flows exist they are not running. Covered by the rig desktop baseline work (glue-02, operator-gated).

<details><summary>Evidence</summary>

```
ssh rig 'systemctl --user --failed'
app-proton\x2dbridge@aad1215d4a384a3196bf0d41095ab843.service loaded failed failed Proton Mail Bridge
ssh rig 'journalctl -b -1 --since "2026-07-31 11:06"' (excerpt):
Jul 31 11:07:11 systemd-coredump[2090325]: Process 8358 (protonmail-brid) of user 1000 terminated abnormally with signal 11/SEGV, processing...
```

</details>

### SL12. UFW BLOCK flood: 8,220 kernel log lines this boot, including Syncthing local-discovery multicast and steady UDP from 192.168.10.177

**Host:** rig · **Component:** ufw / kernel log · **Auditor:** host:rig · **Work item:** `fix-64` · *skeptic-confirmed*

This 26h boot has 8,220 '[UFW BLOCK]' kernel lines: repeated IPv6 multicast to port 21027 (Syncthing local discovery — the mesh uses static addresses per foss-03 config so functional impact is low) and a steady stream of UDP from 192.168.10.177 to changing high ports on the rig. Pure log noise at ~5/min degrades journal signal (taxonomy #7-lite) and 192.168.10.177 is unidentified from this vantage. Worth an ufw logging tune or a deny-rule-without-log for known-benign broadcast, and identifying .177. NOT fixed per read-only mandate.

*Verify note:* CONFIRMED at low. Fresh re-probe: current rig boot (Aug 1 10:25 EDT, ~27h) now has 8,453 '[UFW BLOCK]' kernel lines and still accruing (~5.2/min; last block seconds old) — 4,180 are IPv6 multicast to DPT=21027 (Syncthing local discovery; harmless given foss-03 static-address mesh) and 2,835 from 192.168.10.177. Independent probe identified .177: ARP lladdr 8c:79:f5:8a:ab:3c (Samsung OUI 8C:79:F5) plus dominant DPT=15600 (Samsung SmartThings discovery port) = Samsung smart-TV/SmartThings device doing benign LAN discovery — noise, not a threat, so severity stays low. One evidence correction: the auditor's 'Jul 25 16:26:58' sample line is from a prior boot (boots rotated Jul 29 and Aug 1); the count itself is from the current boot and accurate. No PTR record for .177 in AdGuard (both .4 and .2 resolvers empty). Remediation as filed: ufw logging tune or deny-without-log for known-benign broadcast (21027 multicast + Samsung discovery).

<details><summary>Evidence</summary>

```
ssh rig 'journalctl -k -b 0 | grep -c "UFW BLOCK"'
8220
samples:
Jul 25 16:26:58 kernel: [UFW BLOCK] IN=enp10s0 SRC=fe80::66a8:e11c:d8b4:38bf DST=ff12::8384 PROTO=UDP SPT=49056 DPT=21027  (Syncthing local discovery)
Jul 31 11:05:08 kernel: [UFW BLOCK] IN=enp10s0 SRC=192.168.10.177 DST=192.168.10.12 PROTO=UDP SPT=54239 DPT=43698
```

</details>

### SL13. HA appliance lost all network for ~3 minutes overnight (00:40-00:43 EDT 2026-08-02), self-recovered

**Host:** ha · **Component:** HA OS network / matter+hue+elgato integrations · **Auditor:** host:ha · **Work item:** `fix-66`

The core log (GET /api/hassio/core/logs, fetched 2026-08-02 ~13:05 EDT) shows a clustered outage window: Elgato fetch errors for 192.168.20.101/.102 at 00:40:40-00:41:12, zeroconf OSError [Errno 101] Network unreachable on HA's own socket (192.168.10.50:5353) at 00:42:40, matter_server ConnectionFailed at 00:42:48, and Hue bridge discovery failing with 'Network unreachable' at 00:43:07. ENETUNREACH on HA's own mDNS socket means the appliance itself briefly had no network, not a per-device issue. Fully recovered: Hue light entities show state changes at 01:32/02:20 and Elgato at 04:43 today, and no ERROR/Traceback lines appear after 00:43:07. Automations firing inside that window would have silently no-oped against IoT devices. Single occurrence; unrelated to the mini subnet-squat finding (different host). Worth watching for recurrence but no action needed now.

<details><summary>Evidence</summary>

```
TOK=$(python3 -c "import yaml;print(yaml.safe_load(open('foss-setup/.handoff-secrets.yaml'))['hosts']['ha']['api_token'])")
curl -s -m 20 -H "Authorization: Bearer $TOK" http://192.168.10.50:8123/api/hassio/core/logs
2026-08-02 00:40:40.199 ERROR [homeassistant.components.elgato] Error fetching elgato_192.168.20.102 data: An error occurred while communicating with the Elgato device
2026-08-02 00:42:40.162 WARNING [zeroconf] Error with socket 15 (('192.168.10.50', 5353))): [Errno 101] Network unreachable
2026-08-02 00:42:48.081 ERROR [homeassistant.components.matter] Unexpected exception: Connection failed.
matter_server.client.exceptions.ConnectionFailed: Connection failed.
2026-08-02 00:43:07.145 WARNING [homeassistant.components.hue.config_flow] Error while attempting to retrieve discovery information, is there a bridge alive on IP 192.168.20.100 ?
aiohttp.client_exceptions.ClientConnectorError: Cannot connect to host 192.168.20.100:80 ssl:default [Network unreachable]
# recovery: GET /api/states shows hue lights last_updated 2026-08-02T01:32/02:20, elgato 04:43; no errors logged after 00:43:07
```

</details>

### SL14. Update posture note: core 2026.7.2 -> 2026.7.4, HAOS 18.1 -> 18.2, matter-server 9.1.0 -> 9.1.1 pending (all < 21 days)

**Host:** ha · **Component:** HA core/OS/add-on updates · **Auditor:** host:ha · **Work item:** `fix-66`

Live /api/config confirms 2026.7.2 RUNNING. Three update.* entities are 'on': core (2026.7.4 available, pending since 07-28, 5 days), operating system (18.2 available, since 08-01), matter server (9.1.1, since 07-29). Supervisor 2026.07.5 and terminal/SSH add-on are current. The ha-updates-pending check (fix-36) passed today with updates=ok because its threshold is >=21 days pending — correct behavior, not masking; it will fire ~2026-08-18 if the core update is still unapplied. Note only per sweep scope; no action taken (read-only, and updates are user-facing disruptive work for the 4-7AM window anyway).

<details><summary>Evidence</summary>

```
curl -s -m 10 -H "Authorization: Bearer $TOK" http://192.168.10.50:8123/api/config | python3 -c "..."
{'version': '2026.7.2', 'state': 'RUNNING', ...}
# from GET /api/states update.* entities:
update.home_assistant_core_update state: on installed 2026.7.2 latest 2026.7.4 last_changed 2026-07-28T16:54
update.home_assistant_operating_system_update state: on installed 18.1 latest 18.2 last_changed 2026-08-01T01:45
update.matter_server_update state: on installed 9.1.0 latest 9.1.1 last_changed 2026-07-29T07:54
update.home_assistant_supervisor_update state: off installed 2026.07.5
# mini /var/lib/verification/results.json (2026-08-02T10:23:08-04:00): ha-updates-pending | pass | updates=ok (21-day threshold per checks.d/ha.yaml)
```

</details>

### SL15. Top-level 'journaling/n8n/' dir-exclude defeats the '!n8n/*.workflow.json' negation — n8n workflow source silently unversioned on the live side

**Host:** mini · **Component:** /opt/stacks/.gitignore vs journaling/.gitignore (docker-stacks repo) · **Auditor:** svc:docs-life · **Work item:** `fix-65`

The tracked journaling/.gitignore in the live docker-stacks repo documents that n8n *.workflow.json source files SHOULD be committed ('commit the mirrored SOURCE only ... the n8n *.workflow.json') and carries 'n8n/*' + '!n8n/*.workflow.json' to that end. But /opt/stacks/.gitignore line 58 excludes the whole directory ('journaling/n8n/'), and git never descends into a dir-excluded directory, so the nested negation can never re-include anything: bug-report-intake.workflow.json sits on live disk (Jul 27), is ignored (check-ignore exit 0 citing .gitignore:58), and git status is deceptively clean. journal-analyze.workflow.json and journal-webhook-probe.workflow.json are not on live disk at all. Impact is contained because the Home repo tracks all three workflow JSONs (rebuild path intact), but any future workflow export landed only in /opt/stacks would be silently untracked — the recurring orphaned-drift pattern. Not covered by an open task. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'cd /opt/stacks && git status --porcelain journaling; ls /opt/stacks/journaling/n8n/*.workflow.json'
(status empty = clean)
-rw-rw-r-- 1 btabaska btabaska 32854 Jul 27 14:46 /opt/stacks/journaling/n8n/bug-report-intake.workflow.json
ssh mini 'cd /opt/stacks && git check-ignore -v journaling/n8n/bug-report-intake.workflow.json; echo exit=$?; grep -n "n8n" .gitignore | head -3'
.gitignore:58:journaling/n8n/	journaling/n8n/bug-report-intake.workflow.json
exit=0
56:# journaling stack runtime state (bind mounts) — never version (n8n/config holds the encryption key)
58:journaling/n8n/
ssh mini 'cd /opt/stacks && git ls-files journaling'   # no n8n/*.workflow.json tracked
# Home repo by contrast tracks all 3: git ls-files foss-setup/configs/docker-stack/stacks/journaling | grep workflow.json -> 3 files
```

</details>

### SL16. Suwayomi logging recurring thumbnail FileNotFoundException (65 hits in last 2000 log lines, ongoing today)

**Host:** rig · **Component:** suwayomi · **Auditor:** svc:reading · **Work item:** `fix-58`

Suwayomi (Up 27h healthy, restarted with the 08-01 rig boot) repeatedly throws java.io.FileNotFoundException on /home/suwayomi/.local/share/Tachidesk/downloads/thumbnails/<id>.tmp while handling requests — 65 occurrences in the last 2000 log lines across multiple manga IDs (35, 39, 299, 941), observed live today at 12:30–13:16 EDT. Extension-repo errors: 0. The Komga feed path is unaffected (suwayomi-feeds-komga pass, mount=rw), so impact is limited to broken/failed thumbnail rendering in Suwayomi's own web UI, but the recurrence pattern (taxonomy #7-adjacent log noise) means nobody is reading this log. NOT investigated further or fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh rig 'docker logs suwayomi --tail 2000 2>&1 | grep -c "FileNotFoundException"'
65
ssh rig 'docker logs suwayomi --tail 300 2>&1 | grep -iE "error|exception" | tail -4'
13:13:10.121 [DefaultDispatcher-worker-15] ERROR suwayomi.tachidesk.server.JavalinSetup -- IOException while handling the request
java.io.FileNotFoundException: /home/suwayomi/.local/share/Tachidesk/downloads/thumbnails/39.tmp (No such file or directory)
13:16:55.677 [DefaultDispatcher-worker-11] ERROR suwayomi.tachidesk.server.JavalinSetup -- IOException while handling the request
java.io.FileNotFoundException: /home/suwayomi/.local/share/Tachidesk/downloads/thumbnails/39.tmp (No such file or directory)
ssh rig 'docker logs suwayomi --tail 2000 2>&1 | grep -iE "extension" | grep -icE "error|fail"'
0
```

</details>

### SL17. media-arr-file-quality bad=3: Leverage S05E01/E04/E05 library files are Sample-*.avi imports (fix-27 regression)

**Host:** nas · **Component:** sonarr library (Leverage S05) · **Auditor:** flow:movies-tv · **Work item:** `fix-54` · *skeptic-confirmed*

Today's 10:23 run flags three Leverage (S05) episode files as sample files masquerading as library copies (Sample-Leverage.S05E01/S05E04.PROPER/S05E05), the exact 'green-but-not-watchable' class fix-27 remediated. Deluge still holds leverage.redemption S03E07/E08 with label sonarr-imported (different series, imported fine), so this is the old Leverage 2008 S05 content. Not directly re-probed on disk this session (check output + fix-27 pattern match); regression of fix-27, needs re-grab of the three episodes.

*Verify note:* CONFIRMED with corrected mechanism. Fresh probes: (1) results.json 10:23 run shows the filed WATCHABLE_BAD bad=3 output verbatim; (2) Sonarr API (series 92 Leverage 2008): S05E01/E04/E05 hasFile=True with episodeFileId 904591/904592/904593 = the 'NFO & Samples/Sample-*.mp4' records (14.8/6.8/10 MB) — check is a true positive, episodes are mapped to samples; (3) NAS disk (/volume3/tv/Leverage/Leverage.S05.Season.5.COMPLETE.../): full-size real episodes (358/308/324 MB, dated Jun 2018) exist in the same season folder, and Sonarr also holds episodefile records for them (904383-904385). Corrected mechanism: NOT fresh sample imports and NO re-grab needed — a recent disk rescan (all six IDs in the new 904xxx range) re-registered the 2018 samples from the 'NFO & Samples' subfolder and the three episodes re-mapped to them. Plex scans the folder directly and the real files are present, so watchability is likely intact; the defect is Sonarr mapping integrity (upgrade/rename/delete keyed to sample records). Fix: delete the 3 sample episodefile records / exclude Sample-* and 'NFO & Samples' from import, then rescan to re-map to the real files. Severity lowered medium→low (content present on disk, user impact minimal). Files are .mp4 not .avi; deluge leverage.redemption evidence irrelevant as auditor noted.

<details><summary>Evidence</summary>

```
mini /var/lib/verification/results.json (run 2026-08-02T10:23:08-04:00):
media-arr-file-quality | fail | WATCHABLE_BAD bad=3 radarr=0 sonarr=3  sonarr:Leverage=Sample-Leverage.S05E01.HDTV.x264-F(sample) sonarr:Leverage=Sample-Leverage.S05E04.PROPER.HDTV(sample) sonarr:Leverage=Sample-Leverage.S05E05.HDTV.x264-A(sample)
seedbox deluge RPC: label=sonarr-imported 100.0% Seeding age_d=3.4 leverage.redemption.s03e08…; label=sonarr-imported 100.0% Seeding age_d=2.5 leverage.redemption.s03e07…
```

</details>

### SL18. unpackerr polls Radarr/Sonarr at 192.168.1.2 (wrong/old subnet) and times out — likely dead extraction path (cross-lane: may feed sonarr/radarr queue-stuck)

**Host:** mini · **Component:** unpackerr (host service) · **Auditor:** flow:music · **Work item:** `fix-69` · *skeptic-confirmed*

While reviewing the mini journal for the navidrome window I found the host unpackerr service (PID 756) erroring 'context deadline exceeded' against http://192.168.1.2:7878 (Radarr) and http://192.168.1.2:8989 (Sonarr) at 04:31-04:33 EDT Aug 1. The fleet subnet is 192.168.10.0/24 (mini itself is 192.168.10.2) — 192.168.1.2 is either a stale old-subnet config or a squatted docker subnet address (note sys-docker-subnet-squat ha-19 fails today with 3 squats). If unpackerr cannot reach the arrs, RAR extraction never triggers (pattern #8), which plausibly feeds today's sonarr-queue-stuck=16 / radarr-queue-stuck=9 (verify-06) and the media-09 unextractable-titles backlog. Outside my music lane so I did not dig into unpackerr.conf (sec-10 covers its cleartext keys but NOT this wrong address); flagging for the video/infra lane. NOT fixed per read-only mandate.

*Verify note:* Re-probed live: mini host unpackerr.service (PID 756) still errors NOW (Aug 02 13:49-13:53 EDT) against 192.168.1.2:7878/:8989; /etc/unpackerr/unpackerr.conf lines 88+105 confirm the wrong-subnet URLs; from mini curl 192.168.1.2:8989 -> 000 while 192.168.10.4:{8989,7878}/ping -> 200. HOWEVER the impact mechanism is wrong: a second, functioning unpackerr runs as a NAS container (Up 12 days healthy) colocated with sonarr/radarr, actively polling them and Readarr successfully (5 finished extractions, Uptime-Kuma scraping /metrics). Its logs show the exact queue-stuck items with 'no extractable files found' — the 16/9 stuck items are import-side failures (matched-by-ID, no eligible files, unknown author), NOT missing extraction. So extraction path is NOT dead and the cross-lane queue-stuck/media-09 causal link is disproven. Real finding = orphaned legacy host unit on mini (undocumented, not in configs/host/mini/ known units) with stale wrong-subnet config + cleartext arr keys (sec-10 adjacent), generating error noise every ~2min for weeks. Remediation is disable/remove the mini host service, not fix an extraction outage. Severity medium -> low.

<details><summary>Evidence</summary>

```
ssh mini 'journalctl --since "2026-08-01 04:30" --until "2026-08-01 06:00" --no-pager | grep unpackerr | head -4'
Aug 01 04:31:12 macmini unpackerr[756]: [ERROR] 2026/08/01 08:31:12 Radarr (http://192.168.1.2:7878): api.Get(queue): httpClient.Do(req): Get "http://192.168.1.2:7878/api/v3/queue?...": context deadline exceeded (Client.Timeout exceeded while awaiting headers)
Aug 01 04:31:22 macmini unpackerr[756]: [ERROR] 2026/08/01 08:31:22 Sonarr (http://192.168.1.2:8989): api.Get(v3/queue): ... context deadline exceeded
Aug 01 04:33:12 macmini unpackerr[756]: [ERROR] ... Radarr (http://192.168.1.2:7878) ... context deadline exceeded
Aug 01 04:33:22 macmini unpackerr[756]: [ERROR] ... Sonarr (http://192.168.1.2:8989) ... context deadline exceeded
(mini LAN address is 192.168.10.2; today's sweep: sonarr-queue-stuck stuck=16, radarr-queue-stuck stuck=9, sys-docker-subnet-squat=3)
```

</details>

### SL19. 'The Rotten Romans' is the sole wanted-missing book, monitored but unacquired for ~13 days with no forward progress

**Host:** nas · **Component:** bookshelf wanted-list · **Auditor:** flow:books · **Work item:** `fix-57`

Bookshelf wanted/missing shows exactly one record, 'The Rotten Romans' (missing_total=1). Its libreseerr request terminal-errored on 2026-07-20 with the designed operator message ('Book is unmonitored in the backend with no file — nothing will ever search for it. Monitor it or re-request'); it now appears monitored+missing, so it was re-monitored but no indexer has produced it since — 13 days of no movement. The request layer surfaced it correctly (fix-48 machinery working), so this is an operator-action item (manual acquisition via Shelfmark/MAM or unmonitor), not a pipeline fault. NOT actioned per read-only mandate.

<details><summary>Evidence</summary>

```
curl -s -H "X-Api-Key: $BK" 'http://192.168.10.4:8790/api/v1/wanted/missing?pageSize=5&sortKey=title'
-> missing_total=1 / MISSING: The Rotten Romans
ssh mini 'python3 - (read /opt/stacks/libreseerr/data/requests.json)'
-> The Rotten Romans | created=2026-07-20 | err=Book is unmonitored in the backend with no file — nothing will ever search for it. Monitor it or re-request.
Bookshelf history (200-record pull): no grab events for it since history began 2026-07-20T19:38
```

</details>

### SL20. 16 of 19 in-library manga have 0 chapters downloaded — completed/backlist series will never auto-download, so they can never reach Komga

**Host:** rig · **Component:** suwayomi (library download policy) · **Auditor:** flow:manga-comics · **Work item:** `fix-58`

AUTO_DOWNLOAD_CHAPTERS only fires for chapters newly detected by the updater (which is alive — last global update 2026-08-02 ~08:11 EDT), so series added complete (e.g. 'Why Raeliana Ended up at the Duke's Mansion' 0/150 + volume edition 0/27, added 07-28; Berserk 0/403; Iruma-kun 0/552) sit at 0 downloads indefinitely and will never appear in Komga. Only Spy x Family (155/155) and My Dress-Up Darling (124/124) were manually backfilled 07-27, plus 1-chapter samples of Yotsuba&! and His and Her Circumstances. If the read-18 intent is 'library series readable in Komga', these 16 need a manual download pass (or an enqueue-on-add policy); if in-app Suwayomi reading is acceptable this is working as designed. Zero-throughput observation per lane mandate, not repaired per read-only mandate.

<details><summary>Evidence</summary>

```
$ curl -s -X POST http://192.168.10.12:4567/api/graphql -d '{"query":"query{mangas(condition:{inLibrary:true}){nodes{id title downloadCount chapters{totalCount}}}}"}'
4   | Yotsuba&! | dl: 1 / 130
35  | Welcome to Demon School! Iruma-kun | dl: 0 / 552
932 | Spy x Family | dl: 155 / 155
934 | My Dress-Up Darling | dl: 124 / 124
941 | Berserk | dl: 0 / 403
1094| Why Raeliana Ended up at the Duke's | dl: 0 / 150
1095| Why Raeliana ... (Volume) | dl: 0 / 27
(19 series total; 16 at dl:0)
$ curl -s -X POST http://192.168.10.12:4567/api/graphql -d '{"query":"query{lastUpdateTimestamp{timestamp}}"}'
{"data":{"lastUpdateTimestamp":{"timestamp":"1785672756070"}}}   # 2026-08-02 ~08:11 EDT — updater alive
```

</details>

### SL21. Smart-search crit check has zero timeout margin: an identical probe with the check's own curl -m 30 timed out live today

**Host:** nas · **Component:** verification/immich-smart-search-consumer · **Auditor:** flow:photos · **Work item:** `fix-62`

The deployed crit check (rig-immich-ml.yaml) uses curl -s -m 30 against /api/search/smart. My first live probe with the exact same -m 30 returned an empty body (curl timeout); an immediate retry with -m 60 succeeded in 13.0s. Under CLIP cold-start on the NAS iGPU day-fallback or under today's NAS I/O pressure, this check will false-fail its critical severity even though the consumer path works. It passed at 10:23 today by luck of a warm model. Recommend a warm-up pre-request or a larger -m in the check; NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
# probe 1, same -m 30 as the deployed check:
curl -s -m 30 https://immich.tabaska.us/api/search/smart -H "x-api-key: $KEY" -d '{"query":"beach","size":3}'
(empty body -> json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0))
# probe 2, seconds later:
curl -s -m 60 -w 'HTTP=%{http_code} time=%{time_total}s' ... same request
HTTP=200 time=13.037951s
# deployed def foss-setup/verification/checks.d/rig-immich-ml.yaml:
cmd: resp=$(curl -s -m 30 -X POST https://immich.tabaska.us/api/search/smart ... ) | grep -q '"id":' && echo SEARCH_OK
```

</details>

### SL22. Zero new photo uploads in the last 3+ days (newest asset 2026-07-29 10:42Z) — within the 7-day window but trending toward a freshness trip

**Host:** nas · **Component:** immich / upload throughput · **Auditor:** flow:photos · **Work item:** `fix-60` · *skeptic-confirmed*

API counts: exactly 1 asset uploaded since 2026-07-26 (createdAt 2026-07-29T10:42:20Z) and 0 since 2026-07-30. Total library 34,601 photos / 1,340 videos, all owned by one user. Could be a normal usage lull, but if the phone backup app has silently stopped, the check that would catch it in 3 more days is currently dead (see the fix-35 timeout finding), so this is the only early-warning record of the trend.

*Verify note:* Confirmed with fresh probes. (1) Re-ran the API search/metadata queries: 1 asset since 2026-07-26 (createdAt 2026-07-29T10:42:20.707Z), 0 since 2026-07-30 and 2026-08-01; server stats 34601 photos/1340 videos all owned by one user. (2) Independent probe bypassing the API: psql inside immich_postgres on the NAS shows max("createdAt")=2026-07-29 10:42:20 UTC over 42725 non-deleted asset rows — createdAt is the DB record-creation (upload) timestamp, so the finding correctly measures upload freshness, not photo-taken dates. Now 4 days with zero uploads as of 2026-08-02. Not on the known-normal list; low severity stands as an early-warning trend record.

<details><summary>Evidence</summary>

```
for d in 2026-07-26 2026-07-30 2026-08-01; do curl -s -m 30 https://immich.tabaska.us/api/search/metadata -H "x-api-key: $KEY" -d "{\"createdAfter\":\"${d}T00:00:00Z\",\"size\":1}"; done
createdAfter=2026-07-26 total=1 newest_createdAt= 2026-07-29T10:42:20.707Z
createdAfter=2026-07-30 total=0
createdAfter=2026-08-01 total=0
curl -s -m 20 https://immich.tabaska.us/api/server/statistics -H "x-api-key: $KEY"
"photos": 34601, "videos": 1340
```

</details>

### SL23. Kuma's only published status page 'test' is an empty placeholder (0 groups, 0 monitors)

**Host:** mini · **Component:** uptime-kuma status page · **Auditor:** flow:monitoring-alerting · **Work item:** `fix-63`

Kuma itself is healthy (57 active monitors, 0 down as of 13:30 EDT), but the sole published status page is slugged 'test', titled 'Test', and contains zero monitor groups — https://uptime.tabaska.us/status/test renders an empty page. No Homepage widget consumes it (services.yaml has no uptimekuma widget block, tile is href-only), so nothing is broken today, but anyone handed the status URL (e.g. for bug-03-style friend reports) sees a blank page, and per memory the Homepage Kuma widget cannot be added until a real page is published. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini docker exec uptime-kuma mariadb --socket=/app/data/run/mariadb.sock kuma -N -e "SELECT slug, published FROM status_page;"
test	1
... -e "SELECT CONCAT('active=',COUNT(*)) FROM monitor WHERE active=1;" -> active=57
down-monitor join query -> (no rows)

curl -s https://uptime.tabaska.us/status/test | grep -oiE "<title>[^<]*</title>"
<title>Test</title>
curl -s https://uptime.tabaska.us/api/status-page/test -> title: Test | groups: 0 | monitors: 0

grep -n uptimekuma foss-setup/configs/docker-stack/stacks/homepage/config/services.yaml -> (no match; tile is href-only)
```

</details>

### SL24. Terraria server (Up 5 days) has no Homepage tile while sibling game servers do

**Host:** mini · **Component:** homepage services.yaml · **Auditor:** flow:monitoring-alerting · **Work item:** `fix-67`

The terraria container has run on mini for 5 days and is present in the coverage manifest (verification/coverage/mini.containers), but the Homepage Games group only lists Retro Gaming Guide, RomM, AMP, Palworld, Minecraft — no Terraria tile. Minor UI drift vs mandate 3 (live stack is the source of truth for docs/dashboards); a headless game server is a defensible omission but Palworld/Minecraft set the precedent. Everything else checks out: 62 tiles across 12 groups, and recent services BookLogr, Suwayomi, Komga, Audiobookshelf, Shelfmark are all tiled. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'docker ps --format "{{.Names}}\t{{.Status}}" | grep terraria'
terraria	Up 5 days

grep -riE terraria foss-setup/configs/docker-stack/stacks/homepage/config/services.yaml -> (no match)
grep -riE terraria foss-setup/verification/coverage/ -> foss-setup/verification/coverage/mini.containers:terraria

curl -s -H "Host: home.tabaska.us" http://192.168.10.2:3010/api/services | python3 (group dump)
Games (5): Retro Gaming Guide, RomM, AMP, Palworld, Minecraft
Reading (7): BookLogr, Calibre-Web, Audiobookshelf, Komga, Suwayomi, Wallabag, Miniflux
TOTAL tiles: 62
```

</details>

### SL25. Stale synthetic probe issue #14 open since 2026-07-27 — e2e cleanup failed once, no residue sweeper, and it never got triaged

**Host:** mini · **Component:** home/household-bugs (Forgejo) / bugreport-e2e probe · **Auditor:** flow:bug-intake · **Work item:** `fix-67`

The household-bugs repo contains exactly one issue: #14 '[Something else] n8n-bugreport-probe 1785202787', created 2026-07-27T21:39:47-04:00 by the bugreport-e2e sentinel probe, still open with 0 comments and no 'triaged' label. The probe script's own docstring promises 'DELETE the probe issue -> zero residue in the repo the operator reads' — that delete failed once ~6 days ago and nothing sweeps leftovers, so synthetic noise sits in the tracker the household reads (and it also shows the bugreport sentinel path never received a triage comment). Today's runs cleaned up correctly (#61/#62 deleted=True), so this is a one-time cleanup failure plus a missing residue guard, not a live break. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
TOK=$(python3 -c "...['forgejo']['verification_bugreport_probe_token']")
curl -s -H "Authorization: token $TOK" "https://git.tabaska.us/api/v1/repos/home/household-bugs/issues?state=all&limit=8&type=issues"
#14 | [Something else] n8n-bugreport-probe 1785202787 | state=open | comments=0 | labels=['service:triage', 'sev:annoying', 'source:home'] | created=2026-07-27T21:39:47-04:00
(only issue returned; today's probes reached #61/#62 and were deleted)
ssh mini 'head -60 /opt/verification/bin/bugreport-e2e.py | grep -n delete'
14:  4. DELETE the probe issue -> zero residue in the repo the operator reads.
```

</details>

### SL26. Discord notify leg is a live no-op: DISCORD_BUGS_WEBHOOK empty in the running n8n container while the vault already holds discord/bugs_webhook_url `known-issue`

**Host:** mini · **Component:** n8n bug-report-intake workflow / Discord notify leg · **Auditor:** flow:bug-intake

The workflow's 'Discord configured?' IF gate routes on $env.DISCORD_BUGS_WEBHOOK; in the live n8n container that env var is set but EMPTY (grep line length 22 = bare NAME=), and /opt/stacks/journaling/.env has no non-empty line for it, so 'Notify Discord' never fires and real reports notify ntfy only. The compose file documents this as 'DEFERRED (empty) — the Discord node no-ops while unset', but the vault meanwhile contains discord/bugs_webhook_url, so the credential exists and was never wired — the deferral has drifted into a forgotten leg. Covered by open task bug-03 (Discord friend reports / Discord-leg gaps). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini 'docker exec n8n sh -c "env | grep \"^DISCORD_BUGS_WEBHOOK=\" | wc -c"'
22   (= 'DISCORD_BUGS_WEBHOOK=' + newline -> empty value)
ssh mini 'sudo grep -cE "^DISCORD_BUGS_WEBHOOK=..+" /opt/stacks/journaling/.env'
0
ssh mini 'grep -n DISCORD_BUGS_WEBHOOK /opt/stacks/journaling/compose.yaml'
97: # DISCORD_BUGS_WEBHOOK is DEFERRED (empty) — the Discord node no-ops while unset
workflow node 'Notify Discord': url = {{ $env.DISCORD_BUGS_WEBHOOK }}; gate 'Discord configured?' tests $json.discordSet == true
vault key exists: /discord/bugs_webhook_url (name only; value not read)
```

</details>

### SL27. Real-report notify branch (ntfy 'bugs') has zero monitoring coverage by design — a rotted NTFY_TOKEN would fail silently

**Host:** mini · **Component:** n8n bug-report-intake workflow / ntfy notify branch · **Auditor:** flow:bug-intake · **Work item:** `fix-67` · *skeptic-confirmed*

Both e2e probes carry a healthcheck sentinel that deliberately skips the 'Real report? (notify)' gate so monitoring never pages the phone (documented in bugreport-e2e.py). Consequence: the ntfy publish leg (POST http://ntfy:80/bugs with Authorization from $env.NTFY_TOKEN) is never exercised by any check, so if that token rots or the topic ACL changes, a genuine household report would file the Forgejo issue but silently drop the notification — pattern #2 green-but-broken at the notify consumer end, invisible until a real report is missed. Static wiring verified healthy this session: NTFY_TOKEN present (32 chars, value not read), ntfy container Up 3 weeks (healthy). Filed as a coverage-design gap, not a live fault; a token-validity probe against a sentinel-suppressed or ops-only topic would close it. NOT fixed per read-only mandate.

*Verify note:* CONFIRMED with 4 fresh probes. (1) Workflow JSON: 'Real report? (notify)' IF node gates on $json.notify==true and 'Notify ntfy' (Bearer $env.NTFY_TOKEN -> http://ntfy:80/bugs) hangs only off its true branch. (2) Deployed mini /opt/verification/bin/bugreport-e2e.py carries SENTINEL n8n-bugreport-probe and documents notify suppression — sentinel runs never traverse the ntfy leg. (3) Full sweep of repo + deployed checks.d: bug-intake.yaml covers form/tile/Forgejo-e2e/triage only; alerting.yaml covers ntfy liveness+vhost+upstream-relay; reading.yaml checks libreseerr's token (different container). No check validates the n8n container's NTFY_TOKEN against the server or exercises a bugs-topic publish. (4) Premise strengthened: secrets.yaml ntfy-anon-publish-denied confirms deny-all, so a rotted token = 403 dropped publish, not harmless; n8n NTFY_TOKEN currently set non-empty (length only, value unread). ntfy POST fires after issue creation and n8n execution errors are unmonitored, so failure mode (issue files, ping silently lost) is exactly as filed. Severity low stands — design gap, wiring currently healthy. Suggested closer unchanged: token-validity probe against a sentinel-suppressed or ops-only topic.

<details><summary>Evidence</summary>

```
grep 'Notify ntfy' workflow node (repo foss-setup/configs/docker-stack/stacks/journaling/n8n/bug-report-intake.workflow.json):
url: http://ntfy:80/bugs
headers: Authorization = <REDACTED> {{ $env.NTFY_TOKEN }}
ssh mini 'docker exec n8n sh -c "env | grep \"^NTFY_TOKEN=\" | wc -c"'
44   (= 'NTFY_TOKEN=' + 32-char token + newline -> set, non-empty)
ssh mini 'head -60 /opt/verification/bin/bugreport-e2e.py | grep -n notify'
10: the notify gate SKIPS ntfy/Discord for sentinel reports, so a monitoring run never
ssh mini 'docker ps --format "{{.Names}} {{.Status}}" | grep ntfy'
ntfy Up 3 weeks (healthy)
```

</details>

### SL28. dotfiles GitHub origin is 2 commits behind Forgejo — inverse of the local-ai-tooling mirror gap

**Host:** device · **Component:** dotfiles repo GitHub mirror (github.com/btabaska/dotfiles) · **Auditor:** flow:git-control-plane · **Work item:** `fix-65`

The Mac chezmoi source repo HEAD 394188f matches forgejo/main exactly (0/0 divergence, verified after fresh fetch), but the GitHub origin remote is 2 commits behind: missing 84ddc79 (Ghostty + Starship + zsh terminal setup, per-OS chezmoiignore) and 394188f (README + idempotent install.sh bootstrap), last committed 2026-07-22 — the GitHub mirror has been stale ~11 days. Same push-both-remotes discipline gap as the local-ai-tooling finding but in the opposite direction (there Forgejo lags GitHub; here GitHub lags Forgejo). Hygiene-level: the authoritative fleet remote (Forgejo) is current. NOT fixed per read-only mandate; fix is one push to origin.

<details><summary>Evidence</summary>

```
chezmoi git -- remote -v
forgejo git@forgejo:home/dotfiles.git (fetch/push)
origin  git@github.com:btabaska/dotfiles.git (fetch/push)
chezmoi git -- fetch forgejo; chezmoi git -- fetch origin   (both clean)
chezmoi git -- rev-list --count forgejo/main..HEAD -> 0
chezmoi git -- rev-list --count HEAD..forgejo/main -> 0
chezmoi git -- rev-list --count origin/main..HEAD -> 2
chezmoi git -- log --oneline origin/main..HEAD
394188f Add README + idempotent install.sh bootstrap; ignore repo docs
84ddc79 Add Ghostty + Starship + zsh terminal setup; per-OS chezmoiignore
```

</details>

### SL29. Immich pg dumps accumulate with no observed rotation (~254MB/day, 16 dumps since Jul 18)

**Host:** nas · **Component:** /volume1/docker/immich/backups (DSM task 9) · **Auditor:** flow:backups · **Work item:** `fix-60`

The dump dir holds every daily dump since 2026-07-18 (16 files, ~254MB each, ~4GB total) with no pruning observed. volume1 is only 29% used so local pressure is nil, but the dir sits under /docker which the Hyper Backup task ships to B2, so the offsite set grows ~7.6GB/month of largely redundant full dumps on top of HB's own versioning. Hygiene: add a keep-N rotation to DSM task 9. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh nas 'ls /volume1/docker/immich/backups | wc -l; ls /volume1/docker/immich/backups | head -2; df -h /volume1 | tail -1'
16
immich-2026-07-18.sql.gz
immich-2026-07-19.sql.gz
/dev/mapper/cachedev_2   14T  4.0T   11T  29% /volume1
ssh nas 'ls -la /volume1/docker/immich/backups | tail -2'
-rw-r--r-- 1 root root 254761967 Aug  1 02:31 immich-2026-08-01.sql.gz
-rw-r--r-- 1 root root 254764112 Aug  2 02:31 immich-2026-08-02.sql.gz
```

</details>

### SL30. Hub filesystem watcher dead on game-saves: 'failed to set up inotify handler' — changes on the NAS side only picked up by periodic rescan, and no check watches watchError

**Host:** nas · **Component:** syncthing hub, game-saves folder · **Auditor:** flow:syncthing-mesh · **Work item:** `fix-67`

Live db/status for game-saves on the hub (2026-08-02 13:34 EDT) carries watchError 'failed to set up inotify handler. Please increase inotify limits' while the default folder's watcher is fine — the Synology per-user inotify watch limit is exhausted at the second folder. Consequence: any change made directly on the NAS copy (e.g. a manual save restore under /volume1/docker/syncthing/game-saves, the documented restore surface) propagates only at the periodic rescan (~1h) instead of instantly; peer-originated syncs are unaffected, which is why completion stays 100%. Neither game-saves-mesh-synced nor syncthing-hub-mesh-direct parses watchError, so this degradation is invisible to verification. Touches done work game-12/foss-03 but fails no existing check. NOT fixed per read-only mandate (fix = raise fs.inotify.max_user_watches on DSM or accept scan-only and codify a watchError probe).

<details><summary>Evidence</summary>

```
PW=$(python3 -c "import yaml;print(yaml.safe_load(open('foss-setup/.handoff-secrets.yaml'))['sudo']['nas_password'])")
printf '%s\n' "$PW" | ssh -o ConnectTimeout=10 nas 'sudo -S sh -c '"'"'API=$(grep -o "<apikey>[^<]*</apikey>" /volume1/docker/syncthing/config/config.xml | sed "s/<[^>]*>//g"); curl -s -H "X-API-Key: $API" "http://127.0.0.1:8384/rest/db/status?folder=game-saves"'"'"''
"state": "idle", "needFiles": 0, "errors": 0, "pullErrors": 0,
"watchError": "failed to set up inotify handler. Please increase inotify limits, see https://docs.syncthing.net/users/faq.html#inotify-limits"
same call with folder=default -> "watchError": ""
repo foss-setup/verification/checks.d/game-saves.yaml cmd parses globalFiles/needFiles/state/completion only — watchError not asserted
```

</details>

### SL31. Hub compose header still documents relays/global-discovery as an enabled 'harmless fallback' — contradicts the hardened no-relay posture live and in the wiki

**Host:** repo · **Component:** foss-setup/configs/nas/syncthing/docker-compose.yml · **Auditor:** flow:syncthing-mesh · **Work item:** `fix-68`

The repo (and mirrored live) hub compose header reads 'Global-discovery/relays stay as harmless fallback — file data never leaves the LAN', which describes the pre-hardening state. Live hub config has globalAnnounceEnabled=False and relaysEnabled=False, and the wiki service page + sync.yaml check both state relays/global discovery are DISABLED fleet-wide with an explicit 'do not re-enable'. A future operator following the compose comment could re-enable relays believing them harmless, silently reintroducing the cloud path the syncthing-hub-mesh-direct check exists to forbid. Doc-vs-live drift (standing mandate 3), touching done work foss-03. NOT fixed per read-only mandate (one-line comment correction + mirror to /volume1/docker/syncthing/docker-compose.yml).

<details><summary>Evidence</summary>

```
cd /Users/brandontabaska/GitHub/Home && grep -n -A1 'NO CLOUD' foss-setup/configs/nas/syncthing/docker-compose.yml
8:# NO CLOUD: peers connect over the LAN by static address (tcp://<ip>:22000).
9:# Global-discovery/relays stay as harmless fallback — file data never leaves
10:# the LAN (verified: connection type "tcp (LAN)").
live hub /rest/config options (via NAS sudo curl): globalAnnounceEnabled=False relaysEnabled=False
wiki foss-setup/wiki/docs/services/syncthing.md:13: 'relays + global discovery are DISABLED fleet-wide' ... :29 'Relays and global discovery are disabled in each node's options; do not re-enable them.'
```

</details>

### SL32. rig-esde-romm-library check omits the live wiiu platform from its system sweep and its 8000-rom threshold cannot detect loss of any single small platform

**Host:** repo · **Component:** foss-setup/verification/checks.d/retro-emulation.yaml (rig-esde-romm-library) · **Auditor:** flow:retro · **Work item:** `fix-62`

The check sums rom counts over 7 systems (gb gba n64 nes snes gc wii) but the live ES-DE tree has 8 symlinks — wiiu (34 roms, added with the 2026-07-19 batch) is uncounted, which is why the check reports roms=8332 vs RomM's 8364. Separately, the pass threshold is a single aggregate >=8000, so a vanished small platform dir (wiiu 34, ngc 101, wii 177, or even n64 299) would still pass — only a gross mount/library failure trips it. Concrete consequence: a wiiu- or ngc-only ACL/dir regression on the NAS share would be invisible to monitoring. Check-definition drift versus live library composition; NOT fixed per read-only mandate (fix would be adding wiiu to the loop and/or per-system minimums).

<details><summary>Evidence</summary>

```
foss-setup/verification/checks.d/retro-emulation.yaml lines 22-26:
      for s in gb gba n64 nes snes gc wii; do
      c=$(ls "/home/btabaska/ROMs/$s" 2>/dev/null | grep -vi eaDir | wc -l);
      n=$((n+c));
      done;
      if [ "$n" -ge 8000 ]; then echo "ESDE-ROMM-OK roms=$n"; else echo "LIBRARY-THIN roms=$n"; exit 1; fi
ssh rig 'ls /home/btabaska/ROMs/' -> gb gba gc n64 nes snes wii wiiu  (8 systems live; wiiu absent from check loop)
RomM API: wiiu rom_count=34; check output today roms=8332 vs RomM total 8364
```

</details>

### SL33. shelfmark compose drifts from repo mirror (comment-only): live lacks the rshared/boot-task NOTE the repo copy carries

**Host:** nas · **Component:** /volume1/docker/shelfmark/docker-compose.yml vs configs/nas/shelfmark/ · **Auditor:** repo:live-drift · **Work item:** `fix-68`

Per-app diff of all 16 NAS compose stacks (2026-08-02 ~13:41 EDT): 15 are byte-identical, shelfmark differs. The drift is comments only — the repo copy (dated 2026-07-21) documents the seedbox bind mount's rshared requirement and the DSM 15.task boot-rshared re-apply, which the live file never received; services/images/volumes are functionally identical. Still byte-drift under the anti-drift rule, and configs/nas/ has NO automated mirror tripwire (unlike mini's stack-mirror-drift check), so this class only surfaces on manual sweeps. NOT fixed per read-only mandate; fix = copy the repo file to /volume1/docker/shelfmark/ (or vice versa) and consider a nas-mirror variant of stack-mirror-check.

<details><summary>Evidence</summary>

```
PW=$(python3 -c "...['sudo']['nas_password']"); printf '%s\n' "$PW" | ssh nas 'sudo -S sh -c '...cat each /volume1/docker/<app>/compose...''  # 14 stacks + adguard-nas + beszel-agent
for p in */*; do cmp -s "$p" "$REPO/$p" && echo SAME || echo DIFF; done
SAME: 13 of 14 configs/nas mirrors; DIFF: shelfmark/docker-compose.yml
cmp adguard-nas/compose.yaml configs/docker-stack/stacks/adguard-nas/compose.yaml -> SAME
cmp beszel-agent/compose.yaml configs/nas/beszel/compose.yaml -> SAME
diff -u repo live (shelfmark, trimmed):
-# Secrets in shelfmark.env (gitignored; see shelfmark.env.example). Deployed on the NAS at
-# NOTE: the seedbox bind mount requires the rclone FUSE mount to be `rshared`:
-#   sudo mount --make-rshared /volume1/mounts/seedbox-files
-# (re-applied at boot by the DSM boot-up task 15.task via boot-rshared.sh).
+# Secrets in shelfmark.env (gitignored). Deployed alongside the legacy stack; nothing retired yet.
(volumes/image/restart lines identical)
```

</details>

### SL34. Three cosmetic repo-vs-live drifts in mini host config: stale Documentation= URL live, stripped timer comments, minified daemon.json — plus a stale 'STAGED — NOT YET APPLIED' header on the netplan repo file

**Host:** mini · **Component:** configs/host/mini/ doc-only mirrors (net-selfheal, static-ip, docker) · **Auditor:** repo:live-drift · **Work item:** `fix-68`

Byte-compare of all mini host units/scripts (2026-08-02 ~13:43 EDT): 8 units and all 4 /usr/local/sbin scripts checked; 3 files drift, none functionally. (1) live net-selfheal.service Documentation= still points at a Mac-local file:// path that does not exist on mini; the repo copy has the wiki URL — repo improved, live never redeployed. (2) live apply-static-ip.timer lacks the repo's re-arm comment block (and repo says "tonight's" vs live "tonights"). (3) live /etc/docker/daemon.json is the same JSON minified to one line vs pretty-printed in repo. Additionally the repo netplan file 00-installer-config.static.yaml still opens with 'STAGED — NOT YET APPLIED' although the static config HAS been live as /etc/netplan/00-installer-config.yaml since 2026-07-10 (semantic content matches: 192.168.10.2/24 static, same routes/nameservers) — violates mandate 3 (docs describe what runs). All doc-only; NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
diff configs/host/mini/net-selfheal/net-selfheal.service <(ssh mini cat /etc/systemd/system/net-selfheal.service)
-Documentation=https://wiki.tabaska.us/reference/hosts/mini-network-resilience/
+Documentation=file:///Users/brandontabaska/Documents/Home/foss-setup/docs/handoff-rollout-state.md
diff configs/host/mini/static-ip/apply-static-ip.timer live: repo-only comment block '# One-shot: the apply script disables this timer...' absent live
daemon.json: identical JSON, live single-line vs repo pretty-printed (log-opts max-size 10m/max-file 3, address pools 172.16.0.0/12 + 10.201.0.0/16)
live /etc/netplan/00-installer-config.yaml: dhcp4: false / addresses: [192.168.10.2/24] (static APPLIED)
repo 00-installer-config.static.yaml line 1: '# STAGED — NOT YET APPLIED...'
SAME: tv-torrent-cleanup.{service,timer,sh} net-selfheal.{timer,sh} apply-static-ip.{service,sh} lidarr-artist-monitor-reconcile.{service,timer,py}
```

</details>

### SL35. mini-paperless / mini-wallabag / mini-mealie / mini-tautulli remain bare HTTP-status liveness probes — the exact green-but-broken class mandate 1 exists to prevent, with no open task to deepen them

**Host:** repo · **Component:** checks.d/mini-services.yaml liveness-only probes · **Auditor:** repo:verification-suite · **Work item:** `fix-62`

All four checks assert only an HTTP status code on the root URL (paperless 302, wallabag 302, mealie 200, tautulli 303 — three of them mere login redirects). None touches a consumer path (document count/ingest freshness for paperless, article save for wallabag, recipe API for mealie, Plex-stats query for tautulli), so any of them can be 'green' with a dead database or a stalled ingest — the 2026-07-16 audit's 30+ green-but-broken lesson (failure-pattern #2/#13). read-08 (wallabag KOReader plugin) is adjacent but does not cover check depth, and no other open task does; filing the coverage gap per mandates 1 and 2. Low severity: no active breakage observed behind them today, and the fleet-sweep reference already names them as known liveness-only — this makes the gap a tracked work item rather than tribal knowledge.

<details><summary>Evidence</summary>

```
grep -n -A4 'id: mini-paperless\|id: mini-wallabag\|id: mini-mealie\|id: mini-tautulli' foss-setup/verification/checks.d/mini-services.yaml
mini-paperless: cmd: curl -s -o /dev/null -m 8 -w '%{http_code}' http://localhost:8000/  expect: '^302$'
mini-wallabag: cmd: curl -s -o /dev/null -m 8 -w '%{http_code}' http://localhost:8085/  expect: '^302$'
mini-mealie:   cmd: curl -s -o /dev/null -m 8 -w '%{http_code}' http://localhost:9000/  expect: '^200$'
mini-tautulli: cmd: curl -s -o /dev/null -m 8 -w '%{http_code}' http://localhost:8181/  expect: '^303$'
```

</details>

### SL36. README still describes the plan-era fleet: 10-stack mini list vs 35 repo stacks / 46 live containers, LinuxGSM/Pelican vs live AMP, Dependency-Track reference

**Host:** repo · **Component:** foss-setup/README.md · **Auditor:** repo:tracker-wiki · **Work item:** `fix-68`

foss-setup/README.md:39-40 enumerates the mini docker-stack as exactly 10 stacks ('seerr, miniflux, navidrome, caddy, adguard, dockge, beszel, uptime-kuma, ntfy, diun') while configs/docker-stack/stacks/ holds 35 stack dirs and the live mini runs 46 containers. Phase 5 (line ~131) still plans 'Game servers (LinuxGSM/Pelican)' though the live game layer is AMP, and the inventory line still cites Dependency-Track, which is retired. Violates mandate 3 (document what's running, not what was planned). The alternatives/ line is still accurate (dockhand, pihole exist). NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
sed -n '38,40p' foss-setup/README.md
│   ├── docker-stack/          # the Mac mini stack; mirrors /opt/stacks 1:1 (Dockge)
│   │   ├── stacks/<svc>/       # seerr, miniflux, navidrome, caddy, adguard, dockge,
│   │   │                       #   beszel, uptime-kuma, ntfy, diun
ls foss-setup/configs/docker-stack/stacks/ | wc -l -> 35
wc -l live-mini.txt -> 46 (docker ps names)
README Phase 5: 'Game servers (LinuxGSM/Pelican) and Apollo + Moonlight streaming'
README inventory line: 'SBOM/inventory layer (Phase 4): inventory.md, Dependency-Track Homepage widget, ...'
```

</details>

### SL37. Stale repo path ~/Documents/Home persists in 8 locations across 4 hand-maintained wiki pages; actual checkout is ~/GitHub/Home

**Host:** repo · **Component:** foss-setup/wiki/docs/ (hand-maintained pages) · **Auditor:** repo:tracker-wiki · **Work item:** `fix-68`

The wiki index and three reference/operations pages still state the repo lives at /Users/brandontabaska/Documents/Home (with copy-paste commands using that path), but the live checkout is /Users/brandontabaska/GitHub/Home. Anyone pasting the documented scp/cd commands gets 'no such file or directory'. These are hand-maintained pages (not generator outputs), so the fix is a direct edit + wiki rebuild. fleet-sweep-reference.md:379 already documents this drift axis; it is still unremediated. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
grep -rn 'Documents/Home' --include='*.md' . | grep -v .git/
foss-setup/wiki/docs/index.md:48:| **GitHub `btabaska/home-config`** | `origin` of `~/Documents/Home` | ...
foss-setup/wiki/docs/operations/repo-structure.md:12: (`/Users/brandontabaska/Documents/Home`) confirms **two remotes**...
foss-setup/wiki/docs/operations/repo-structure.md:23: the git root is `/Users/brandontabaska/Documents/Home`...
foss-setup/wiki/docs/operations/repo-structure.md:105: (`/Users/brandontabaska/Documents/Home/.gitignore`)...
foss-setup/wiki/docs/reference/nas/calibre-web-automated.md:54:cd ~/Documents/Home/foss-setup/configs/nas
foss-setup/wiki/docs/reference/seedbox/music-pipeline.md:132:scp -r ~/Documents/Home/foss-setup/...
foss-setup/wiki/docs/reference/seedbox/music-pipeline.md:166-167: scp ~/Documents/Home/foss-setup/... (x2)
```

</details>

### SL38. rig README still frames local-ai-tooling as a GitHub-only external repo — superseded by the ai-02..07 dual-remote (Forgejo) fidelity work

**Host:** repo · **Component:** foss-setup/configs/host/rig/README.md · **Auditor:** repo:tracker-wiki · **Work item:** `fix-68`

configs/host/rig/README.md:40-42 describes local-ai-tooling as 'the separate local-ai-tooling repo (github.com/btabaska/local-ai-tooling)' with no mention of the Forgejo remote. Since ai-02..07 (2026-07-29) the repo is dual-remoted (push BOTH origin+forgejo, guarded by the ai-tooling-clean-pushed tripwire), so the GitHub-only framing is stale. This matters today: the ai-tooling-clean-pushed check is currently failing precisely because forgejo (b24c...) is behind origin/HEAD (9a11062) — an ai-03 regression counted in the regression-ledger finding — and the README a reader would consult omits the push-both requirement. The pointer-not-copy guidance for fleet-mcp.service and the ollama override remains valid. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
sed -n '40,42p' foss-setup/configs/host/rig/README.md
Two rig units are owned by the separate **`local-ai-tooling`** repo
(`github.com/btabaska/local-ai-tooling`, checked out on the rig at
`~/Documents/GitHub/local-ai-tooling/`). Mirroring them here would create cross-repo drift, so
grep -n -iE 'forgejo' foss-setup/configs/host/rig/README.md -> (no matches)
Today's daily run: ai-tooling-clean-pushed | warn | ai-03 | head=9a11062 origin=9a11062 forgejo=b24ca1d
```

</details>

### SL39. Tracked rig flatpak inventory is zero bytes while the live rig has 8 installed flatpak apps — rebuild inventory is wrong

**Host:** repo · **Component:** foss-setup/hosts/cachyos/flatpak.txt · **Auditor:** repo:junk-deadpaths · **Work item:** `fix-65`

foss-setup/hosts/cachyos/flatpak.txt (captured 2026-07-19, tracked in git) is 0 bytes, but live rig 'flatpak list --app' returns 8 applications today (Chrome, Steam, ungoogled-chromium, librewolf, TinyWiiBackupManager, +3 more). The sibling zero-byte files cron.d-listing.txt and crontabs.txt were verified legitimately empty (rig has no /etc/cron.d and no crontab binary), so only flatpak.txt is an invalid capture — likely run over ssh where flatpak returned nothing. Consequence: a rig rebuild from this inventory (glue-06 rebuild-drill capstone) silently drops the desktop app set; adjacent to open task glue-02 (rig desktop baseline) but this is drift of an existing tracked inventory file. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ ls -la foss-setup/hosts/cachyos/ | grep -E 'flatpak|cron'
.rw-r--r-- 0 brandontabaska 19 Jul 18:45 cron.d-listing.txt
.rw-r--r-- 0 brandontabaska 19 Jul 18:45 crontabs.txt
.rw-r--r-- 0 brandontabaska 19 Jul 18:45 flatpak.txt
$ ssh rig 'flatpak list --app --columns=application 2>/dev/null | wc -l; flatpak list --app --columns=application 2>/dev/null | head -5'
8
com.google.Chrome
com.valvesoftware.Steam
io.github.ungoogled_software.ungoogled_chromium
io.gitlab.librewolf-community
it.mq1.TinyWiiBackupManager
$ ssh rig 'ls /etc/cron.d; crontab -l'
ls: cannot access '/etc/cron.d': No such file or directory
/bin/bash: line 1: crontab: command not found
```

</details>

### SL40. 53 stale agent-session artifacts in mini /tmp older than 7 days, including two session-cookie files and an Uptime-Kuma DB copy

**Host:** mini · **Component:** /tmp · **Auditor:** repo:junk-deadpaths · **Work item:** `fix-69`

mini /tmp holds 53 non-system files/dirs older than 7 days from past agent sessions (excluding systemd-private/tmux/socket dirs): scratch python (htr.py, e2e.py, bnc.py, find_phantom.py, exec_nodes.py...), fix-session dirs (fix29-deploy, fix42-pretest), json dumps (rmovies.json, llmc.json, dl.json), a macOS ._verification junk file, a root-owned zero-byte kuma-ro.db (Jul 9), and notably /tmp/ls.cookies (Jul 20) and /tmp/romm-cookies.txt (Jul 20) which are world-readable session-cookie files. Cookies are likely expired but leaving auth material in /tmp is bad hygiene. Also /tmp/sweep-1320.log dates to Jul 10 (previous audit leftover). Nothing deleted per read-only mandate.

<details><summary>Evidence</summary>

```
$ ssh mini 'find /tmp -maxdepth 1 -mtime +7 \( -type f -o -type d \) ! -path /tmp ! -name ".*-unix" ! -name "systemd-private-*" ! -name "tmux-*" | wc -l'
53
$ ssh mini 'find /tmp -maxdepth 1 -mtime +7 ... | head' (sample)
/tmp/sweep-1320.log /tmp/ls.cookies /tmp/plex.out /tmp/htr.py /tmp/e2e.py
/tmp/fix42-pretest /tmp/rmovies.json /tmp/llmc.json /tmp/._verification
/tmp/kuma-ro.db /tmp/fix29-deploy /tmp/romm-cookies.txt /tmp/dl.json
$ ssh mini 'ls -la /tmp/ls.cookies /tmp/romm-cookies.txt /tmp/kuma-ro.db /tmp/sweep-1320.log'
-rw-r--r-- 1 root     root        0 Jul  9 20:04 /tmp/kuma-ro.db
-rw-rw-r-- 1 btabaska btabaska  131 Jul 20 19:19 /tmp/ls.cookies
-rw-rw-r-- 1 btabaska btabaska  226 Jul 20 01:29 /tmp/romm-cookies.txt
-rw-rw-r-- 1 btabaska btabaska 1076 Jul 10 09:22 /tmp/sweep-1320.log
```

</details>

### SL41. 12 stale ad-hoc results-<suite>.json side files (Jul 14-21) littering the verification state dir alongside live scheduled outputs

**Host:** mini · **Component:** /var/lib/verification/results-*.json · **Auditor:** repo:junk-deadpaths · **Work item:** `fix-69`

Of ~29 results-*.json side files in /var/lib/verification, 12 have internal timestamps older than 7 days: results-alerting.json (2026-07-15), results-verification-self (07-18), results-gaming/power-journal/mini-services (07-18), results-backups/host-hygiene/media-aux/nas-host (07-19), results-seedbox (07-20), results-tier-reading (07-21), and results-media-watchable etc. from 07-26. Files fresh today (results-tier-fast 13:35, results-docker-fleet/media/url 12:40-41) correlate with the live verification-quick/fast timers, so those are legitimate scheduled outputs — the stale ones are ad-hoc suite-run leftovers that no longer reflect state and could mislead a future reader. Not deleted per read-only mandate; suggest the runner or a tidy job expire side files.

<details><summary>Evidence</summary>

```
$ ssh mini 'for f in /var/lib/verification/results-*.json; do echo "$f"; python3 -c "import json;print(json.load(open(...))[\"timestamp\"])"; done' (trimmed)
results-alerting.json    2026-07-15T00:04:54+00:00
results-verification-self.json 2026-07-18T03:11:55+00:00
results-gaming.json      2026-07-18T16:01:15+00:00
results-backups.json     2026-07-19T10:03:32-04:00
results-host-hygiene.json 2026-07-19T10:40:28-04:00
results-seedbox.json     2026-07-20T19:30:13-04:00
results-tier-reading.json 2026-07-21T09:05:00-04:00
results-tier-fast.json   2026-08-02T13:35:26-04:00  (fresh, scheduled)
$ ssh mini 'systemctl list-timers --no-pager | grep -i verif'
Sun 2026-08-02 14:40:02 EDT ... verification-quick.timer
Mon 2026-08-03 10:15:47 EDT ... verification.timer
n/a ... Sun 2026-08-02 13:45:06 EDT 3s ago verification-fast.timer
```

</details>

### SL42. Mirror-dir naming mismatch: live stack dir is 'syncthing' but repo mirror is 'syncthing-node' — a drift trap for the stacks/<app> mirroring rule

**Host:** repo · **Component:** foss-setup/configs/docker-stack/stacks/syncthing-node vs mini /opt/stacks/syncthing · **Auditor:** repo:junk-deadpaths · **Work item:** `fix-68`

The mini stack lives at /opt/stacks/syncthing (running container 'syncthing'), but its repo mirror is foss-setup/configs/docker-stack/stacks/syncthing-node/. Content is currently identical (compose.yaml md5 36cbbd71... matches both sides), so no drift today — but CLAUDE.md's rule is 'mirror changed files back to configs/docker-stack/stacks/<app>/', and an agent following it literally would create a new stacks/syncthing/ dir and orphan syncthing-node, splitting the mirror. Rename one side or document the exception. NOT fixed per read-only mandate.

<details><summary>Evidence</summary>

```
$ ssh mini 'ls -1 /opt/stacks/syncthing/; docker ps --format "{{.Names}}" --filter "label=com.docker.compose.project.working_dir=/opt/stacks/syncthing"'
compose.yaml
home
syncthing
$ ls -1 foss-setup/configs/docker-stack/stacks/ | grep sync
syncthing-node
$ ssh mini 'md5sum /opt/stacks/syncthing/compose.yaml'; md5 -r foss-setup/configs/docker-stack/stacks/syncthing-node/compose.yaml
36cbbd71437851d86de73be2bf725fdf  /opt/stacks/syncthing/compose.yaml
36cbbd71437851d86de73be2bf725fdf foss-setup/configs/docker-stack/stacks/syncthing-node/compose.yaml
```

</details>

### SL43. adguard-nas (a NAS-deployed stack) is filed under the mini docker-stack mirror tree instead of configs/nas/

**Host:** repo · **Component:** foss-setup/configs/docker-stack/stacks/adguard-nas · **Auditor:** repo:junk-deadpaths · **Work item:** `fix-68`

foss-setup/configs/docker-stack/stacks/adguard-nas/ contains the compose for the NAS secondary AdGuard (deploys from /volume1/docker/adguard-nas/ per its own header comment), but CLAUDE.md's convention is 'NAS compose lives in /volume1/docker/<app>/; repo mirror under foss-setup/configs/nas/' — and configs/nas/ has 17 other NAS apps but not adguard-nas. The dir has a README and dns-resilience cross-link so the placement may be semi-deliberate (grouping both AdGuards), but as filed it violates the stated anti-drift convention and someone syncing NAS state from configs/nas/ would miss it. NOT moved per read-only mandate.

<details><summary>Evidence</summary>

```
$ head -8 foss-setup/configs/docker-stack/stacks/adguard-nas/compose.yaml
# AdGuard Home — SECONDARY network DNS (NAS)
# Purpose: DHCP DNS #2 — survives Mac mini reboots. ...
# Deploy on Synology from /volume1/docker/adguard-nas/
#   sudo /usr/local/bin/docker-compose -f /volume1/docker/adguard-nas/compose.yaml up -d
$ ls -1 foss-setup/configs/nas/ | head -8
audiobookshelf
bazarr
beszel
bitmagnet
calibre-web-automated
diun
immich
jellyfin
(no adguard-nas entry under configs/nas/)
```

</details>

### SL44. Dead rootless-docker experiment artifacts in seedbox home (dockerd stopped 2026-07-08, never restarted) plus an old syncthing binary dir

**Host:** seedbox · **Component:** ~/docker, ~/.docker, ~/.dockerd-rootless.log, ~/apps/syncthing/syncthing.old · **Auditor:** repo:junk-deadpaths · **Work item:** `fix-69`

Seedbox home carries a rootless-docker experiment that ended 2026-07-08: ~/.dockerd-rootless.log's last lines are a graceful shutdown at 2026-07-08T03:10, no dockerd process runs today, yet ~/docker, ~/.docker and the 59KB log remain. Also ~/apps/syncthing/syncthing.old (superseded binary dir) sits beside the live binary. The rest of the home is tidy and in active use: syncthing itself IS running (2 procs), and ~/scripts (deluge-reaper.py, deluge-preimport-stuck.py) + ~/logs are live fix-25 tooling. Shared host, light touch — listed only, nothing removed per read-only mandate.

<details><summary>Evidence</summary>

```
$ ssh seedbox 'tail -2 ~/.dockerd-rootless.log'
time="2026-07-08T03:10:16..." level=info msg="stopping healthcheck following graceful shutdown" module=libcontainerd
time="2026-07-08T03:10:16..." level=info msg="stopping event stream following graceful shutdown" error="context canceled" module=libcontainerd namespace=plugins.moby
$ ssh seedbox 'pgrep -af dockerd' -> only the probe's own ssh wrapper lines, no dockerd
$ ssh seedbox 'ls -la ~ | grep -iE "docker"'
drwx------  3 btabaska slices 4096 Jun 27 02:46 .docker
drwxr-xr-x  3 btabaska hd34   4096 Jun 27 02:50 docker
-rw-r--r--  1 btabaska hd34  59405 Jul  8 03:10 .dockerd-rootless.log
$ ssh seedbox 'ls ~/apps/syncthing; pgrep -a syncthing | head -2'
syncthing
syncthing.old
2458105 /home/hd34/btabaska/apps/syncthing/syncthing --home /home/hd34/btabaska/.config/syncthing
```

</details>

### SL45. ntfy message cache retains only ~12h — alert history for any incident older than half a day is unreconstructable

**Host:** mini · **Component:** ntfy cache retention · **Auditor:** arch:topology · **Work item:** `fix-63`

While reconstructing the 07-31 rig outage, the ntfy cache.db oldest message was 2026-08-02T01:45 at a 13:45 query time (~12h retention, the ntfy default). All pages sent during 07-31/08-01 — including the fast-tier incident page and the Healthchecks DOWN page for verification-mini — were already purged; I had to fall back to journald on mini to prove alerts fired. For a fleet whose standing mandate is evidence-based verification, a longer cache-duration (or shipping ntfy publishes to a log) would make post-incident review possible. NOT changed per read-only mandate.

<details><summary>Evidence</summary>

```
ssh mini sudo python3 (sqlite ro) /opt/stacks/ntfy/cache/cache.db 'select min(time) ...' via ordered dump:
msgs since 07-31 00:00 EDT: 78
first row: 2026-08-02T01:45:04 homelab-alerts | NAS services down | ...
(query run 2026-08-02 ~13:45 EDT — nothing cached older than ~12h; 07-31/08-01 outage pages absent)
```

</details>

### SL46. OWUI knowledge API renders populated collections as empty (files:null) and wiki-rag-sync never re-verifies attachment — a data-loss illusion and a real re-attach blind spot

**Host:** rig · **Component:** open-webui knowledge API / wiki-rag-sync.py · **Auditor:** gap:wiki-rag-conflict · **Work item:** `fix-62`

Reconciled contradiction: retrieval against homelab-wiki works (3 relevant chunks live, 325 docs tracked) yet /api/v1/knowledge list+detail return files:null / data:{} with updated_at frozen at 2026-07-16 — one sweep lane misread this as total RAG data loss. Two durable defects remain: (a) any operator or future auditor querying the documented API sees an empty collection (observability trap); (b) wiki-rag-sync.py skips files whose sha256 matches its local state manifest and never verifies the collection attachment, so a REAL detachment (e.g. an OWUI upgrade/reset) would be a permanent silent no-op — the producer check mini-wiki-rag-fresh would stay green forever. A retrieval-level probe should back the check.

<details><summary>Evidence</summary>

```
OK=$(vault ai_stack.openwebui_rag_sync_api_key)
curl -s https://ai.tabaska.us/api/v1/knowledge/ -H "Authorization: Bearer $OK"  # -> files:null, data:{}, updated_at 2026-07-16
curl -s -X POST https://ai.tabaska.us/api/v1/retrieval/query/collection -H "Authorization: Bearer $OK" -d '{"collection_names":["<homelab-wiki id ce2a3840>"],"query":"How is LiteLLM configured?","k":3}'  # -> 3 relevant wiki chunks returned
/opt/verification/bin/wiki-rag-sync.py state: /var/lib/verification/wiki-rag-state.json — 325 tracked, last run 05:15 EDT exit 0, '+0 ~0 -0'
```

</details>


---

## INFO (193)

### SI1. Verified healthy: zero btrfs error counters on all 3 volumes, data arrays clean, no disk events since Jul 2

**Host:** nas · **Component:** storage (btrfs volumes 1-3, md RAID, disk.log) · **Auditor:** host:nas

btrfs device stats for /volume1, /volume2, /volume3 show 0 write/read/flush/corruption/generation errors on all three cachedev devices — no failure-pattern-#1 (RO-remount cascade) precursors. /proc/mdstat: data arrays md2/md3/md4 all active raid1 [1/1] [U] (single-disk basic volumes by design); md1 (swap) shows [4/3] [UUU_] which is the expected shape for 3 drives in a 4-bay DS920+, not degradation. /var/log/disk.log's newest entries are the Jul 2 sata3 (ST18000NM002J) hot-add — no disk errors in a month.

### SI2. Verified healthy: seedbox rclone mount alive, rw, and mount propagation still shared (rshared intact for the shelfmark leg)

**Host:** nas · **Component:** /volume1/mounts/seedbox-files (rclone fuse) · **Auditor:** host:nas

The fuse.rclone mount of seedbox:/home/hd34/btabaska/files at /volume1/mounts/seedbox-files lists content and stats files normally. /proc/self/mountinfo shows propagation flag shared:2 — the NAS has not rebooted (uptime 30d) so the reboot-resets-to-private hazard has not triggered, and the guard task 15.task 'Shelfmark seedbox mount rshared (MAM path persist)' plus 3.task 'Mount watchdog' both exist in the scheduler. findmnt is not present on DSM — used mountinfo instead (note for future check authors).

### SI3. Verified healthy: 31/31 NAS containers Up and exactly matching both coverage manifests; immich_machine_learning Up (healthy) as day fallback

**Host:** nas · **Component:** docker fleet / coverage manifest · **Auditor:** host:nas

docker ps -a shows 31 containers, all Up (uptimes 5 days - 3 weeks), zero Exited/Restarting, healthchecked ones all (healthy). The set matches mini:/opt/verification/coverage/nas.containers AND the repo copy foss-setup/verification/coverage/nas.containers name-for-name (31/31, no orphans, no uncovered) — the 100% monitoring-coverage tripwire holds on NAS. immich_machine_learning is Up 8 days (healthy), confirming the NAS iGPU fallback is in place during the rig's ML day-window (glue-14 known-normal).

### SI4. Host vitals sane: uptime 30d21h, 11.9GB mem available, load ~4 but IO-dominated (busy media host, not CPU-starved)

**Host:** nas · **Component:** host vitals · **Auditor:** host:nas

Uptime 30 days 21h (last boot ~Jul 2, matching the disk.log sata3 install). Memory: 19.8GB total, 11.9GB available; swap 5.9GB used of 13.9GB — DSM's habitual swapping of idle pages, with ample available RAM, no pressure signals in logs. Load average 3.99/4.54/4.21 on the 4-core J4125 decomposes to IO 3.14/3.93/3.63 vs CPU 0.85/0.60/0.56 — the box is IO-busy (normal for the 31-container media host) but CPU-idle. Nothing here explains today's nas-immich-backup-freshness and bitmagnet-torznab TIMEOUTs by itself, though sustained IO load ~4 could slow 60s-budget checks; noting for whichever lane owns those.

### SI5. Seerr request layer verified healthy — no phantom PROCESSING requests, both long-running requests explainable

**Host:** mini · **Component:** seerr (:5055) · **Auditor:** svc:arr-stack

22 total requests: 0 pending, 0 failed, 2 processing, 20 completed. The two processing requests are 28d and 32d old but are NOT taxonomy-#5 phantoms: cross-checked against Sonarr, req#7 = Phineas and Ferb (259/261 episode files, continuing) and req#15 = Smoking Behind the Supermarket with You (4/4 files, currently airing — waiting on future episodes). Container Up 3 weeks (healthy); API key self-sourced from /opt/stacks/seerr/config/settings.json per recipe.

### SI6. Musicseerr verified healthy at service level — Lidarr sync succeeded 2026-08-01, AudioDB sweep fresh

**Host:** mini · **Component:** musicseerr (:8688) · **Auditor:** svc:arr-stack

Container Up 2 weeks (healthy), UI 200, API correctly 401s unauthenticated probes. Config (read on disk, secrets redacted) shows lidarr_settings.last_sync_success=True at 2026-08-01T19:17:25Z and audiodb_sweep_last_completed 2026-08-01T19:32:55Z — scheduled work is executing. One caveat feeds the NAS SQLite finding: its Lidarr history poll got an HTTP 500 today at 13:42 EDT (Lidarr database-is-locked at that exact second). Note config/library.db is a 0-byte root-owned file since Jul 17 — apparently unused, no functional symptom observed.

### SI7. Whisparr and Bookshelf service-level green: empty queues, clean health (beyond shared bitmagnet/DB-lock findings), root folders accessible

**Host:** nas · **Component:** whisparr (:6969) + bookshelf (:8790) · **Auditor:** svc:arr-stack

Whisparr: /api/v3/health returns no items, queue totalRecords=0. Bookshelf: queue totalRecords=0, root folder /readarr-library accessible with 10260 GiB free, only health item is the bitmagnet warning filed separately; one single-shot error 'TrackedDownloadService ... Author with ID 0 does not exist' on 2026-07-31 (not recurring). Both apps' database-is-locked task errors are covered by the dedicated SQLite finding. All four v3-arr root folders verified accessible this session: /tv 8558 GiB free, /movies 6152 GiB, /music 10260 GiB, /readarr-library 10260 GiB.

### SI8. Prowlarr update available (v2.5.2.5491) plus intermittent external-indexer feed errors — within known-normal bounds `known-issue`

**Host:** nas · **Component:** prowlarr (:9696) · **Auditor:** svc:arr-stack

Prowlarr health shows a single UpdateCheck warning 'New update is available: v2.5.2.5491' — consistent with the known-normal weekly image-manifest pin lag, noted for the next pin cycle. Error log also shows low-rate external feed errors (iptorrents 2x, znth.cx 2x over ~24h) which fall under the deliberate indexer-availability probe exclusion; only the bitmagnet feed failure (filed separately) is systematic.

### SI9. Immich verified green end to end: v3.0.3 matched across server and both ML containers, 35,941 assets, queues idle, day-window ML pause confirmed deliberate

**Host:** nas · **Component:** immich · **Auditor:** svc:nas-apps

Server /api/server/version = 3.0.3; NAS immich_machine_learning is v3.0.3-openvino (Up 8 days healthy); rig ML is v3.0.3-cuda, Exited (143) 7h ago — normal day-window stop (immich-ml-window off at 07:00 EDT). Statistics: 34,601 photos + 1,340 videos, 416.8 GB. /api/jobs shows all 19 queues empty; faceDetection/smartSearch/ocr are paused, which the repo script foss-setup/configs/host/rig/immich-ml/immich-ml-window.sh confirms is the deliberate daytime state (resumed at 01:00 EDT). Watch item: newest upload createdAt 2026-07-29 (4 days) — within the 7-day freshness window and nas-immich-mobile-paired passed today, but worth a glance if it ages further.

### SI10. Plex serving verified green: LAN + WAN identity match the expected machineIdentifier, ingest fresh today (Movie added 14:10, TV 03:46)

**Host:** nas · **Component:** plex · **Auditor:** svc:nas-apps

LAN /identity and WAN /identity (probed from the seedbox vantage, reproducing edge-plex-remote-identity which passed today) both return machineIdentifier 70ffcfbb5dc9389e315070cf3a8af99c5fb340b4. Four sections present (Movies, TV Shows, Music, YouTube). Recently-added is fresh on 2026-08-02: TV at 03:46, Movie at 14:10 — throughput is live (taxonomy #13 clear). Minor observation: /library/sections/N/all?X-Plex-Container-Size=0 count queries ran >60s from the Mac and were abandoned; use recentlyAdded-style bounded queries for probes.

### SI11. Jellyfin verified green: 10.11.11 serving, 580 movies / 143 series / 9,314 episodes / 3,461 songs

**Host:** nas · **Component:** jellyfin · **Auditor:** svc:nas-apps

/System/Info/Public answers with Version 10.11.11 (container lscr.io/linuxserver/jellyfin:10.11.11 Up 10 days) and authenticated /Items/Counts (vault jellyfin.verify_api_key) returns full library counts. Today's nas-jellyfin-serves check also passed including an actual ranged stream probe (stream=206), so the consumer path is exercised, not just liveness.

### SI12. Komga verified green including a real page-stream: 2 libraries OK, 3 series / 14 books, newest content 2026-07-27, page 1 streams as image/png

**Host:** nas · **Component:** komga · **Auditor:** svc:nas-apps

Komga 1.25.0 (Up 9 days): both libraries (Comics /data/Comics, Manga /manga) report available; 3 series (Homelab Sample Comic, Yotsuba&! via Suwayomi, Watchmen 12 books) totaling 14 books; newest books created 2026-07-27 (Watchmen 10-12). Reproduced the consumer probe live: GET /api/v1/books/0R33S9AMEF14Y/pages/1 returned 200, image/png, 4,544 bytes. Today's komga-libraries-consumer and suwayomi-feeds-komga checks both passed (SUWAYOMI_OK suwayomi=v2.3.2243 mount=rw). Small library is content volume, not a fault.

### SI13. Audiobookshelf verified green: v2.35.1, both libraries answer with items (1 audiobook, 8 podcasts), newest additions 2026-07-23

**Host:** nas · **Component:** audiobookshelf · **Auditor:** svc:nas-apps

ABS 2.35.1 (Up 9 days) authenticated API (vault audiobookshelf.api_key): Audiobooks library total=1 (newest 'Child's New Story Book' added 2026-07-23), Podcasts total=8 (newest 'Kit & Krysta' added 2026-07-23). Today's audiobookshelf-libraries-consumer check passed (ABS_OK books=1 podcasts=8). Neutral observation: the audiobook library holds a single title — the read-19 iPod pipeline has little to sync; not a fault, just noting the content level, and no new items in 10 days.

### SI14. Container inventory verified in sync: live fleet == deployed manifest == repo manifest

**Host:** mini · **Component:** coverage manifest /opt/verification/coverage/mini.containers · **Auditor:** host:mini

Live docker ps (excluding -run- ephemera) diffs clean against both the deployed manifest on mini and the repo copy at /Users/brandontabaska/GitHub/Home/foss-setup/verification/coverage/mini.containers. The 100%-coverage tripwire mandate is currently upheld on mini; 46 containers all Up.

### SI15. Nightly restic backup to B2 verified green (though its failure notifier is the broken one)

**Host:** mini · **Component:** restic-backup.service · **Auditor:** host:mini

Last two nightly runs (Aug 01 01:34, Aug 02 01:41) completed with 'no errors were found'; timer scheduled next for Mon 01:31. Backing set covers /opt/stacks, /etc, and key dotfiles. Green today, but this is the unit whose OnFailure alert path is dead per the sec-12 notifier finding — a future failure would be silent until the Healthchecks dead-man catches it.

### SI16. Host resources healthy: disk 23%, inodes 7%, load 0.79, no journal retry-storms

**Host:** mini · **Component:** host resources · **Auditor:** host:mini

Root LV 86G/402G used (300G free), inodes 7%, load ~0.79 on a 24-day uptime. Docker: 26.29GB images (8.17GB reclaimable), 2.29GB build cache fully reclaimable — mild prune candidate, not a problem. 7-day p-err flood scan max uniq-count is 10 (the lidarr reconcile unit) — no taxonomy-#7 retry storms; journal is otherwise clean at err level.

### SI17. One-off unit failures in last 48h all explained and self-recovered (rig outage collateral + one DHCP blip)

**Host:** mini · **Component:** net-selfheal / wiki-rag-sync / verification-fast · **Auditor:** host:mini

Three transient failures triaged: (1) net-selfheal detected UNHEALTHY enp3s0f0 at Aug 02 00:41:14, its first renew attempt exited 1, the 00:42 run renewed and recovered — the self-healer did its job during a real ~1-minute network blip. (2) wiki-rag-sync failed Aug 01 05:10 with HTTP 502 (Open WebUI upstream on the rig, which was powered off Jul 31 11:07 - Aug 01 10:25); the Aug 02 05:15 run finished clean. (3) verification-fast 'Failed to start' Jul 31 19:30 + Aug 01 03:40 fall inside the same rig-off window with crit checks rig-suspend-masked/rig-root-fs-writable failing — checks-failed exit path, not a runner fault (known-normal class). No action needed on mini; the rig 23h power-off itself belongs to the rig lane.

### SI18. llama-server SIGSEGV storm (8 coredumps in 3 min) on 07-29 preceded that day's reboot — consistent with known day-window VRAM contention

**Host:** rig · **Component:** llama-swap / llama-server · **Auditor:** host:rig

coredumpctl shows 8 SIGSEGV coredumps of /app/llama-server between 11:18:08 and 11:21:41 on Wed 07-29 (daytime), followed by an orca-ide SEGV at 12:21 and a clean operator reboot at 12:57. This matches the documented known-normal 'llama-swap exited prematurely during day-window VRAM contention' (glue-14 era), but the density (8 crashes/3min) and the operator reboot it apparently provoked are worth noting as the cost of that contention. llama-swap is currently Up 27 hours (healthy). No new crashes since the 08-01 power-on.

### SI19. Verified green: Bedrock UDP tunnel probe healthy every 10 min today; single failure was 08-01 boot catch-up while playit was still starting

**Host:** rig · **Component:** playit-udp-guard (fix-34 M30) · **Auditor:** host:rig

playit-udp-guard.timer fires every ~10 min and every run today reports 'tunnel healthy: bedrock.tabaska.us:1111 answered through playit' (latest 13:04:17). The one failure in the 24h error journal (08-01 14:26:14 'Failed to start') was the post-outage boot catch-up racing playit's own startup and never recurred. The fix-34 M30 self-heal loop is working end-to-end through the public tunnel.

### SI20. Verified green: restic B2 backup (no errors, 25/25 snapshots), nas-music-mirror, and abs-ipod-stage all ran clean this morning

**Host:** rig · **Component:** backups + scheduled jobs · **Auditor:** host:rig

restic-backup to Backblaze B2 completed 01:36 today with 'no errors were found' after checking 25/25 snapshots. nas-music-mirror finished 05:04. abs-ipod-stage staged 1 audiobook + 14 podcast episodes at 05:31 (the staging leg of read-19 — device-write leg has a separate finding). All 19 timers on the host show sane NEXT/LAST values; fstrim and export-manifests are weekly and on schedule. No dead or n/a timers.

### SI21. Verified green: 16-container fleet all Up since power-on, no failed system units, disk 27%, GPU day-normal, no BTRFS/NVMe errors this boot

**Host:** rig · **Component:** docker fleet + host vitals · **Auditor:** host:rig

All 16 containers Up ~27h (since the 08-01 power-on) with health flags where defined (suwayomi, llama-swap, open-webui, litellm-db, lumiverse, palworld all healthy); the only exits/restarts are explained elsewhere (lumiverse rc=1 shim panic, palworld rc=1 SEGV, immich_machine_learning Exited 143 = day-window known-normal). systemctl --failed: 0 system units. Root filesystem 27% (490G/1.9T). GPU 1014MiB/24564MiB, 43C, 0% util — day-normal. Current boot has zero BTRFS/NVMe errors; the boot-time 'corrupt 1' lifetime counter on nvme1n1p2 is historical residue of the fix-20 incident, not new corruption. pcie-aer-monitor green every 20 min (corr=0 fatal=0), and ai-stack-watchdog is silent-when-healthy by design (dead-man ping to Healthchecks 'ai-stack-rig', which reports up), firing every 10 min.

### SI22. Two-tailscaled mystery resolved: single daemon (up 3d15h); the second PID is a per-session 'be-child ssh' handler for our own inbound Tailscale-SSH connection

**Host:** seedbox · **Component:** tailscaled · **Auditor:** host:seedbox

Preflight flagged two tailscaled processes (one etime 00:00). Reproduced live 2026-08-02: the only persistent daemon is PID 2474559 (--tun=userspace-networking, up 3-15:26, parent systemd --user 2474177). The transient PID is 'tailscaled be-child ssh --remote-ip=100.81.199.6 ... --cmd=<our probe command>' with PPID 2474559 — Tailscale-SSH spawns one per inbound session, so every audit probe creates one. Not a duplicate daemon. tailscale status shows healthy direct connections to brandons-macbook-air, macmini, and nas. No action needed.

### SI23. Load 87.4 (1.37/core on 64 cores) — above the documented 40-57 shared-host band, but our processes total well under one core

**Host:** seedbox · **Component:** shared-host-load · **Auditor:** host:seedbox

Observed 2026-08-02 19:07 UTC: load average 87.41/78.88/72.29 on a 64-core host up 55 days with 29 users. Our footprint: deluged 35.1% of one core (RSS 12.2GB), slskd 8.5%, syncthing 0.5%, tailscaled 0.5% — under half of a single core combined, so the elevation is other tenants' workload, per the lane rule this is a neutral observation. The band drift (40-57 documented, ~72-87 today) is worth noting in the fleet-sweep reference doc next time it is edited. deluged RSS of 12.2GB with 536 torrents is large-but-plausible for libtorrent caches; worth watching on future sweeps.

### SI24. slskd verified end-to-end: process up 3d15h, web UI serves app-specific body locally and via tailnet 100.119.134.94:5030

**Host:** seedbox · **Component:** slskd · **Auditor:** host:seedbox

Verified 2026-08-02. slskd native binary (PID 2474555, up 3-15:26) answers HTTP 200 on 127.0.0.1:5030 on-host, and from the operator Mac via the tailnet IP it returns the actual slskd SPA (<title>slskd</title> plus hashed asset bundle), confirming the userspace-tailscaled inbound proxy path that soularr/consumers depend on. The mini-side soularr crashloop signal (soularr-not-crashlooping fatal_errors=2, nas-soularr-failed-imports-fresh) is therefore not a seedbox-side slskd availability problem.

### SI25. Deluge daemon verified healthy at the host level: up 3d15h, 536 torrents in state, RPC :3254 reachable from the Mac via tailnet, deluge-web running, zero ERROR-level log lines

**Host:** seedbox · **Component:** deluged · **Auditor:** host:seedbox

Verified 2026-08-02. deluged (PID 2458058) and deluge-web (PID 2458162) both up 3-15:28; 536 .torrent files in ~/.config/deluge/state/; the arr consumer path (daemon bound 127.0.0.1:3254, proxied inbound by userspace tailscaled) accepts TCP from the operator Mac at 100.119.134.94:3254; the 400KB log window has zero ERROR-level lines. Torrent-level state (the 17 PREIMPORT_STUCK items from deluge-preimport-stuck / fix-25 regression) is owned by the flow:movies-tv lane — nothing at the daemon/host layer explains a stall.

### SI26. Syncthing process itself is healthy (monitor+worker pair up 3d15h, /rest/noauth/health OK, GUI 200) — the problem is what it is (not) doing, filed separately

**Host:** seedbox · **Component:** syncthing-process · **Auditor:** host:seedbox

Verified 2026-08-02: the standard syncthing parent/child pair (PIDs 2458105/2458824, up 3-15:28) is running, /rest/noauth/health on 127.0.0.1:12104 returns status OK, and unauthenticated REST is correctly refused with 403. Process-level health is green; the zero-folder/zero-peer purposelessness and public plaintext exposure are covered in the separate high finding.

### SI27. Verified green: HA 2026.7.2 RUNNING, 140 entities, availability drift exactly at accepted baseline, all enabled ha-* checks pass

**Host:** ha · **Component:** entity availability / core API / daily ha-* checks · **Auditor:** host:ha

Live probes 2026-08-02 ~13:00-13:15 EDT: /api/config returns version 2026.7.2 state RUNNING; /api/states returns 140 entities. Unavailable/unknown counts match the accepted baseline EXACTLY with zero new drift: 11 sensor.btiphone_* unavailable (baseline <=11), 7 light.* unavailable (all hue wall-switched names, baseline ~8), 21 scenes + 4 buttons + 1 tts + 1 notify 'unknown' (stateless-until-used, normal). 73 light entities total, hue integration actively delivering state changes today. Today's 10:23 daily run: ha-http, ha-proxy-e2e, ha-api-auth, ha-hue-lights (73), ha-lights-available, ha-updates-pending, ha-availability-drift, ha-iphone-presence, ha-assist-rig-llm-reachable all pass; ha-hacs-loaded skipped (deliberately disabled, open task ha-04). Minor note: 2026-08-01 22:20 log warnings show a scene/automation referencing 3 of the wall-switched bulbs (basement_hue_white_lamp_5, kitchen_kitchen_overhead_2, upstairs_bathroom_vanity_1) which no-oped — a known consequence of the accepted wall-switch baseline.

### SI28. Verified green: HA off-eMMC backup on NAS is fresh (<48h) per today's crit-severity dead-man check

**Host:** ha · **Component:** ha-backup-offsite-fresh (ha-11 dead-man) · **Auditor:** host:ha

The crit-severity check ha-backup-offsite-fresh (task ha-11, defined in foss-setup/verification/checks.d/ha.yaml) passed in today's 10:23 EDT daily run with 'backup=fresh' — it verifies via NAS sudo find that at least one *.tar in /volume1/backups is younger than 2880 minutes (48h). Cited from mini /var/lib/verification/results.json rather than re-running the NAS sudo pipeline, per the sweep's keep-NAS-sudo-light rule; the results file timestamp is 2026-08-02T10:23:08-04:00 so the observation is ~3h old and current.

### SI29. Mini-side music mounts verified healthy — host and container views agree; mount is NOT the cause of the Navidrome grey-out

**Host:** mini · **Component:** nas-music CIFS mounts · **Auditor:** svc:media-aux

Both fstab automounts are live: //192.168.10.4/music on /mnt/nas/music (ro, navidrome's MUSIC_FOLDER per /opt/stacks/navidrome/.env) and /mnt/nas-music-rw (rw, metube ingest). Host ls shows 47 artist dirs; docker exec navidrome ls /music shows the same 47 (including #recycle) — no docker+autofs empty-bind trap, no stale CIFS handle. Evidence handed to the flow:music lane: the Navidrome outage is entirely the root .ndignore (separate critical finding), not the mount.

### SI30. bgutil POT provider verified end to end: server 1.3.1 serving on :4416 and plugin zip in pinchflat is the matching 1.3.1

**Host:** mini · **Component:** bgutil-pot · **Auditor:** svc:media-aux

The known failure mode (plugin zip must version-match server, per bgutil POT quirks) is NOT present: today's 10:23 EDT check bgutil-pot-serving passed with "version":"1.3.1" from :4416/ping (probed from caddy on the shared docker network), and a live read of the plugin zip inside the pinchflat container shows getpot_bgutil.py __version__ 1.3.1. Version pair verified matched this session.

### SI31. MeTube backend verified live: /version returns loaded yt-dlp 2026.07.06.234510 (not just the SPA)

**Host:** mini · **Component:** metube · **Auditor:** svc:media-aux

Live probe this session reproduced the metube-serving check's consumer-end assertion: :8081/version returns {"yt-dlp": "2026.07.06.234510", "version": "2025.11.13"}, proving the aiohttp backend and yt-dlp are loaded rather than only the static SPA. Check metube-serving also passed in today's 10:23 EDT run.

### SI32. Tautulli zero-throughput probe negative: history is fresh (last play 2026-08-01 17:44 EDT), API consumer path works

**Host:** mini · **Component:** tautulli · **Auditor:** svc:media-aux

Tautulli's daily check (mini-tautulli, pass, 303 redirect) is liveness-only, so a taxonomy-#13 probe was run via its API: get_activity returns stream_count 0 (nothing playing at ~13:20 EDT Saturday, plausible) and get_history's newest record is 'Supergirl' started 2026-08-01T17:44:34 — less than 24h old, so Tautulli is actively receiving Plex playback data. API key was read from /opt/stacks/tautulli/config/config.ini into a shell var without printing.

### SI33. Bazarr-to-arr wiring verified healthy: both SignalR feeds LIVE, 283 movies + 163 series synced (check green today)

**Host:** nas · **Component:** bazarr arr-sync · **Auditor:** svc:media-aux

Check bazarr-synced-from-arrs passed in today's 10:23 EDT run with BAZARR_OK movies=283 series=163 sonarr=LIVE radarr=LIVE — the consumer-end sync assertion (library non-empty via Radarr API pull, both SignalR live-connections up) holds. Note this green is explicitly scoped to sync only; the provider layer is dead (separate high finding), so treat this as 'wiring healthy, delivery broken'.

### SI34. Beets ingest verified fresh: nas-beets-ingest-fresh passed today's run (ingest=fresh)

**Host:** nas · **Component:** beets · **Auditor:** svc:media-aux

Check nas-beets-ingest-fresh passed in the 2026-08-02 10:23 EDT daily run with output 'ingest=fresh' — the NAS beets music-ingest path shows recent successful activity. No live re-probe needed for this lane; cited from the runner's results.json per sweep guidance to verify rather than rediscover.

### SI35. LiteLLM virtual-key e2e verified working through the public vhost; 24h logs clean of non-benign Proxy:ERROR

**Host:** rig · **Component:** litellm :4000 (llm.tabaska.us) · **Auditor:** svc:ai-stack

One-shot completion with the verify virtual key (vault ai_stack.litellm_verify_key) on model 'utility' via https://llm.tabaska.us returned a real completion ('Ok') at ~13:05 EDT. docker logs --since 24h litellm filtered for Proxy:ERROR excluding the known-benign 'No api key passed in' noise returned zero lines. Corroborated by today's 10:23 EDT daily run: rig-litellm-vkey-e2e, rig-litellm-consumer-e2e ('PONG'), and rig-ai-e2e all pass.

### SI36. Continue.dev/opencode key path verified: vault opencode key completes on model 'fast' through llm.tabaska.us

**Host:** rig · **Component:** litellm opencode key / remote-coding chain · **Auditor:** svc:ai-stack

The previously-flagged gap (remote-coding chain end) is green: a one-shot completion with vault ai_stack.litellm_opencode_key on model 'fast' (max_tokens 20) via https://llm.tabaska.us returned a real assistant message at ~13:20 EDT. This verifies the key is live and the default remote-coding model resolves and infers.

### SI37. llama-swap healthy: 11 models listed, fast-3b loaded/ready, no 'exited prematurely' in 48h

**Host:** rig · **Component:** llama-swap :9292 · **Auditor:** svc:ai-stack

/v1/models lists 11 models (cydonia-24b, deckard-heretic, dolphin-venice-24b, fast-3b, gemma4-31b-qat, goetia-24b, qwen2.5-coder-7b, qwen3-embed, qwen3.6-27b, qwen3.6-35b-a3b, qwen3.6-35b-a3b-swarm); /running shows fast-3b state=ready (ttl 300). 48h of container logs contain zero 'exited prematurely' events — nothing even needing the day-window explanation. Only noise: two transient 'proxy error: dial tcp [::1]:10004: connect: connection refused' lines (08-01 18:41Z, 08-02 14:40Z) consistent with requests racing model spin-up. Daily checks rig-llama-swap, rig-llama-swap-models, rig-llama-swap-creative all pass.

### SI38. ComfyUI verified through the public vhost: object_info 200 with model stacks present; gpu-arbiter process running

**Host:** rig · **Component:** comfyui :8188 + gpu-arbiter :8189 (comfyui.tabaska.us) · **Auditor:** svc:ai-stack

https://comfyui.tabaska.us/object_info returned HTTP 200 with 1.6MB / 1013 node classes at ~13:10 EDT. Model inventory present: CheckpointLoaderSimple offers NoobAI-XL-v1.1.safetensors; UNETLoader offers 4 z-image models (z_image_turbo_bf16 + cyberrealistic/moody variants) — consistent with the prior multi-stack inventory. gpu-arbiter.py process is running on the rig with docker-proxy bound on :8189. Daily checks rig-comfyui, rig-comfyui-arbiter, rig-gpu-arbiter-unload-hook, rig-ai-gpu-yield (YIELD_OK vram=1014MiB) all pass. No image was generated per sweep rules.

### SI39. mcpo and fleet-mcp healthy; rig-ops-agent-e2e passed in today's daily run

**Host:** rig · **Component:** mcpo :8000 + fleet-mcp :8765 · **Auditor:** svc:ai-stack

Live at ~13:10 EDT: mcpo /docs returns HTTP 200 on rig localhost:8000; fleet-mcp systemd unit is active (GET / returns 404 which is just no root route — the daily check rig-fleet-mcp expects svc=active http=406 and passed today). Citing today's 10:23 EDT run: rig-ops-agent-e2e pass (agent answered a live VRAM question end-to-end) and rig-mcpo-fleet-tools pass (fleet MCP OpenAPI served, version 1.28.1). Note the ops-agent output quoted 23,215/24,564 MiB VRAM at run time — that was the agent's own big-model inference resident; current day-window snapshot is 6611 MiB used.

### SI40. Ollama shim serving expected model set including llama3.2:3b

**Host:** rig · **Component:** ollama compat shim :11434 · **Auditor:** svc:ai-stack

Live /api/tags at ~13:05 EDT lists exactly the designed shim set: llama3.2:3b, tag:fast, nomic-embed-text:latest (ai-01 posture — big models live in llama-swap). Daily checks rig-ollama, rig-ollama-models, rig-ollama-keepalive all pass today.

### SI41. OWUI itself up and API-authenticated (login page 200, admin-key API works) — only the wiki knowledge content is broken (filed separately)

**Host:** rig · **Component:** open-webui :3000 (ai.tabaska.us) · **Auditor:** svc:ai-stack

https://ai.tabaska.us/ returns HTTP 200 and /api/v1/knowledge/ authenticates with the vault admin key (ai_stack.openwebui_rag_sync_api_key), returning valid JSON. Container open-webui Up 27 hours (healthy). Daily checks rig-open-webui, journaling-owui-save-fn-installed, journaling-owui-coach-preset all pass today, so the journaling OWUI functions are intact. The empty homelab-wiki knowledge collection is filed as a separate high finding.

### SI42. rig-llm-scoped-keys-public posture check green today (KEYSCOPE=cydonia,dolphin-venice,goetia)

**Host:** rig · **Component:** litellm scoped public keys · **Auditor:** svc:ai-stack

Cited from the 2026-08-02 10:23 EDT daily run on mini: rig-llm-scoped-keys-public passed with KEYSCOPE=cydonia,dolphin-venice,goetia on both probes, confirming the publicly-exposed LiteLLM keys remain scoped to the creative model set only. Not independently re-probed this session (citation per sweep guidance to verify, not rediscover).

### SI43. Rig AI container fleet all Up ~27h (since the 08-01 10:25 boot), VRAM in normal day-window state

**Host:** rig · **Component:** AI stack containers / GPU day-window · **Auditor:** svc:ai-stack

docker ps at ~13:05 EDT: llama-swap (healthy), gpu-arbiter, comfyui, open-webui (healthy), litellm, litellm-db (healthy), mcpo — all Up 27 hours, matching the 2026-08-01 10:25 EDT boot (the ~23h prior power gap is preflight-flagged host territory, not re-filed here). VRAM 6611/24564 MiB with immich ML off by day as designed (rig-immich-ml-window DAY_OFF_OK pass today). No restart loops in the AI stack.

### SI44. Caddy verified healthy: live config current (repo hash == live hash, newest booklogr vhosts loaded), no proxy-layer errors of its own

**Host:** mini · **Component:** caddy · **Auditor:** svc:infra-mini

Repo mirror Caddyfile md5 (a4fb34af71f38ddb09b3e53ec7a5e47d) exactly matches live /opt/stacks/caddy/caddy/Caddyfile — zero anti-drift gap. The :2019 admin running config (21362 bytes) contains the booklogr/booklogr-api vhosts from read-26 (newest service), confirming the on-disk config was actually loaded; check mini-caddy-live-config-current also passed at 10:23 EDT. All 5xx in 24h trace to upstream apps (suwayomi 500s, rig-unreachable window), none to Caddy itself; no non-access error-level log lines. Container Up 5 days.

### SI45. DNS chain verified working: internal rewrites and external recursion both resolve from a LAN client

**Host:** mini · **Component:** adguardhome + unbound · **Auditor:** svc:infra-mini

Live dig against 192.168.10.2 from the Mac: plex.tabaska.us and home.tabaska.us both return 192.168.10.2 (correct Caddy rewrite), external anthropic.com resolves via Unbound upstream (160.79.104.10). Both containers Up (unbound healthy, 3 weeks). All eight dns-* / container-dns checks passed in the 10:23 EDT sweep (dns-mini-internal/external, dns-mini-unbound-upstream, mini-container-dns-egress, edge-public-dns-no-rfc1918, edge-public-dns-www-nxdomain).

### SI46. Forgejo verified healthy end to end: healthz pass, web+ssh serving, home/homelab and home/docker-stacks fully in sync with their counterparts

**Host:** mini · **Component:** forgejo · **Auditor:** svc:infra-mini

Forgejo healthz reports status pass with cache:ping and database:ping passing (queried 2026-08-02 17:14 UTC); web is published on host :3030 (not :3000) and serves 200 via git.tabaska.us through Caddy; ssh :2222 works (git ls-remote succeeded from the Mac). Repo freshness: home/homelab main is identical on GitHub origin, Forgejo, and local Mac HEAD (7adbd584973f); home/docker-stacks Forgejo HEAD (f12c6fd5c242) exactly matches live mini /opt/stacks HEAD with porcelain clean (0 lines) — the git-stacks-clean tripwire state is genuinely green. The /api/v1/version endpoint requires sign-in (deliberate lockdown), not a fault. The one Forgejo-hosted repo out of sync is local-ai-tooling (filed separately as the ai-03 regression).

### SI47. Homepage verified working: all 62 tiles enumerated, every internal vhost + href-only external tile (Proton x5, UniFi) responds healthy

**Host:** mini · **Component:** homepage · **Auditor:** svc:infra-mini

Pulled /api/services via the Host-header path (source of truth per quirks memory): 62 tiles across 12 groups. Probed all 49 distinct internal tabaska.us hrefs from the Mac through Caddy — every one returned a healthy code (200, or documented-normal 401 for Plex and 30x login redirects for bug/jellyfin/tautulli/music/stash/seerr/mylar/books/wallabag/paperless/dns/sonarr/radarr/lidarr/whisparr/prowlarr/scrutiny/uptime/health, 301 bitmagnet). The href-only external tiles the dead-tile guard misses were also probed: all 5 Proton apps 200, UniFi 192.168.10.1 200. Daily checks homepage-dead-tiles=NONE, homepage-widget-errors=0, homepage-calendar-ics-fetch and homepage-unifi-tile pass corroborate. No dead tiles found.

### SI48. Uptime-Kuma verified: 57 active monitors, zero in non-up state (queried embedded MariaDB read-only); monitor count grew from documented ~47

**Host:** mini · **Component:** uptime-kuma · **Auditor:** svc:infra-mini

Kuma v2 runs with its embedded MariaDB (the legacy kuma.db sqlite is 0 bytes). Queried the DB read-only through the container socket at ~13:25 EDT: 57 active monitors, and the latest-heartbeat-per-monitor join returned zero rows with status != up — nothing down or pending. Container Up 5 days (healthy), login redirect healthy at uptime.tabaska.us. The Homepage tile uses siteMonitor only (no status-page widget/slug configured). error.log's last entry is Jul 28 (PROTOCOL_CONNECTION_LOST during that day's restart — stale, matches container age). Note the fleet doc says ~47 monitors; actual is 57 — doc drift only.

### SI49. Dockge, Beszel hub+agents, and the ntfy service itself all verified healthy

**Host:** mini · **Component:** dockge + beszel + ntfy (service side) · **Auditor:** svc:infra-mini

All containers Up (dockge healthy 3 weeks, beszel/beszel-agent 3 weeks, ntfy healthy 3 weeks); vhosts dockge/status/ntfy all 200 through Caddy. Beszel hub and agent logs show zero error/fail lines in 24h, and the 10:23 EDT check alert-beszel-none-down passed with down=0 (agent connectivity from all fleet hosts intact). ntfy checks alert-ntfy-healthy ({"healthy":true}), alert-ntfy-upstream-relay (ntfy.sh), and ntfy-anon-publish-denied (403) all pass — the broken piece is only mini's OnFailure publisher wrapper (filed separately under sec-12). No publish was performed per read-only mandate.

### SI50. Alert chain verified end-to-end by a real incident: verification-mini dead-man down/up both paged successfully via ntfy

**Host:** fleet · **Component:** alerting chain (Healthchecks dead-man -> ntfy -> operator) · **Auditor:** svc:monitoring-stack

The Aug 1 missed daily sweep gave a live end-to-end test of the alerting plane and it passed: verification-mini flipped down 2026-08-02T02:26:49Z (22:26 EDT Aug 1) and Healthchecks' Notification log shows the ntfy page sent with error='' to channel topic 'healthchecks' (http://ntfy:80, priority 4); the recovery page at 14:25:03Z also delivered. restic-backup-rig down/up pages around the rig outage (Aug 1 11:40Z down, 18:27Z up) likewise delivered. ntfy server is actively publishing (messages_published counter 1973 -> 1975 during a 25-min observation window; verification-topic tier summaries flowing all night including the 10:23 daily). alert-healthchecks-none-down's crit this morning was the check working exactly as designed — naming the down dead-man.

### SI51. All 16 Healthchecks up; export-manifests-rig is NOT overdue — its 152h-old last ping is normal for a weekly Monday-04:00 cron check

**Host:** mini · **Component:** Healthchecks (health.tabaska.us) · **Auditor:** svc:monitoring-stack

Live API pull at ~13:10 EDT: 16/16 checks status=up. export-manifests-rig is a cron-schedule check ('0 4 * * 1', grace 86400s) whose last ping Mon Jul 27 08:09:38Z (04:09 EDT) matches its Monday cadence; next expected Mon Aug 3 04:00 EDT + 1d grace, so the preflight's 152h-age concern is resolved as in-period. export-manifests-mini (timeout 7d) last pinged Jul 28, also in period. verification-fast-mini and verification-quick-mini pinged within the hour; verification-mini recovered at 10:25 EDT today (see the Aug 1 incident finding).

### SI52. Uptime Kuma verified: 57 active monitors, 0 down, 0 paused

**Host:** mini · **Component:** Uptime Kuma · **Auditor:** svc:monitoring-stack

Live read-only MariaDB query at ~13:17 EDT: 57 active monitors, latest heartbeat status=0 (down) on none, and zero paused monitors — nothing is silenced-by-pause hiding an outage. Corroborates the 10:23 daily alert-kuma-none-down pass (down=0, task sec-03).

### SI53. Beszel verified: hub authenticating, mini/nas/rig agents all up with records updated within the last minute

**Host:** fleet · **Component:** Beszel hub + agents · **Auditor:** svc:monitoring-stack

Authenticated to the hub (creds at vault beszel.admin_user / beszel.admin_password) at ~13:18 EDT: all three systems report status=up with updated timestamps 17:17-17:18Z, i.e. seconds old. Corroborates the 10:23 daily alert-beszel-none-down pass (down=0; the 10:23 ntfy daily summary also showed alert-beszel-* in its recovered list).

### SI54. Diun verified: both instances completed today's scan clean (mini 43 images, NAS 30 images, failed=0)

**Host:** fleet · **Component:** Diun (mini + NAS) · **Auditor:** svc:monitoring-stack

mini Diun cron fired today 06:00:29 EDT and completed 06:00:31 with added=0 failed=0 unchanged=43; NAS Diun fired 06:30:12 and completed 06:31:02 with failed=0 unchanged=30. Only blemish in the window: Jul 31 mini scan had one transient failure fetching codeberg.org/forgejo/forgejo:15.0.1 (registry returned 503) which self-resolved on the Aug 1 run — no action needed. Both containers also pass their daily alert-diun-*-up checks.

### SI55. Scrutiny verified: 7 disks all device_status=0 with collector data fresh from today 06:00-06:01 across NAS + mini/rig spokes

**Host:** nas · **Component:** Scrutiny hub (:8080) + collector spokes · **Auditor:** svc:monitoring-stack

Direct /api/summary probe from the Mac at ~13:17 EDT: 7 devices (sata1-3 on NAS, sda + nvme0/1/2 from the mini/rig spokes) all device_status=0, temps 32-49C, every collector_date stamped today between 06:00:05 and 06:01:51 — hub AND all three spokes reporting on schedule. Independently corroborates the 10:23 daily sys-disk-smart-health pass ('smart_ok drives=7', task glue-10 territory).

### SI56. All three verification timers firing on cadence; preflight's 'NEXT=Mon 10:15' worry is void — today is Sunday, Monday 10:15 is the correct next daily elapse

**Host:** mini · **Component:** verification-fast/quick/daily timer triple · **Auditor:** svc:monitoring-stack

Live list-timers at 13:15 EDT: verification-fast LAST 13:05 / NEXT 13:15 (10-min cadence, and the 13:15 run's results-tier-fast.json exists), verification-quick LAST 12:40 / NEXT 13:41, verification (daily) LAST today 10:15:09 / NEXT Mon Aug 3 10:15:47. The daily OnCalendar is *-*-* 07:15 America/Los_Angeles = 10:15 EDT daily, so with today's run complete, tomorrow(Monday) is the correct next elapse — nothing is skipping Sunday. Today's daily also completed normally (Finished 10:25:01, healthchecks ping received 14:25:01Z).

### SI57. Miniflux verified fully green end to end: 49 feeds, zero parsing errors, newest entry published today

**Host:** mini · **Component:** miniflux (:8082) · **Auditor:** svc:docs-life

API probe 2026-08-02: 49 feeds, 0 with parsing_error_count>0, 0 disabled; 1422 entries total, newest published 2026-08-02T15:20:00Z (SMBC) — real throughput within the hour, no taxonomy-#13 staleness. Corroborates today's 10:23 passing checks mini-miniflux (200), mini-miniflux-feeds-fresh, mini-miniflux-articles-flowing, mini-miniflux-no-bootstrap-admin.

### SI58. Paperless verified working: API auth good, 39 documents, newest added 2026-07-22

**Host:** mini · **Component:** paperless-ngx (:8000) · **Auditor:** svc:docs-life

Token auth (vault homepage_widgets.paperless_token) against the documents API works; 39 documents, newest added 2026-07-22T19:05 EDT (11 days ago). No new intake since then, which is consistent with personal scan cadence rather than a stuck consumption pipeline; container Up 3 weeks (healthy) with db/redis/gotenberg/tika all healthy. Check mini-paperless passed at 10:23 (302 login redirect = healthy).

### SI59. Wallabag verified working: 21 entries, newest saved 2026-07-28

**Host:** mini · **Component:** wallabag (:8085) · **Auditor:** svc:docs-life

Read-only DB query inside wallabag_db (creds via container env, never printed): 21 entries in wallabag_entry, newest created/updated 2026-07-28 18:10 — articles were being saved as recently as 5 days ago, so the KOReader/read-it-later path has real throughput. Container Up 3 weeks (healthy, healthcheck hits /api/info); check mini-wallabag passed at 10:23 (302 = healthy login redirect).

### SI60. Mealie healthy but near-empty: exactly 1 recipe three weeks post-deploy

**Host:** mini · **Component:** mealie (:9000) · **Auditor:** svc:docs-life

API auth (vault homepage_widgets.mealie_token) works and check mini-mealie passed (200) at 10:23, but the library holds exactly one recipe ('Oyakodon'), created 2026-07-22 — deploy week — and nothing since. Confirmed with perPage=50 (1 item returned, total=1). Not a fault (taxonomy-#13 checked: service reads/writes fine), but the deployed service is delivering near-zero value; worth an adoption nudge or a decision, not a fix.

### SI61. BookLogr serving path verified: both Caddy vhosts wired as designed, consumer check green (v1.11.1)

**Host:** mini · **Component:** booklogr (SPA :80 + API :5000 via two Caddy vhosts) · **Auditor:** svc:docs-life

Today's 10:23 check booklogr-serves-consumer passed: web=200 with SPA bundle index-CxiitvYw.js, api_version=1.11.1, CORS header present for the web origin. Live Caddyfile (/opt/stacks/caddy/caddy/Caddyfile lines 162-170) carries the two designed vhosts booklogr.{$DOMAIN} -> booklogr-web:80 and booklogr-api.{$DOMAIN} -> booklogr-api:5000 with local_tls, matching the compose design (BL_API_ENDPOINT baked to https://booklogr-api.tabaska.us/). Both containers Up 4 days. Only defect is the separate open-registration finding.

### SI62. Journaling loop verified green end to end; n8n workflow/webhook tables clean, no stale webhook rows; whisper healthy

**Host:** mini · **Component:** journaling stack (memos :5230, n8n :5678, faster-whisper :8010) · **Auditor:** svc:docs-life

All 11 journaling-* checks passed at 10:23 including journaling-loop-e2e (E2E_OK, posted+reflected test memo) and journaling-whisper-transcribes. Live corroboration: faster-whisper /health returns OK and lists Systran/faster-whisper-small; n8n sqlite (read-only) shows exactly the expected state — journal-analyze active=1, bug-report-intake active=1, journal-webhook-probe active=0, and all 3 webhook_entity rows map to active workflows (the stale-webhook-row hazard from the 2.x CLI-unpublish quirk is NOT present). The e2e cleans up after itself: DB newest persistent memo is 2026-07-27T17:45Z despite today's test post. Memos holds 8 memos total; newest real entry is 6 days old — user cadence, not a fault. Encryption-key hygiene verified both sides: journaling/n8n/config and journaling/.env are gitignored in the live docker-stacks repo, and the Home-repo journaling/.gitignore scopes n8n/* correctly (workflow JSONs tracked, key excluded).

### SI63. Minecraft Java public join path verified end-to-end: real protocol ping from operator Mac through playit edge answers Paper 26.1.2

**Host:** rig · **Component:** AMP MinecraftCross01 / Minecraft Java via playit · **Auditor:** svc:gaming

Spoke the actual Java client handshake+status protocol from the Mac to the public playit edge 69.9.181.17:1105 (handshake hostname minecraft.tabaska.us) — the exact path a friend uses. Server answered with Paper 26.1.2, 0 players, at ~13:10 EDT 2026-08-02. AMP container Up 27h (since the 08-01 boot); latest AMP_Logs file for today has zero error/exception lines in its tail.

### SI64. Minecraft Bedrock public UDP path verified: RakNet pong through playit 69.9.181.17:1111; udp-guard green every 10 min, no register errors in 24h

**Host:** rig · **Component:** playit tunnel + Geyser (Bedrock UDP) · **Auditor:** svc:gaming

RakNet unconnected ping from the Mac through the public playit UDP tunnel returned the Geyser pong ('Powered by AMP', v26.33) — the historically flaky M30 path. On-rig playit-udp-guard.timer is active and every 10-minute run in the last hour logged 'tunnel healthy'; daily checks game-playit-bedrock-udp (PONG) and game-playit-udp-register-errors (REGISTER-OK) both passed at 10:23 EDT. playit container Up 27h.

### SI65. AMP Minecraft backup chain verified healthy: fresh hourly backup, no DoNothing policy, restic snapshots bloat-free

**Host:** rig · **Component:** AMP backup pipeline (fix-34 H10/M29) · **Auditor:** svc:gaming

The 10:23 EDT daily run passed all three fix-34 regression checks at the consumer end: game-amp-backup-fresh BACKUP-OK age=982s (newest zip ~16 min old against an hourly schedule), game-amp-backup-policy POLICY-OK (no instance carries the silently-refusing ReplacePolicy=DoNothing), and restic-bloat-rig HYGIENE-OK/BLOAT-OK across 25 snapshots. The H10 five-day silent-freeze class is demonstrably guarded.

### SI66. Palworld verified at the consumer end: REST info+metrics answer with vault admin cred — 2 players online, 59fps, world day 993

**Host:** rig · **Component:** palworld REST API (:8212) · **Auditor:** svc:gaming

Probed the same REST path the Homepage customapi widget uses, from the Mac to rig :8212 with basic auth (cred at vault palworld.admin_password, never printed). /v1/api/info returned server v1.0.2.101103 'Tabaska Palworld'; /v1/api/metrics showed 2 live players, 59 serverfps, 15 basecamps, uptime 67338s — the server is actively in use right now. Compose confirms REST bound LAN-wide on 8212/tcp, RCON localhost-only, game port 8211/udp public via playit. (See separate medium finding for the 08-01 segfault/restart.)

### SI67. Terraria co-op server verified: world AnalogueCoop loaded with 8 open slots, live REST re-probed this session, 5d uptime

**Host:** mini · **Component:** terraria (TShock, :7777) · **Auditor:** svc:gaming

Live TShock REST status at 13:12 EDT: v1.4.5.6, tshock 6.1.0.0, world AnalogueCoop, 0/8 players, uptime 5d03h. Daily checks terraria-join-handshake (JOINABLE msgType=2 — protocol-level join pipeline answered) and terraria-world-loaded both passed at 10:23. Container Up 5 days. Neutral observation: REST reports serverpassword:false — fine if exposure is LAN/tailnet-only as designed for game-01, worth a glance if it ever gets a public tunnel.

### SI68. RomM verified functional: heartbeat live (4.9.2, RetroAchievements enabled), library consistent at 8364 ROMs

**Host:** mini · **Component:** romm (:8998) · **Auditor:** svc:gaming

Live heartbeat re-probed this session from the mini: version 4.9.2 with RA_API_ENABLED true (the retro-02 tripwire flag). The 10:23 daily run passed romm-serving, romm-retroachievements, and romm-content-ingest with ROMM_CONSISTENT files=8368 roms=8364 — DB record count tracks on-disk files, so the shelf is not silently emptying (zero-throughput class checked).

### SI69. ES-DE library healthy: zero broken symlinks, NAS CIFS-backed tree intact, 8332 ROMs visible with all launch cores

**Host:** rig · **Component:** ES-DE ROM symlink farm (/home/btabaska/ROMs) · **Auditor:** svc:gaming

find -xtype l over the whole /home/btabaska/ROMs tree found 0 broken symlinks (the tree is 9 top-level entries — system-dir symlinks into the NAS mount, so a dropped CIFS mount or deleted target would show here). Daily check rig-esde-romm-library passed at 10:23 with ESDE-ROMM-OK roms=8332 and all six libretro cores present. Consistent with RomM's 8364 (ES-DE sees the 7 core systems subset).

### SI70. Game-save sync mesh green in today's run: 23 files, rig 100% complete, idle

**Host:** fleet · **Component:** game-saves sync mesh · **Auditor:** svc:gaming

Cited from the 10:23 EDT daily sweep (not independently re-probed this session): game-saves-mesh-synced passed with game_saves_mesh=ok files=23 rig_complete=100% state=idle. No drift signal on the save-sync path.

### SI71. Bookshelf verified healthy at the app level: empty queue, valid Hardcover token (352 days left), version matches pinned image

**Host:** nas · **Component:** bookshelf · **Auditor:** svc:reading

Live API probe 2026-08-02 ~13:10 EDT: /api/v1/queue totalRecords=0 (nothing stuck), /api/v1/system/status reports version 0.4.20.129 matching the running image tag ghcr.io/pennydreadful/bookshelf:hardcover-v0.4.20.129, container Up 12 days. Today's checks: hardcover-token-valid pass (HC_TOKEN_OK days_left=352 user=RobitFarmer), bookshelf-foreign-records/grab-history NONE, bookshelf-import-deadends NONE, bookshelf-cwa-copy-drops drops=0. Only health complaint is the Bitmagnet indexer (filed separately). Open task sec-11 (rotate bookshelf API key) still applies but is tracked.

### SI72. rreading-glasses-hc clean: zero 403s / zero error-level lines, no refresh herd; postgres healthy; still on temp local patched image (books-hc-upstream-swap) `known-issue`

**Host:** nas · **Component:** rreading-glasses-hc · **Auditor:** svc:reading

Live log sweep 2026-08-02 ~13:20 EDT of the last 2000 lines: 0 lines with "status":403, 0 with "level":"error"; the 97 initial 'refresh' grep hits were per-minute debug controller-stats lines all showing refreshWaiting=0 (no Hardcover refresh herd, quota healthy). rreading-glasses-db postgres:17.6 Up 12 days (healthy). Container runs local/rreading-glasses:hardcover-batch5-a2939b6 — the temporary local patched image, fully covered by open task books-hc-upstream-swap. Serving check nas-rreading-glasses-hc pass (200) this morning.

### SI73. libreseerr verified healthy: zero gunicorn WORKER TIMEOUTs, no pending/stuck requests (all 30 in terminal states)

**Host:** mini · **Component:** libreseerr · **Auditor:** svc:reading

Live probe 2026-08-02 ~13:12 EDT: container Up 12 days; 0 'WORKER TIMEOUT' occurrences in the last 1000 log lines (taxonomy #16 clear); /opt/stacks/libreseerr/data/requests.json holds 30 requests, all terminal — 18 completed, 12 error, 0 pending/processing/retrying/downloading. The 12 error-status requests are old terminal failures already vetted by this morning's passing libreseerr-request-rot (LIBRESEERR_OK checked=12 legacy_skipped=6); libreseerr-request-stuck (STUCK_REQUESTS=NONE) and libreseerr-request-path-guards also pass.

### SI74. Shelfmark verified live: health 200 + seedbox-files mount propagation shared:2 (MAM→CWA-ingest path intact)

**Host:** nas · **Component:** shelfmark · **Auditor:** svc:reading

Reproduced the shelfmark-mam-path-ready probe live 2026-08-02 ~13:15 EDT: /api/health on 127.0.0.1:8084 returns 200 and the seedbox-files mount shows rshared propagation (shared:2) in /proc/self/mountinfo. Container Up 11 days (healthy). Matches this morning's passing check (SHELFMARK_OK health=200 prop=shared:2, task bmig-06).

### SI75. Mylar3 verified healthy: no errors in recent logs, mylar3-feeds-komga green (13 cbz, 2 Komga comic series)

**Host:** nas · **Component:** mylar3 · **Auditor:** svc:reading

Live 2026-08-02 ~13:05 EDT: container Up 5 days; grep of the last 400 log lines for error/traceback/DDL returned nothing. This morning's consumer-end check mylar3-feeds-komga passes: MYLAR3_OK mylar3=70edba407fff cbz=13 komga_comics_series=2 — the Komga feed path is intact.

### SI76. Suwayomi→Komga feed path verified: persistent fstab-generated CIFS mount rw (not autofs), survived the 08-01 rig reboot

**Host:** rig · **Component:** suwayomi /mnt/nas-manga mount · **Auditor:** svc:reading

Live 2026-08-02 ~13:12 EDT: /mnt/nas-manga is mounted cifs rw from //192.168.10.4/manga with uid/gid 1000, and the systemd unit mnt-nas\x2dmanga.mount is 'generated' (from /etc/fstab) — the persistent-not-autofs requirement from read-18 holds, and the mount came back correctly after the 08-01 rig reboot (container Up 27h healthy). Directory listing shows mangas/ + thumbnails/. This morning's suwayomi-feeds-komga passes: SUWAYOMI_OK suwayomi=v2.3.2243 mount=rw komga_manga_series=1. Extension-repo errors in logs: 0.

### SI77. CWA verified healthy: ingest dir empty/flowing, automerge settings intact, fork-image supply-chain tripwires all green

**Host:** nas · **Component:** cwa (calibre-web-automated) · **Auditor:** svc:reading

Live 2026-08-02 ~13:05 EDT: container Up 5 days (healthy) on the deliberate I68 fork image ghcr.io/new-usemame/calibre-web-nextgen:v4.0.7 (upstream crocodilestick stalled pre-CVE-fix at 4.0.6); all three supply-chain tripwires pass this morning — cwa-image-digest-pinned PIN_OK (live image == compose digest pin), cwa-ghcr-tag-digest-drift TAG_UNCHANGED (ghcr tag still points at vetted digest), cwa-upstream-cve-catchup UPSTREAM_STALLED 4.0.6 (fork still justified). Ingest dir /volume1/books-ingest is empty (cwa-ingest-not-stuck pass ingest=ok), and cwa-ingest-automerge-guard confirms automerge=overwrite dupdetect=1 scan=1 freq=after_import unchanged. Only blemish is the nocover=1 regression, filed separately.

### SI78. Kobo sync consumer verified end to end: both device endpoints return HTTP 200 + parseable JSON from outside the LAN path

**Host:** fleet · **Component:** cwa kobo/koreader sync consumers · **Auditor:** svc:reading

Probed both vault-held device sync URLs (cwa.kobo_api_endpoint_admin and cwa.kobo2_api_endpoint — values not shown, they embed per-user tokens) from the operator Mac at 2026-08-02 ~13:15 EDT: both returned HTTP 200 with parseable JSON (empty sync payload = nothing new to sync, valid). Matches this morning's passing cwa-kobo-sync-consumer (KOBO_SYNC_OK) and cwa-kobo-proxy-intent (proxy=1 sync=1); the KOReader side also passes (cwa-koreader-sync-consumer KOSYNC_OK auth=401 checksums=162). This is the flow:books consumer probe — flow lane can cite this result.

### SI79. Verified healthy: seedbox rclone mount alive and current (files through today 13:13)

**Host:** nas · **Component:** rclone SFTP mount /volume1/mounts/seedbox-files · **Auditor:** flow:movies-tv

The rclone SFTP mount is NOT the stall cause: daemon running since Jul 07, directory listing instant, tv/ dir mtime Aug 2 12:45, newest movie file mtime Aug 2 13:13 (a 16GB file still syncing in). seedbox-mount-listable passed at 10:23. Fresh content from Jul 31-Aug 2 visible throughout tv/.

### SI80. Verified healthy: unpackerr up 12 days, polling all 5 apps, 0 failed extractions — correctly reporting the stuck queue, not causing it

**Host:** nas · **Component:** unpackerr · **Auditor:** flow:movies-tv

unpackerr 24h logs show no extraction errors; the 17 'Completed item still waiting' entries are it accurately relaying the arrs' import rejections (not-an-upgrade, ID-match manual import, missing dirs). Queue counters: 17 waiting, 0 extracting, 0 failed. unpackerr-poll-advancing passed (polls 45605, advancing). No RAR backlog exists in the current stall.

### SI81. Verified working end-to-end today: imports flowed as recently as 12:06 EDT and land in Plex/Jellyfin; request layer clean

**Host:** fleet · **Component:** seerr -> arr -> import -> Plex/Jellyfin consumer chain · **Auditor:** flow:movies-tv

The chain is functioning for good grabs — the stalls are per-item, not systemic. Sonarr's newest import 2026-08-02T16:06Z (HotD S02E01 REPACK), radarr's 10:36Z; arr-grabbed-not-imported GRABS_OK checked=22; Plex coverage radarr 0.993 / sonarr 0.992 COVERAGE_OK; Jellyfin streams (206, movies=580 episodes=9313); seerr-request-rot SEERR_OK checked=0 and libreseerr-request-rot OK checked=12 — no phantom requests. Deluge daemon healthy on 127.0.0.1:3254 (RPC + web up since Jul 30), seedbox-arr-deluge-e2e 200, loopback binds and public lockdown pass.

### SI82. Two queue items need one-off manual import: TWD Dead City S03E02 and Jackass 2010 blocked by 'matched by ID' grab-history quirk

**Host:** nas · **Component:** radarr/sonarr importBlocked items · **Auditor:** flow:movies-tv

Both show trackedDownloadState=importBlocked with 'Found matching series/movie via grab history, but release was matched by ID. Automatic import is not possible' — content is complete on the seedbox and visible on the mount; each needs a single manual-import action (NOT done per read-only mandate). Small residual class distinct from the storm and the missing-content wedges.

### SI83. Verified green: NAS music source intact and actively growing — the wipeout is NOT a data loss

**Host:** nas · **Component:** /volume1/music source library · **Auditor:** flow:music

The source library on the NAS is fully intact: 171 entries at find -maxdepth 2, ~47 artist dirs, with fresh writes today (YouTube dir Aug 2 12:54, Lana Del Rey Aug 2 02:39 — soularr/lidarr imports still landing) and Jul 31 activity for Linkin Park/Daft Punk. The Navidrome incident is purely a stale-flag problem in navidrome.db, not missing files. Navidrome recovery prerequisite (files present and readable over the same share) is confirmed satisfied.

### SI84. Verified green: mini CIFS music mount currently healthy — host view and container view identical (47 artist dirs each)

**Host:** mini · **Component:** mnt-nas-music CIFS mount + navidrome container bind · **Auditor:** flow:music

The ro CIFS mount //192.168.10.4/music on /mnt/nas/music (autofs-fronted, MUSIC_FOLDER=/mnt/nas/music per /opt/stacks/navidrome/.env) is active (since Jul 13, no remount cycles) and the navidrome container's /music bind serves the identical 47-entry listing. Zero kernel CIFS/VFS errors since Jul 31. Whatever transiently emptied the scanner's view at Aug 1 09:18:49Z is fully recovered — a full rescan would repopulate the library immediately.

### SI85. Verified green: rig ALAC mirror fresh — timer ran 05:03 EDT today, 3457 files, new 2026 releases present

**Host:** rig · **Component:** nas-music-mirror (ALAC mirror) · **Auditor:** flow:music

nas-music-mirror.timer last ran Sun 2026-08-02 05:03:52 EDT (next Mon 05:02), ~/Music holds 3457 files with today's changes mirrored (Lana Del Rey dir mtime Aug 2 05:04) and recent content including Olivia Rodrigo 'you seem pretty sad for a girl so in love (2026)' in .m4a (ALAC). Notably the mirror ran successfully at 05:03 EDT today over the same NAS share Navidrome scans — additional proof the share serves fine and the Aug 1 blip was transient. The mirror's empty-source abort guard (documented in the ipod-sync guide family) is exactly the guard Navidrome's scanner lacks.

### SI86. Verified green: slskd up on seedbox :5030, Soulseek Connected+LoggedIn, soularr searches flowing

**Host:** seedbox · **Component:** slskd (Soulseek daemon) · **Auditor:** flow:music

slskd answers HTTP 200 on localhost:5030 from the seedbox; today's 10:23 sweep check seedbox-slskd-e2e passed with 'Connected, LoggedIn'; and live soularr logs at 13:19 EDT show real search round-trips completing (searches return results, user caching works — e.g. users rwwwm, Toyrocket). The soularr→slskd hop is fully functional; its failures today are all Lidarr-side (DB locks, junk wanted-albums, failed imports).

### SI87. Verified green: musicseerr healthy, phantom-request check passes (checked=0 — no active requests to evaluate)

**Host:** mini · **Component:** musicseerr · **Auditor:** flow:music

musicseerr container Up 2 weeks (healthy); today's sweep check musicseerr-phantom-requests passed with PHANTOM_OK checked=0, i.e. no requests currently in a downloading state to cross-check against Lidarr monitoring — no phantoms. The media-07 reconciler leg is also healthy: lidarr-reconcile-timer-healthy passed and the unit ran to completion at 04:30 EDT Aug 1. (Separately, mini OnFailure ntfy notifications remain broken via the sec-12 env-file defect — known, sec-12.)

### SI88. Verified green: Navidrome DB backups fresh and armed — clean recovery material exists for the missing-flag incident

**Host:** mini · **Component:** navidrome backups · **Auditor:** flow:music

Today's sweep: navidrome-backup-fresh passed (fresh_backups=1, nightly sqlite backups landing in /opt/stacks/navidrome/backup per the fix-37 M15 wiring) and navidrome-backup-armed passed (disabled_msgs=0). A pre-incident DB copy (navidrome.db.bak-fix45, Jul 19) also sits in /opt/stacks/navidrome/data. Remediation for the library wipeout therefore has two safe paths: a full rescan against the healthy mount, or DB restore — both deferred to the fix queue per read-only mandate.

### SI89. Verified working: both Kobo device sync URLs answer 200 + parseable JSON through the proxied books.tabaska.us path

**Host:** nas · **Component:** CWA Kobo sync consumer · **Auditor:** flow:books

Re-ran the cwa-kobo-sync-consumer probe live from the Mac on 2026-08-02 using the vault URLs (cwa.kobo_api_endpoint_admin, cwa.kobo2_api_endpoint): both devices' tokened sync endpoints return HTTP 200 with valid JSON (82-element sync lists incl. reading-state deltas), matching the 10:23 daily pass (KOBO_SYNC_OK, task fix-38). Caveat on payload cleanliness filed separately (stray 'ResponseStatus' element).

### SI90. Verified working: KOSync auth endpoint returns 401 (enabled + auth-gated) through the public proxy `known-issue`

**Host:** nas · **Component:** CWA KOSync endpoint · **Auditor:** flow:books

GET https://books.tabaska.us/kosync/users/auth returns 401 — the /kosync blueprint is live and correctly gated (503 was the broken/disabled state per check cwa-koreader-sync-consumer, read-15, which also passed via localhost at 10:23 with populated book_format_checksums). This is the server leg only; the device-side KOReader wiring remains open under read-06.

### SI91. Verified working: Bookshelf's Deluge download-client test passes (200) and the 'Copy to CWA ingest' Connect script is wired onImport+onUpgrade; post-import relabel flow demonstrated by 10 bookshelf-imported torrents

**Host:** nas · **Component:** Bookshelf -> Deluge -> Connect(CWA ingest) · **Auditor:** flow:books

Live on 2026-08-02: Bookshelf's own downloadclient/test for Deluge returns 200 (proves NAS container -> tailnet -> seedbox loopback deluge-web auth end to end, same method as seedbox-arr-deluge-e2e). The single Connect notification is the CustomScript 'Copy to CWA ingest' (the readarr-copy-to-cwa-ingest.sh successor) with onReleaseImport=True and onUpgrade=True. On the seedbox, 10 of 11 book-labelled torrents carry the post-import 'bookshelf-imported' label, showing the grab->import->relabel loop worked for everything except the Adrift item filed separately.

### SI92. Verified working: zero stuck requests; all 12 terminal errors carry actionable operator messages; author-gate correctly refusing wrong-book binds (07-28 classics burst = Hardcover coverage gap, not a fault)

**Host:** mini · **Component:** libreseerr request board · **Auditor:** flow:books

Live read of /opt/stacks/libreseerr/data/requests.json on 2026-08-02: 30 requests, 18 completed, 12 error, 0 in any non-terminal state (matches libreseerr-request-stuck pass STUCK_REQUESTS=NONE and libreseerr-request-path-guards pass REQUEST_PATH_OK at 10:23, fix-48). The 2026-07-28 burst (The Odyssey x3, The Iliad, Le Morte d'Arthur, The romance of Arthur) all terminal-errored with the designed messages — author-gate refusals (requested author 'Όμηρος'/editor names vs Hardcover records) and provider-missing titles — i.e. the C1/C4 protections working as built; public-domain classics with translator/editor authorship are a known-weak discovery area on Hardcover, not a pipeline break. hardcover-token-valid also passed (HC_TOKEN_OK days_left=352) and metadata-search-canary passed (CANARY_OK rank=2 results=14).

### SI93. Verified: library is growing via the Shelfmark/manual path (newest Calibre book 2026-07-29); last Bookshelf grab (07-20) landed in Calibre; no Bookshelf grabs in 13 days is demand-driven, not breakage

**Host:** fleet · **Component:** books chain end-to-end continuity · **Auditor:** flow:books

Calibre metadata.db holds 81 books, newest 'How to Do Nothing' 2026-07-29 01:36 and 4 more since 07-27 — all arrived via the Shelfmark/manual ingest path since Bookshelf's newest history event is 2026-07-20T23:45 (Cassiel's Servant grab->import same night, and today's books-pipeline-lost-imports pass LOST_BOOKS=NONE confirms every Bookshelf book-with-file is present in Calibre). Bookshelf queue is empty and wanted-missing=1, so the absence of grabs since 07-20 reflects no new requests reaching the arr (the 07-28 libreseerr burst was all author-gate/provider terminal errors), not a dead pipeline — its Deluge client test passes live. cwa-ingest-automerge-guard, cwa-kobo-proxy-intent, books-format-guard, bookshelf-foreign-records/grab-history, books-language-guard, cwa-library-author-split and cwa-library-dup-titles all passed at 10:23.

### SI94. ABS API verified healthy at the consumer end: libraries respond, podcast auto-download flowing (newest episode 1.8d old)

**Host:** nas · **Component:** audiobookshelf (:13378) · **Auditor:** flow:audiobooks-ipod

Probed the ABS API from the Mac at 2026-08-02 ~13:05 EDT with the vault key audiobookshelf.api_key. Audiobooks library total=1 ('Child's New Story Book', added 2026-07-23 -- the library's entire content since read-16 setup, small but consistent everywhere downstream), Podcasts library total=8 shows. recent-episodes shows Grey Wolf Feed ep 1058 published 2026-07-31 already downloaded (1.8d old), so podcast auto-download is flowing -- taxonomy #13 zero-throughput checked and negative. Matches today's 10:23 check audiobookshelf-libraries-consumer pass 'ABS_OK books=1 podcasts=8' (read-16).

### SI95. abs.tabaska.us through Caddy serves the real Audiobookshelf app (proxy path verified, not bare 200)

**Host:** mini · **Component:** Caddy vhost abs.tabaska.us · **Auditor:** flow:audiobooks-ipod

From the Mac at 2026-08-02 ~13:06 EDT, https://abs.tabaska.us/ redirects to /login/ which returns the Audiobookshelf Nuxt app (title 'Audiobookshelf', 17 app-specific body references). Taxonomy #10 (proxy-path 4xx while direct port green) probed and negative -- the browser-consumer path through mini Caddy to NAS :13378 is intact.

### SI96. iPod staging leg verified end to end: timer ran 05:31 today, staged content exactly matches ABS (1 book + 14 episodes), mounts and dead-man healthy

**Host:** rig · **Component:** abs-ipod-stage.timer / RO CIFS automounts / staging (read-19) · **Auditor:** flow:audiobooks-ipod

abs-ipod-stage.timer fired Sun 2026-08-02 05:31:57 EDT (OnCalendar 05:30 + RandomizedDelaySec=300) and the service finished cleanly: 'stage done: 1 audiobooks, 14 podcast episodes'. Staged inventory equals ABS exactly (ABS episode counts 3+6+5=14 across Grey Wolf Feed / MinnMax / Kit & Krysta; 1 book). The audiobooks/podcasts RO CIFS mounts are x-systemd.automount with idle-timeout=120 -- absent from 'mount' output is by design; both automount units are active and an ls through them lists all 8 shows plus the book, with the share's newest file ('1058 - Carrion Comfort ... .mp3') matching ABS's newest episode and already copied to staging on Aug 01 14:26. Healthchecks dead-man abs-ipod-stage-rig is up, last_ping 2026-08-02T09:31:59Z (= today's 05:31 EDT run); it also behaved correctly through the Aug 01 rig-off window (missed 05:30 run, Persistent=true catch-up at boot pinged it back). Check ipod-abs-stage-fresh passed at 10:23 with 'IPOD_ABSENT stage_ok audiobooks=1 podcasts=14 manifest_age_h=5' (iPod not plugged in -- a passing state by design).

### SI97. 5 of 8 podcast shows have zero episodes (autoDownload on, only cover.jpg on disk) -- consistent everywhere, likely finished shows with no new episodes since 07-23 subscribe

**Host:** nas · **Component:** audiobookshelf podcast subscriptions · **Auditor:** flow:audiobooks-ipod

Hell of Presidents, Hell on Earth, Movie Mindset, The Players Club and Time For My Stories show numEpisodes=0 in the ABS API with autoDownloadEpisodes=True, and their /volume1/podcasts dirs (viewed via the rig RO CIFS mount) contain only cover.jpg. This is internally consistent (ABS DB, NAS files, and iPod staging all agree -- no missing-file green-but-broken condition), and ABS auto-download only grabs episodes published after subscription (2026-07-23); these are mostly completed/limited series. Filed as a neutral observation so the operator can confirm the backlog omission is intentional -- if back-catalog episodes were expected on the iPod, none will ever arrive for these 5 shows.

### SI98. Comics chain verified healthy end to end: Mylar3 DDL grabs post-processed, Komga scans every 6h, newest book streams real page bytes

**Host:** nas · **Component:** mylar3 -> /volume1/comics -> komga (Comics library) · **Auditor:** flow:manga-comics

Mylar3 history shows Watchmen 1-12 all Post-Processed 2026-07-27 19:50 (matches file mtimes on /volume1/comics), wanted list empty — idle-normal for a completed 12-issue series, nothing stuck. Komga Comics library (root /data/Comics) periodic-scanned successfully today at 02:03 and 08:03 EDT ('Scanned 2 series, 13 books'), matching disk exactly (12 Watchmen + 1 'Homelab Sample Comic' bootstrap file, which is still present — deliberate read-17 test data). Consumer probe: page 1 of the NEWEST book (Watchmen 12, created 07-27T23:52Z) returned HTTP 200 with 1,141,476 bytes of verified JPEG (1680x2560), and OPDS returned 200 in today's komga-libraries-consumer run. mylar3-feeds-komga (MYLAR3_OK cbz=13 komga_comics_series=2) corroborated live.

### SI99. CIFS mount itself verified healthy and correctly persistent (not autofs) with remote-fs ordering — the boot race is a container-ordering gap, not a mount regression

**Host:** rig · **Component:** mnt-nas\x2dmanga.mount (CIFS //192.168.10.4/manga) · **Auditor:** flow:manga-comics

findmnt shows //192.168.10.4/manga on /mnt/nas-manga as a real persistent cifs mount (vers=3.0, uid/gid 1000, rw, soft), active since boot 08-01 10:25:52 EDT; the unit carries After=remote-fs-pre.target network-online.target per the read-18 design. Host-side reads/writes work (mangas/ + thumbnails/ visible; thumbnails last written Jul 28). The read-18 mount hardening itself held across the 08-01 reboot — only the docker container start ordering (separate high finding) is unguarded.

### SI100. Suwayomi service itself alive and current: healthy container, GraphQL API serving, global updater ran this morning, download queue clean

**Host:** rig · **Component:** suwayomi (updater + API surface) · **Auditor:** flow:manga-comics

Container Up 27 hours (healthy) — restart time consistent with the rig's 08-01 boot, not a crash loop. GraphQL API on :4567 answers library, chapter, and status queries; last global library update timestamp 1785672756070 = 2026-08-02 ~08:11 EDT, so new-chapter detection is running on schedule; download queue empty/STOPPED (nothing stalled). No new upstream chapters for the two fully-downloaded ongoing series since 07-27 (Spy x Family totalCount steady at 155), so zero new files on the share this week is plausible-normal on the producer side — the pipeline breaks are the two high findings, not the updater.

### SI101. DSM system/swap mirrors md0/md1 show [4/3] [UUU_] (one member slot missing) — likely empty-bay artifact, worth a storage-lane confirmation

**Host:** nas · **Component:** DSM system RAID md0/md1 · **Auditor:** flow:photos

/proc/mdstat shows the DSM system partition (md0) and swap (md1) as raid1 [4/3] [UUU_] with members sata1/sata2/sata3 only, while the three data volumes (md2/md3/md4, single-disk raid1 each) are all [U] healthy. On a 4-bay DS920+ this pattern is usually a cosmetic empty-bay marker, but it can also mean a previously-installed disk's system partition dropped out. Neutral observation from the photos lane (I was on the box chasing I/O); flagging for whoever owns the storage territory to confirm bay population.

### SI102. VERIFIED GREEN: smart-search consumer works end to end through the public vhost on the day-window NAS iGPU backend

**Host:** fleet · **Component:** immich smart search (consumer path) · **Auditor:** flow:photos

Live at ~13:15 EDT: POST https://immich.tabaska.us/api/search/smart with the verify key (vault immich.verify_api_key) returned HTTP 200 with 3 relevant IMAGE assets for query 'beach' — full text-encode + vector-search path exercised with rig ML off (day window), i.e. the NAS OpenVINO fallback is genuinely serving. Confirms today's 10:23 pass of crit check immich-smart-search-consumer. Warm latency 13s is degraded (see the NAS I/O finding) but the path is functionally intact.

### SI103. VERIFIED GREEN: ML version parity across all three nodes — server v3.0.3 = NAS ML v3.0.3-openvino = rig ML v3.0.3-cuda

**Host:** fleet · **Component:** immich ML version parity · **Auditor:** flow:photos

Server /api/server/version reports 3.0.3; NAS runs immich-server:v3.0.3 + immich-machine-learning:v3.0.3-openvino (Up 8 days, healthy); rig runs immich-machine-learning:v3.0.3-cuda (Exited 143 six hours ago = the 07:00 EDT day-window stop, known-normal). No version skew — the past NAS-vs-rig ML mismatch hazard from memory is not present.

### SI104. VERIFIED GREEN: ML day/night window operating exactly as designed — queues paused by day, container stopped at 07:00, zero job backlog

**Host:** fleet · **Component:** glue-14 immich-ml-window (day/night GPU gate) · **Auditor:** flow:photos

/api/jobs (admin key, vault immich.admin_api_key) shows precisely the three ML-GPU queues named in immich-ml-window.sh (smartSearch, faceDetection, ocr) paused, all 19 queues at active=0 waiting=0 failed=0, and the rig container exited (143) ~6h ago — meaning it was running through last night's 01:00-07:00 window and the off-transition fired on time this morning. No unbounded thumbnail/ML backlog (taxonomy #13 clean on the job side).

### SI105. VERIFIED GREEN: Immich pg-dump backups landing daily at 02:01, newest today (2026-08-02), sizes consistent

**Host:** nas · **Component:** immich postgres backup · **Auditor:** flow:photos

/volume1/photo/backups holds daily immich-db-backup-*.sql.gz files at 02:01 with the newest from today 2026-08-02 (256,374,315 bytes) and a smooth monotonic size progression over the visible retention window — the DSM pg-dump task is healthy despite the freshness check being dead. This is the ground truth behind the fix-35 TIMEOUT: the backup itself did not regress.

### SI106. YouTube video chain verified end to end: mount rw, 1364/1364 disk-to-Plex coverage, ACL intact, newest file visible in Plex

**Host:** mini · **Component:** pinchflat -> /mnt/nas-youtube -> plex section 4 · **Auditor:** flow:youtube

Live this session: /mnt/nas-youtube is a healthy rw CIFS mount of //192.168.10.4/youtube (autofs, 4.0T used/29%). Today's 10:23 run passed pinchflat-plex-visible (COVERAGE_OK disk=1364 plex=1364 ratio=1.00) and plex-youtube-readable (plexacl=ok — the PlexMediaServer ACE hazard is clear). Spot-checked the consumer end via Plex API: section 4 recently-added newest item addedAt 2026-07-13T17:12:14 exactly matches the newest disk file (Kaji Pm short, 2026-07-13 17:12). Pinchflat container Up 2 weeks (healthy), Oban cron ticking at 13:27 today.

### SI107. POT countermeasure pipeline verified: plugin 1.3.1 == server 1.3.1 (version-match hazard clear), server up 24 days

**Host:** mini · **Component:** bgutil-pot + pinchflat yt-dlp plugin · **Auditor:** flow:youtube

The bgutil version-match hazard is clear: today's pinchflat-pot-provider pass shows pinchflat's baked yt-dlp plugin as bgutil:http-1.3.1 (external, available), and a live ping this session from inside the docker network returned server version 1.3.1 with ~23.9 days uptime. bgutil-pot-serving also passed at 10:23. The provider was therefore healthy when item 3076 failed, confirming that failure is YouTube-side hard-gating, not a pipeline fault.

### SI108. Zero downloads in 14 days is supply-side explained, not a stalled pipeline: index loop alive, only 2 new uploads and both YouTube-gated

**Host:** mini · **Component:** pinchflat throughput · **Auditor:** flow:youtube

Newest media_downloaded_at fleet-wide is 2026-07-13T21:12Z and dl_last_14d=0, which looks like failure-pattern #13 zero-throughput — but it is fully explained. Source 2 (Kaji Pm) is on a 43200-min (30-day) index cadence, last indexed 2026-07-12, with no uploads newer than what's downloaded. Source 1 (Yellow Cherry Jam) indexes daily (last 2026-08-02T00:34:50Z, today) and has exactly 2 undownloaded new uploads: id 3430 (bzn6EU0HlU4, uploaded 07-27) which is members-only ('available to this channel's members on level: Two Yellow Cherries') — correctly unobtainable and correctly not counted by the stuck-media check — and id 3076, the bot-check item filed separately. Indexing, filtering, and error attribution are all working as designed.

### SI109. beets audio leg verified: daily import ran today 03:15, web UI green — idle only because MeTube has had no new audio since Jul 8

**Host:** nas · **Component:** beets (youtube audio leg) · **Auditor:** flow:youtube

Checks nas-beets (200) and nas-beets-ingest-fresh (ingest=fresh) passed at 10:23, and live this session /volume1/docker/beets/import.log has mtime 2026-08-02 03:15:27 with daily 'import started' entries for Aug 1 and Aug 2. Each run logs 'skip /music/YouTube' because there is nothing new to tag — the newest MeTube audio drop is 2026-07-08 (MeTube is on-demand, so idle is normal, not zero-throughput). Linkage note only (music lane owns it): the downstream Navidrome consumer is broken fleet-wide today (navidrome-library-present PRESENT_DEGRADED missing=3495/3495, fix-28 regression), so tagged YouTube audio is currently invisible in Navidrome even though the beets leg itself is healthy.

### SI110. MeTube backend + yt-dlp verified live (:8081/version), container Up 3 weeks

**Host:** mini · **Component:** metube · **Auditor:** flow:youtube

Live probe this session of the /version endpoint (which proves the aiohttp backend and yt-dlp module loaded, not just the static SPA) returned yt-dlp 2026.07.06.234510 on app 2025.11.13; check metube-serving also passed at 10:23. Container Up 3 weeks, restart count normal. yt-dlp build is ~4 weeks old, consistent with the known-normal weekly image-pin lag — not filed.

### SI111. Core journaling reflection loop verified end-to-end: E2E_OK in both of today's runs, n8n wiring clean, 255/255 executions success in 30d

**Host:** mini · **Component:** journaling stack (memos -> n8n -> rig coach -> comment loop) · **Auditor:** flow:journaling

journaling-loop-e2e (journal-06) returned E2E_OK — not SKIP_COACH_UNAVAILABLE — in both the 10:23 EDT daily run and the fresh 13:01 EDT audit sweep, each posting a probe memo and seeing exactly one reflection comment after 6s, then self-cleaning. Live probes at ~13:10 EDT: memos /healthz 'Service ready.', n8n /rest/settings 200, POST /webhook/journal armed (GET returns the 'not registered for GET' 404 that proves a POST webhook owns the path). n8n DB (read-only): journal-analyze active=1 with exactly one webhook_entity row (path 'journal', POST) and no stale rows; last-30d execution history is 255/255 success. Real memos 18, 59, 62 each carry exactly one reflection comment written 4-7s after creation, and the comment write-back events quick-exit (~60-80ms) proving the loop guard holds. Also green today: journaling-memos-webhook-wired WEBHOOK_OK and journaling-igdb-enrich IGDB_ENRICH_OK. Newest real memo is 2026-07-27 (6 days) — user quiet period, not a service fault (e2e probe memos self-delete so they don't appear).

### SI112. Voice-note transcription path verified: /health 200 live and real probe-clip transcription green in both of today's runs

**Host:** mini · **Component:** faster-whisper (speaches, :8010) · **Auditor:** flow:journaling

Live at ~13:10 EDT, http://localhost:8010/health returned 200. The deeper journaling-whisper-transcribes daily check (journal-04, real CPU inference against the cached Systran/faster-whisper-small model, not just liveness) returned WHISPER_TRANSCRIBES_OK in both the 10:23 daily run and the 13:01 audit sweep — the check that previously flapped has stayed recovered. The workflow's audio branch also has a verified fail-safe: the Merge-transcript node falls back to the text-only messages if transcription yields nothing, so the primary text path cannot regress.

### SI113. Coach model registered and reachable from mini; loads on demand even in the day window (E2E_OK with 6s reflection at ~12:56 EDT)

**Host:** rig · **Component:** llama-swap :9292 / dolphin-venice-24b (journaling coach model) · **Auditor:** flow:journaling

Live at ~13:08 EDT, llama-swap /v1/models from the mini lists dolphin-venice-24b (status unloaded — the normal on-demand idle state; all models unloaded means the 3090 Ti is free, consistent with the glue-14 day window where Immich ML is off the card). Despite the coach being documented best-effort by day, both of today's journaling-loop-e2e runs got a real reflection in 6s rather than SKIP_COACH_UNAVAILABLE, so day-window availability is currently good, not merely tolerated. journaling-coach-model-reachable passed in both runs.

### SI114. DB-only OWUI journaling artifacts intact: Save-to-Journal action active and Journaling Coach preset on dolphin-venice, verified live

**Host:** rig · **Component:** Open WebUI (save_to_journal action fn + journaling-coach preset) · **Auditor:** flow:journaling

Probed live at ~13:15 EDT from the mini using the runner's OWUI creds (grep'd from /etc/verification/env into shell vars, never printed): /api/v1/functions/id/save_to_journal reports is_active=True type=action, and /api/v1/models/model?id=journaling-coach reports base_model_id=dolphin-venice is_active=True. Matches the green journaling-owui-save-fn-installed and journaling-owui-coach-preset checks (journal-05 drift guards) in both today's runs. These artifacts live only in the OWUI DB, so this confirms no redeploy/volume-wipe drift.

### SI115. Paying consumer path verified end-to-end: virtual-key completion via public vhost returned real tokens

**Host:** rig · **Component:** LiteLLM virtual-key path (llm.tabaska.us) · **Auditor:** flow:ai-serving

Reproduced the full consumer chain live at ~13:10 EDT: Mac -> AdGuard -> mini Caddy -> https://llm.tabaska.us -> rig LiteLLM :4000 DB-backed virtual key (vault ai_stack.litellm_verify_key) -> llama-swap :9292 -> model 'utility', got finish_reason=stop with content 'PONG'. This is the exact hop that historically 503s while master-key liveness stays green (taxonomy #2) — it is genuinely working today. Corroborates today's 10:23 checks: rig-litellm-vkey-e2e pass, rig-ai-e2e pass, rig-litellm-consumer-e2e pass (LITELLM_CONSUMER_OK 'PONG'), rig-litellm pass (401 = auth gate up). LiteLLM container logs over 24h contain no real errors — only the known-normal 'No api key passed in' noise (75 lines).

### SI116. HA Assist LLM leg healthy: ha-assist-rig-llm-reachable passed today and ollama shim serves 3 models from LAN

**Host:** rig · **Component:** ollama shim :11434 / HA Assist leg · **Auditor:** flow:ai-serving

The HA Assist leg that recovered today is confirmed: check ha-assist-rig-llm-reachable passed at 10:23 (assist_llm=ok). From the Mac (same LAN vantage HA uses), rig :11434 /api/tags returns 200 with 3 models: nomic-embed-text:latest, tag:fast, llama3.2:3b. Probing from HA's own vantage is untestable (HA is LAN-only, SSH refused) — LAN probe from Mac is the agreed proxy. rig-ollama (200) and rig-ollama-models also passed today; rig-ollama-keepalive shows OLLAMA_KEEP_ALIVE=0 as configured.

### SI117. Marinara auth gate and Lumiverse verified healthy at the proxy end; connection configs intact

**Host:** rig · **Component:** marinara / lumiverse (public vhosts) · **Auditor:** flow:ai-serving

https://marinara.tabaska.us returns 401 without credentials — that IS the pass condition (Caddy basic_auth gate; matches rig-marinara-auth-gate pass). https://lumiverse.tabaska.us returns 200 post-restart, container healthy, and its startup log shows lumiverse.tabaska.us in trusted origins. Today's rig-lumiverse-connections pass shows the full consumer wiring intact: llm='LiteLLM Creative' -> https://llm.tabaska.us/v1 plus 3 image connections (NoobAI-XL, Z-Image Turbo, Flux.2 Klein) all -> https://comfyui.tabaska.us; rig-marinara-connections likewise shows the Flux.2 Klein image_generation connection (model klein-9b-comfyui).

### SI118. ComfyUI reachable through arbiter with all 3 model stacks loader-visible (no image generated)

**Host:** rig · **Component:** comfyui.tabaska.us via gpu-arbiter · **Auditor:** flow:ai-serving

https://comfyui.tabaska.us/object_info returns 1013 nodes through the gpu-arbiter proxy. All three advertised model stacks are present in loader dropdowns: (1) Anime = NoobAI-XL-v1.1.safetensors in CheckpointLoaderSimple; (2) Z-Image Turbo = z_image_turbo_bf16.safetensors + 3 variants in UNETLoader; (3) Flux.2 Klein = flux-2-klein-9b-Q8_0.gguf + flux-2-klein-base-9b-Q8_0.gguf in UnetLoaderGGUF, with flux2-vae.safetensors (VAELoader), Flux2TurboComfyv2.safetensors (LoraLoader) and Qwen3 text encoders (DualCLIPLoaderGGUF). No image generation was triggered per the sweep mandate. Matches today's rig-comfyui and rig-comfyui-arbiter passes.

### SI119. No GPU contention conflicts in arbiter logs over 48h; yield path verified by today's checks

**Host:** rig · **Component:** gpu-arbiter · **Auditor:** flow:ai-serving

gpu-arbiter (Up 27h) logs over the last 48h contain only /system_stats polling and a benign pip warning from startup — zero unload/yield/conflict/deny/503 events, i.e. no LLM-vs-image contention incidents recently. Today's 10:23 checks corroborate the yield machinery works: rig-ai-gpu-yield pass (YIELD_OK vram=1014MiB), rig-gpu-arbiter-unload-hook pass, rig-comfyui-arbiter pass (200). Day-window state is as designed (immich ML off by day, card free).

### SI120. Wiki-RAG retrieval end verified: live query against homelab-wiki returns relevant chunks (325 docs tracked); note two quirks

**Host:** rig · **Component:** open-webui wiki-RAG (ai.tabaska.us) · **Auditor:** flow:ai-serving

Consumer-end verified live: POST /api/v1/retrieval/query/collection on the homelab-wiki collection (id ce2a3840) returned 3 relevant wiki chunks for a LiteLLM question — retrieval genuinely works, complementing the producer-only mini-wiki-rag-fresh check (pass today, age_h=5; last sync 05:15 EDT exit 0, '+0 ~0 -0, total tracked 325'). Two observations for future auditors: (1) OWUI's knowledge API returns files:null and data:{} on both list and detail endpoints and the collection updated_at is frozen at 2026-07-16 — an empty-looking API view that could be misread as data loss; the retrieval query is the trustworthy probe. (2) The 08-01 05:10 sync run failed with HTTP 502 because rig (which hosts OWUI) was powered off during the Jul-31->Aug-1 ~23h gap flagged in preflight; mini-wiki-rag-fresh correctly went stale and the next scheduled run recovered — no missed content (0 deltas).

### SI121. Two transient backend dial-refused lines in llama-swap over 24h — consistent with documented day-window swap behavior

**Host:** rig · **Component:** llama-swap :9292 · **Auditor:** flow:ai-serving

llama-swap (Up 27h, healthy) logged 'proxy error: dial tcp [::1]:10004: connect: connection refused' twice in 24h (2026-08-01 18:41Z and 2026-08-02 14:40Z = 10:40 EDT, ~17min after the daily verification run). This is a request hitting a model backend port during swap-in/out, the same family as the known-normal 'exited prematurely' day-window contention noise — not a storm (2 lines) and the consumer path completed successfully both at 10:23 (checks) and 13:10 EDT (my live PONG probe). Filed as a neutral observation so a future sweep can distinguish growth from baseline.

### SI122. Verified working: dead-man DOWN/UP notifications published to ntfy, including during the rig 23h outage

**Host:** fleet · **Component:** healthchecks -> ntfy dead-man chain · **Auditor:** flow:monitoring-alerting

The Healthchecks Notification log proves the verification-mini DOWN was sent to the ntfy channel (topic 'healthchecks', priority 4, in-network http://ntfy:80) at 2026-08-02T02:26:49Z with empty error, and the UP at 14:25:03Z is still visible in the ntfy topic cache (the DOWN was only evicted by ntfy's ~12h message cache). The chain also paged restic-backup-rig down/up around the rig's 23h power-off (Aug 1 11:40Z and 18:27Z). So dead-man detection, notification dispatch, and ntfy publish all demonstrably work; only device-side delivery remains unproven (separate gap finding).

### SI123. Verified working: the 10:23 daily sweep's failure summary published to the verification topic

**Host:** mini · **Component:** verification runner -> ntfy topic · **Auditor:** flow:monitoring-alerting

The runner-to-ntfy leg carried this morning's daily result: a 'Verification: 2 NEW failure(s)' message timestamped 10:23:08 EDT is cached on the verification topic, matching the journal's verify-cycle summary line exactly (267/296 passed, 29 failed). Tiered runs (fast/quick/media/docker-fleet/url) publish state-diff messages continuously, and ntfy reports one live subscriber connection. Alerts flowed this morning as designed.

### SI124. Verified working: Diun (mini) watch cycle fresh — ran today 06:00, 43 images, 0 failed

**Host:** mini · **Component:** diun · **Auditor:** flow:monitoring-alerting

Diun on mini completed its daily cron at 06:00:29 EDT today, analyzed 43 images with 0 failed/0 skipped, and scheduled the next run for Aug 3 06:00. The NAS Diun instance passed its daily check (alert-diun-nas-up, running) in the 10:23 sweep. Image-update alerting cadence is intact.

### SI125. Verified working: Beszel hub shows mini/nas/rig all up with sub-minute freshness

**Host:** mini · **Component:** beszel hub · **Auditor:** flow:monitoring-alerting

Authenticated to the Beszel hub API (vault beszel/admin_user + admin_password) at 13:34 EDT: all three agent systems (mini, nas, rig) report status up with 'updated' timestamps seconds old. Metrics collection across the fleet is current; the 10:23 sweep's alert-beszel-none-down also recovered this morning.

### SI126. Verified: all 16 Healthchecks dead-men up; export-manifests-rig's 152h-old ping is normal for its weekly Monday schedule

**Host:** fleet · **Component:** healthchecks dead-men · **Auditor:** flow:monitoring-alerting

Live API poll at 13:15 EDT shows 16/16 checks up with recent pings (verification-fast-mini 13:26 EDT, ai-stack-rig 13:20 EDT, backups overnight). The flagged export-manifests-rig staleness (last ping 2026-07-27T08:09Z, ~152h) matches its cron schedule '0 4 * * 1' (Mondays 04:00) exactly — last Monday was Jul 27, next due Aug 3, grace 24h — so it is not overdue and needs no filing. Kuma cross-check: 57 active monitors, 0 down.

### SI127. Bug-intake and auto-triage verified working end to end — both daily e2e checks green today and every leg independently re-confirmed read-only

**Host:** mini · **Component:** bug-intake chain (Homepage -> n8n form -> Forgejo -> triage) · **Auditor:** flow:bug-intake

Today's 10:23 EDT run: bug-intake-e2e (crit, bug-01) = pass 'BUGREPORT_OK form+submit->issue #61 ... deleted=True' and bug-triage-e2e (bug-02) = pass 'BUGTRIAGE_OK issue #62 diagnosis comment posted + labeled [service:immich ... triaged] deleted=True' — the rig LLM answered even in the day VRAM window. Independently re-verified this session without submitting: public form GET via Caddy renders the armed n8n form (200, 30942 bytes, 'What happened' field present); Homepage tile 'Report a Problem' live in /api/services with href https://bug.tabaska.us target=_blank; bug-triage-evidence container healthy, 0 restarts, up since 07-27; Forgejo API reachable with the scoped probe token; fast checks bug-intake-form-armed, bug-intake-homepage-tile, bug-triage-evidence-armed all pass. n8n Up 5 days (healthy).

### SI128. Home repo control plane verified in sync: local == GitHub == Forgejo at 7adbd58, working tree clean, vault-lint gate passes

**Host:** repo · **Component:** ~/GitHub/Home publish-deploy chain · **Auditor:** flow:git-control-plane

Verified 2026-08-02 ~13:00 EDT from the Mac: git ls-remote shows origin/main and forgejo/main both at 7adbd584973f, matching local HEAD, with a clean porcelain — the publish-deploy.sh dual-push discipline held for the Home repo. The vault-lint gate that publish-deploy.sh runs (foss-setup/scripts/secrets/vault-lint.py, confirmed read-only, no write/subprocess calls in its 72 lines) exits 0: no unexplained empty vault keys (14 documented exceptions).

### SI129. /opt/stacks verified clean and pushed: porcelain=0, HEAD f12c6fd == origin/main

**Host:** mini · **Component:** /opt/stacks (Forgejo home/docker-stacks) · **Auditor:** flow:git-control-plane

Verified live 2026-08-02: the mini /opt/stacks repo has zero porcelain entries, HEAD f12c6fd (retro-guide update) exactly matches origin/main on Forgejo, and status -sb shows no ahead/behind markers. The git-stacks-clean tripwire condition holds; the recurring orphaned-drift pattern from the opt-stacks-git-hygiene memory is not present today.

### SI130. etckeeper on mini verified clean (unclean rc=1 = clean per convention)

**Host:** mini · **Component:** etckeeper · **Auditor:** flow:git-control-plane

Verified live 2026-08-02: 'sudo etckeeper unclean' exits 1 on mini, which by etckeeper convention means /etc has NO uncommitted changes — the /etc git capture is current.

### SI131. Nightly ansible-pull ran successfully on both hosts today, pulling current code from Forgejo

**Host:** fleet · **Component:** ansible-pull.service/timer (mini + rig) · **Auditor:** flow:git-control-plane

mini: ansible-pull.timer fired 2026-08-02 04:23 EDT, recap ok=41 failed=0 unreachable=0 (changed=1 is the chezmoi task filed separately); next run Mon 04:33. rig: ran 2026-08-02 04:47 EDT, recap ok=29 failed=0 (also a catch-up run Aug 01 14:29 after the ~23h power gap noted in preflight). The unit's CONTROL_REPO_URL=git@forgejo:home/homelab.git, and forgejo/main == origin/main == 7adbd58 (verified), so nightly convergence executes the current playbook.

### SI132. rig chezmoi verified fully converged: empty diff (no content hunks, no mode flap), source clean at forgejo HEAD

**Host:** rig · **Component:** chezmoi dotfiles · **Auditor:** flow:git-control-plane

Verified live 2026-08-02: 'chezmoi diff' on rig produces zero output (not even the known-normal mode-bit flap), and the source repo at ~/.local/share/chezmoi has a clean porcelain at 394188f, which equals forgejo/main of home/dotfiles. Note this convergence is maintained by the nightly non-idempotent 'chezmoi init --apply' re-run documented in the ansible finding — the outcome is correct even though the mechanism reports phantom changed.

### SI133. mini restic -> B2 verified green end to end (fresh snapshot, clean integrity check, dead-man corroborates)

**Host:** mini · **Component:** restic-backup.service -> B2 · **Auditor:** flow:backups

Last run finished 2026-08-02 01:41:13 EDT: backup + retention + structural 'restic check' all clean (11 snapshots, no errors). Daily check restic-snapshot-fresh-mini (crit) passed at 10:23 with FRESH age_hours=8; restic-snapshot-hygiene-mini HYGIENE-OK; restic-role-matches-source-mini RESTIC-ROLE-OK; Healthchecks dead-man restic-backup-mini status=up, last ping 2026-08-02T05:41:13Z matching the journal to the second.

### SI134. rig restic -> B2 verified green, including a successful Persistent=true catch-up after the ~23h power-off

**Host:** rig · **Component:** restic-backup.service -> B2 · **Auditor:** flow:backups

The rig was powered off Fri Jul 31 11:07 -> Sat Aug 1 10:25 EDT, missing its 01:30 window on Aug 1; Persistent=true fired a catch-up run at 14:27 Aug 1 which succeeded, and the normal Aug 2 01:35 run also succeeded with a clean 25-snapshot integrity check. restic-snapshot-fresh-rig FRESH age_hours=8, hygiene/bloat/role-match checks all pass, Healthchecks restic-backup-rig up (ping 05:36:21Z = journal finish). The backup leg fully absorbed the outage; why the rig was off ~23h is another lane's question.

### SI135. NAS Tier-1 Hyper Backup -> B2 verified fresh (last completed version ~2026-08-01 20:52 EDT)

**Host:** nas · **Component:** Hyper Backup -> B2 (TabaskaNAS_2.hbk) · **Auditor:** flow:backups

nas-hyperbackup-b2-fresh (crit) passed today with tok=ok, and the underlying success signal — last_version_inodedb mtime in the client image cache, rewritten only when a backup version completes — reads Aug 1 20:52, ~17h before probe, well inside the 50h window. No plaintext synobackup log exists on this DSM (/var/log/synolog holds only *.db), so the cache mtime plus the check are the designed evidence. Standing note from the check comments: the window should be tightened to ~30h once the daily schedule is confirmed in the DSM UI; observed cadence is consistent with daily.

### SI136. Immich DB dump leg verified green: daily 02:31 dumps, latest today 254MB, dead-man pinging

**Host:** nas · **Component:** Immich pg dump (DSM task 9) · **Auditor:** flow:backups

Newest dump immich-2026-08-02.sql.gz (254,764,112 bytes) landed at 02:31 today with an unbroken daily series and steady ~monotonic size growth (no truncation). Checks backup-immich-dump-fresh (crit) and backup-immich-dump-nonempty both passed at 10:23; Healthchecks immich-dump-nas status=up with last ping 06:31:28Z matching the dump time. Note this is a different leg from today's timed-out nas-immich-backup-freshness (fix-35, phone-asset flow — flow:photos lane is re-running that one).

### SI137. HA off-eMMC backup leg verified green: daily encrypted tar landed 04:45 today on the NAS

**Host:** ha · **Component:** HA -> NAS offsite backup · **Auditor:** flow:backups

ha-backup-offsite-fresh (crit) passed at 10:23 (backup=fresh), and the target dir shows an unbroken daily series — Automatic_backup tars for Jul 31, Aug 1, and Aug 2 at 04:45, ~23.5MB each with plausible day-over-day growth. Encryption key custody is documented at vault hosts.ha.backup_password. (See the separate medium finding on this directory's permissive ACLs.)

### SI138. Game-save legs verified green: hourly AMP zips current to 13:00 EDT, ludusavi 2-hourly runs succeeding, mesh 100% replicated to NAS

**Host:** rig · **Component:** AMP backups + ludusavi/Syncthing game saves · **Auditor:** flow:backups

AMP MinecraftCross01 hourly backup zips are present for 10:00-13:00 EDT today (~275MB each); game-amp-backup-fresh passed at 10:23 (BACKUP-OK age=982s) and game-amp-backup-policy (crit) POLICY-OK — no DoNothing refusal regression. ludusavi-backup.timer (user unit) is active, last run 12:03:02 EDT success (4 games -> /home/btabaska/game-saves), next fire 14:02; game-saves-mesh-synced on the NAS hub reports files=23 rig_complete=100% state=idle, and restic-bloat-rig confirms the AMP zips are excluded from the B2 snapshot.

### SI139. B2 ransomware immutability verified at the consumer end today: live delete refused 401, retention locked, bucket manifest matches

**Host:** mini · **Component:** b2-bucket-guard (B2 immutability + policy) · **Auditor:** flow:backups

Today's 10:23 sweep ran b2-restic-immutable (crit) which asserts governance/30d default retention, per-file locks on the newest packs, and performs a real b2_delete_file_version attempt expecting refusal — result IMMUTABLE with delete-probe=401. b2-bucket-policy also passed with exactly the two expected buckets. Cited from the sweep per fix-22's design; not re-run live to avoid a second delete probe in one day.

### SI140. export-manifests-rig 152h-old ping is on schedule, not stale (weekly Monday-04:00 cron, next due Aug 3)

**Host:** fleet · **Component:** Healthchecks export-manifests-rig · **Auditor:** flow:backups

Preflight flagged the 152h-old last ping for verification. The Healthchecks definition is cron '0 4 * * 1' (Mondays 04:00) with 24h grace; last ping 2026-07-27T08:09:38Z = Monday Jul 27 04:09 EDT, exactly on cadence, and no Monday has passed since. Status is up and the next expected ping is Mon Aug 3 04:00 EDT (rig is powered on now, so it should fire). Not a finding — verified normal.

### SI141. No-cloud mesh verified end to end: all 4 devices direct TCP, relays + global discovery disabled on every probed node

**Host:** fleet · **Component:** syncthing mesh (foss-03) · **Auditor:** flow:syncthing-mesh

Live-verified 2026-08-02 ~13:35 EDT. NAS hub /rest/system/connections shows mini (CCBXYGN, connected since 07-22), rig (KDLS63N) and macbook (RYRBWQ6) all connected type=tcp-server — zero relay transports. Hub, mini node, rig native service AND the operator macbook all have globalAnnounceEnabled=False + relaysEnabled=False with static LAN addresses configured for every peer. Check syncthing-hub-mesh-direct passed in today's 10:23 run ('syncthing_hub=ok peers_direct=2/2') and was re-reproduced live. The 4th device (macbook 192.168.10.253, default folder only) is anticipated by the wiki service page ('any personal laptop/phone that joins') and is itself relay-disabled, so it is not a cloud-leak vector.

### SI142. Game-save replication verified end to end: rig backup timer alive, hub + mini 100% complete, 0 errors

**Host:** fleet · **Component:** game-saves folder (game-12 ludusavi mesh) · **Auditor:** flow:syncthing-mesh

Live-verified 2026-08-02. Hub db/status for game-saves: 23 files / 769,643 bytes, state=idle, needFiles=0, errors=0, pullErrors=0; /rest/db/completion shows both rig and mini at 100% with remoteState=valid; /rest/folder/errors is null. Rig ludusavi-backup.timer is active, last service Result=success, last run 12:03 EDT today, next 14:02 — the freshness mechanism is alive. Newest actual save content dates to Jul 28 (Selaco mapping.yaml), consistent with no gaming since then rather than a stalled pipeline. Checks game-saves-mesh-synced ('game_saves_mesh=ok files=23 rig_complete=100% state=idle') and ludusavi-backup-timer-alive both passed the 10:23 run and were re-reproduced live.

### SI143. Both reverse-proxied GUIs serve real Syncthing through Caddy; mini + rig GUI admin auth confirmed present; v2.1.2 parity across all three nodes

**Host:** fleet · **Component:** syncthing GUIs + Caddy vhosts · **Auditor:** flow:syncthing-mesh

From the mini, https://syncthing.tabaska.us/rest/noauth/health and https://syncthing-rig.tabaska.us/rest/noauth/health both return 200 (check syncthing-gui-urls also passed the 10:23 run). Mini and rig config.xml GUI blocks both carry a non-empty user + password hash (values not read), matching the documented LAN+auth posture; rig GUI is bound 0.0.0.0:8384 per the 2026-07-22 rebind for Caddy proxying. Version parity holds: hub and mini run the digest-pinned syncthing/syncthing:2.1.2 image, rig native binary reports v2.1.2 'Hafnium Hornet'. Hub versioning safety net confirmed live: staggered versioning (maxAge 2592000s = 30d) configured on both folders and Sync/.stversions exists on disk.

### SI144. Rig rejoined the mesh cleanly after its ~23h power-off and resynced to 100% with no manual intervention

**Host:** rig · **Component:** syncthing mesh resilience · **Auditor:** flow:syncthing-mesh

The rig's hub connection dates from 2026-08-01T14:25:54 — a few hours after boot 0 started (Sat 08-01 10:25 EDT, following the ~23h powered-off gap flagged in preflight). Both folders are back to completion=100 / needItems=0 for the rig peer, and hub stats show lastSeen current (13:34:49 today) with a continuous ~46h prior connection. The mesh's store-and-forward hub design absorbed the outage as intended. The rig downtime itself is out of this lane's scope (filed by the preflight; 24/7-mandate question belongs to the rig lane).

### SI145. Verified green: WAN port posture clean from true off-net vantage — only TCP 32400 answers

**Host:** fleet · **Component:** WAN edge (162.0.177.18) · **Auditor:** flow:edge-dns

Probed from seedbox (the only off-net vantage) at ~13:20 EDT 2026-08-02 against WAN IP 162.0.177.18 (obtained via mini's egress): 32400 open as intended for Plex remote access; 443, 80, 8123 (HA), and 22 all closed/filtered. Matches today's edge-wan-port-posture pass (NO_UNEXPECTED_PORTS, sec-03/edge territory).

### SI146. Verified green: public zone leaks nothing — service names NXDOMAIN at 1.1.1.1, no RFC1918 records

**Host:** fleet · **Component:** public DNS zone tabaska.us · **Auditor:** flow:edge-dns

Queried 1.1.1.1 directly for plex/immich/llm/home/ha/wiki.tabaska.us plus the apex: all return no A records publicly (internal-only resolution lives in AdGuard rewrites). Matches today's edge-public-dns-no-rfc1918 pass (ZONE_CLEAN) and edge-public-dns-www-nxdomain pass.

### SI147. Verified green: both LAN resolvers return 192.168.10.2 for tabaska.us vhosts

**Host:** fleet · **Component:** AdGuard split-horizon DNS (192.168.10.2 + 192.168.10.4) · **Auditor:** flow:edge-dns

dig against both AdGuard instances (mini .2 and NAS .4) for plex/home/git.tabaska.us: all six answers are 192.168.10.2 (mini Caddy). Consistent with today's passing dns-mini-internal, dns-nas-internal, dns-mini-external, dns-nas-external, dns-mini-unbound-upstream, mini-container-dns, and mini-container-dns-egress checks.

### SI148. Verified green: full 62-vhost Caddy sweep — zero 502/504/000, every upstream alive through the proxy

**Host:** mini · **Component:** Caddy reverse proxy (/opt/stacks/caddy) · **Auditor:** flow:edge-dns

Enumerated all 62 vhost blocks from the live Caddyfile and curled each through AdGuard->Caddy from the Mac at ~13:30 EDT: every one answered with a healthy code (200/301/302/303/307/401). No dead-upstream 502s (failure pattern #10 / drift axis 11 clean at this plane). Explained non-200s: plex 401 known-normal; marinara 401 = its auth/Host-header gate; mcpo 404 at / but /docs returns 200 (FastAPI norm); apollo/sunshine 307 login redirect; bitmagnet 301 redirect. App-body assertions passed on wiki ('Going Analogue — Homelab Manual') and retro-guide ('Feminist Retro Gaming Guide'); home.tabaska.us returns the known Next.js client-rendered shell (per Homepage quirk, not a defect).

### SI149. Verified green: live Caddyfile matches repo mirror byte-for-byte and matches the running :2019 config

**Host:** mini · **Component:** Caddy config currency + repo mirror · **Auditor:** flow:edge-dns

md5 of mini /opt/stacks/caddy/caddy/Caddyfile equals the repo mirror foss-setup/configs/docker-stack/stacks/caddy/caddy/Caddyfile (a4fb34af...), so no live-vs-repo drift on the edge config. Today's mini-caddy-live-config-current check passes (caddy_config=current), ruling out failure pattern #9 (config-edited-never-reloaded) on the proxy; mini-caddy-running also passes.

### SI150. Verified green: TLS certs healthy, ~65 days remaining; note these are per-name certs, not a wildcard

**Host:** mini · **Component:** Caddy TLS (Let's Encrypt via Cloudflare DNS-01) · **Auditor:** flow:edge-dns

openssl s_client against home.tabaska.us at 13:36 EDT 2026-08-02: CN=home.tabaska.us, notAfter Oct 6 2026 (~65 days left) — well inside Caddy's automatic renewal horizon. One observation for future sweep prompts: the Caddyfile issues individual per-vhost DNS-01 certs (SAN contains only the one name), not a shared wildcard cert as the sweep spec assumed — expiry monitoring per-name is therefore per-vhost.

### SI151. Verified green: exposed Plex is the correct claimed server — machineIdentifier matches the fleet's fixed identifier

**Host:** nas · **Component:** Plex remote access (WAN 32400) · **Auditor:** flow:edge-dns

Off-net /identity fetch from seedbox returns machineIdentifier 70ffcfbb5dc9389e315070cf3a8af99c5fb340b4 (matches the fixed identifier), claimed=1, real build 1.43.3.10793-cd55560bb. Today's edge-plex-remote-identity and edge-plex-manual-port-mapping (PLEX_MANUAL_PORT_OK) both pass. The only edge-plex failure is the version check, filed separately as a check-logic bug.

### SI152. Verified working: HA conversation pipeline answers a live query end to end (default agent)

**Host:** ha · **Component:** conversation API (/api/conversation/process) · **Auditor:** flow:ha-consumer

One cheap probe at ~13:36 EDT 2026-08-02: POST /api/conversation/process with text 'what time is it' returned response_type action_done with speech '1:36 PM' and a conversation_id — the Assist conversation pipeline is alive and answering at the consumer end via the default agent. (The rig-LLM agent path is covered separately as a monitoring-gap finding.)

### SI153. Verified working: HA frontend serves 200 through the Caddy proxy (ha-proxy-e2e green)

**Host:** ha · **Component:** ha.tabaska.us proxy path (Caddy on mini) · **Auditor:** flow:ha-consumer

Live curl from the Mac at ~13:30 EDT returned HTTP 200 through https://ha.tabaska.us, and today's 10:23 daily run has ha-proxy-e2e PASS ('<title>Home Assistant</title>' — asserts the HA frontend body, not a bare 200). This is the path that once sat 400-for-11-days (taxonomy #10, fixed under fix-32); it is healthy today.

### SI154. Verified working: 66/73 lights available; the 7 unavailable are the known wall-switched Hue set (ha-lights-available green)

**Host:** ha · **Component:** lights (Hue + Elgato entities) · **Auditor:** flow:ha-consumer

Live /api/states pull at ~13:32 EDT: 73 light entities, 66 available, 7 unavailable — all 7 match the documented chronically-unavailable wall-switched Hue bulbs (kitchen overheads/counters, basement, one vanity), which is known-normal and below the check's >12 alert threshold. Spot-checked light.elgato_a2utb50412m3fy: state off, last_changed 2026-08-02T04:43Z (real recent transition). Today's run: ha-lights-available PASS (lights_avail=ok) and ha-hue-lights PASS (73 >= 50 entities registered).

### SI155. Verified working: Hue bridge reachable from HA — Hue room group had real on/off transitions last night

**Host:** ha · **Component:** Hue bridge (IoT VLAN) · **Auditor:** flow:ha-consumer

light.living_room_living_room is a genuine Hue room group (is_hue_group=True, hue_type=room, 3 member bulbs) and the logbook shows it turning on at 2026-08-02T02:26Z and off at 02:42Z (22:26/22:42 EDT Aug 1) — real state changes flowing through the Hue bridge on the IoT VLAN within the last ~15 hours. Combined with ha-hue-lights PASS (73 entities registered), the HA→bridge path is healthy from HA's perspective.

### SI156. Confirmed: ha-assist-rig-llm-reachable recovered in today's 10:23 run (listed under 'Recovered since last run')

**Host:** ha · **Component:** ha-assist-rig-llm-reachable check · **Auditor:** flow:ha-consumer

Today's daily run (2026-08-02T10:23:08-04:00) has ha-assist-rig-llm-reachable PASS (assist_llm=ok — rig Ollama :11434 reachable and serving llama3.2:3b), and last-summary.md lists it in the 'Recovered since last run' section. The prior failure is consistent with the rig being powered off ~23h (boot gap Fri 07-31 11:07 → Sat 08-01 10:25 EDT — the rig downtime itself belongs to another lane). Backend reachability is green again; note the e2e conversation-agent gap filed separately.

### SI157. Minecraft Java verified end-to-end from the friend's seat: real status ping via public playit edge answers Paper 26.1.2

**Host:** rig · **Component:** playit (Minecraft Java tunnel) · **Auditor:** flow:game-servers

Ran the repo probe foss-setup/scripts/gaming/mc-status-ping.py from the operator Mac against the public playit edge 69.9.181.17:1105 with handshake hostname minecraft.tabaska.us — full protocol handshake+status succeeded, returning version Paper 26.1.2 with 0 players. This is the exact path a Java friend uses. Today's 10:23 verification run also passed playit-java-public on try 1/4 (task game-10), and the rig playit log shows my connection plus the hourly checks arriving as New TCP Client entries on tunnel 4234967.

### SI158. Minecraft Bedrock verified end-to-end: RakNet ping via public playit UDP edge answers with server MOTD

**Host:** rig · **Component:** playit (Minecraft Bedrock tunnel / Geyser) · **Auditor:** flow:game-servers

Ran foss-setup/scripts/gaming/mc-bedrock-ping.py from the Mac against 69.9.181.17:1111 — RakNet unconnected pong received with MOTD 'Powered by AMP', version 26.33. This traverses the same public UDP path a Bedrock player uses, the path the historical M30 UDP-claim bug severs while TCP stays green. Today's 10:23 run passed both playit-bedrock-public (try 1/4) and game-playit-bedrock-udp (PONG from 69.9.181.17), and the M30 class guard game-playit-udp-register-errors passed with 0 register errors in 24h.

### SI159. Palworld verified with a live friend connected: serverfps 59, player CroadNation online at 86ms ping

**Host:** rig · **Component:** palworld (REST :8212) · **Auditor:** flow:game-servers

Probed the Palworld REST API from the Mac over LAN using vault palworld.admin_password (key path only, value not printed): /v1/api/metrics reports serverfps 59 (avg 59.7), 1/16 players, world day 993, uptime 68781s (~19.1h, matching the container's post-boot restart); /v1/api/players shows friend CroadNation actually connected and playing right now at 85.9ms ping — the strongest possible consumer verdict. Container is Up 19 hours (healthy). Check palworld-rest-liveness (game-10) also passed at 10:23.

### SI160. Terraria verified joinable: wire handshake answers, world AnalogueCoop loaded with 8 slots, up 5 days (rode through the rig outage)

**Host:** mini · **Component:** terraria (TShock :7777) · **Auditor:** flow:game-servers

Re-ran the terraria-join-handshake check command live on mini: the real Terraria wire protocol Connect Request got a framed reply msgType=2 (version-mismatch kick, expected for the probe client string against the 1.4.5.x beta build — proves the join pipeline reached version-check). TShock REST /v2/server/status confirms world AnalogueCoop loaded, v1.4.5.6, 0/8 players, no password, uptime 5d03:36 — meaning Terraria (the only game NOT on the rig) stayed available to friends throughout the rig's 23h outage window.

### SI161. AMP panel reachable through amp.tabaska.us: 200 with login page (healthy per convention)

**Host:** rig · **Component:** amp (panel via Caddy vhost) · **Auditor:** flow:game-servers

curl from the Mac to https://amp.tabaska.us/ (Caddy vhost on mini proxying to the rig, per stacks/caddy/caddy/Caddyfile line 286) returns HTTP 200 with the 'AMP - Application Management Panel' title and login form — the login-gate response that counts as healthy. Backup-side checks game-amp-backup-fresh (BACKUP-OK age=982s) and game-amp-backup-policy (POLICY-OK) both passed at 10:23, so the H10 silent-backup-freeze regression guards are green too.

### SI162. playit agent logged two transient reconnect bursts in 24h (00:42 EDT DNS/network-unreachable ~16s; 10:19 EDT pong timeout) — self-recovered, self-heal armed

**Host:** rig · **Component:** playit agent · **Auditor:** flow:game-servers

docker logs --since 24h on the playit container shows a burst 2026-08-02T04:42:53-04:43:09Z (00:42 EDT) of 'dns error: failed to lookup address information' plus 'Network unreachable' — the rig briefly lost network/DNS overnight, worth correlating with other lanes' overnight signals — and a single 'timeout waiting for pong' reconnect at 14:19:58Z (10:19 EDT). Both self-recovered; the M30 register-error signature count is 0, playit-udp-guard.timer is active firing every 10 min (last run 13:34 EDT), and my live public probes plus the 10:23 checks all pass, so the tunnels are currently solid. Neutral observation, no action needed in this lane.

### SI163. Entire game-server check suite green at today's 10:23 run — playit public checks recovered, saves mesh synced, restic bloat guard clean

**Host:** fleet · **Component:** verification game-check suite · **Auditor:** flow:game-servers

Confirmed from mini /var/lib/verification/results.json (run 2026-08-02T10:23:08-04:00): all 12 game-related checks pass — game-saves-mesh-synced (23 files, rig 100%), game-amp-backup-fresh/policy, restic-bloat-rig, game-playit-bedrock-udp, game-playit-udp-register-errors, terraria-join-handshake/world-loaded, palworld-rest-liveness, playit-java-public and playit-bedrock-public (both on try 1/4). Per today's Healthchecks signal all 16 dead-man checks including playit-udp-rig are status=up. The game lane recovered fully after yesterday's rig outage.

### SI164. RomM library verified consistent end-to-end: 8364 roms / 8 populated platforms / ~845GB, DB healthy, share-vs-DB counts match

**Host:** mini · **Component:** romm (/opt/stacks/romm, :8998) · **Auditor:** flow:retro

Check romm-content-ingest (task fix-37) passed in today's 10:23 EDT run with ROMM_CONSISTENT files=8368 roms=8364, and I reproduced the consumer path live at ~13:40 EDT: API (authed with vault romm.admin_username/admin_password) reports 8 populated platforms (nes 3537, gba 2808, snes 786, gb 622, n64 299, wii 177, ngc 101, wiiu 34) totalling 8364 roms, 845,395,718,122 bytes. romm Up 11 days, romm-db Up 3 weeks (healthy), MARIADB_ROOT_PASSWORD confirmed set in-container (value not printed) and root DB query works, so the daily consistency check's self-contained cred path is intact. Newest DB ingest 2026-07-20 18:02 UTC (Wii Party U, wiiu) matches the newest files on the NAS share (2026-07-19 wiiu batch) — ingest lag was ~1 day when last exercised. Note: 29 additional zero-rom platforms exist in RomM mirroring empty scaffold dirs under /mnt/share/Games/romm/roms/ (3ds, psx, switch, ...) — cosmetic clutter only.

### SI165. ES-DE consumer path verified: 8 platform symlinks, 0 broken, CIFS mount to NAS games share live rw, all 6 launch cores present

**Host:** rig · **Component:** ES-DE + libretro (/home/btabaska/ROMs, /usr/lib/libretro) · **Auditor:** flow:retro

Check rig-esde-romm-library (task retro-05) passed today with ESDE-ROMM-OK roms=8332, and I reproduced live at ~13:35 EDT: /home/btabaska/ROMs holds exactly 8 symlinks (gb gba gc n64 nes snes wii wiiu) all pointing into /mnt/share/Games/romm/roms/, find -xtype l over the whole tree returns 0 broken links, //192.168.10.4/games is mounted rw via cifs vers=3.0 (systemd automount), es-de 3.4.1 (r51) is installed, and all six libretro cores the check requires (mesen snes9x mgba gambatte mupen64plus_next dolphin) exist in /usr/lib/libretro (6 .so files total). The full seedbox->NAS->RomM->rig retro chain is healthy at the consumer end.

### SI166. RomM public vhost serves app-specific heartbeat 200 through the proxy (v4.9.2, wizard done, IGDB+RA+Hasheous enabled)

**Host:** mini · **Component:** caddy edge -> romm.tabaska.us · **Auditor:** flow:retro

Probed through Caddy per the proxy-path failure pattern (#10), not just the direct port: https://romm.tabaska.us/api/heartbeat returns 200 with real app JSON — VERSION 4.9.2 (matches the compose pin rommapp/romm:4.9.2), SHOW_SETUP_WIZARD false, IGDB_API_ENABLED true, RA_API_ENABLED true, HASHEOUS_API_ENABLED true. Metadata providers configured in the repo compose (foss-setup/configs/docker-stack/stacks/romm/compose.yaml) are live and enabled at the running app.

### SI167. NAS Games share newest content is the 2026-07-19 wiiu batch; no additions in 14 days — batch-import flow idle by design, no active seedbox staging

**Host:** nas · **Component:** games share (/mnt/share/Games/romm on mini <- //192.168.10.4/games) · **Auditor:** flow:retro

Probed via mini's CIFS mount to keep NAS load off: newest files on the share are the wiiu set from 2026-07-19 15:48-15:50 (New Super Mario Bros. U, Paper Mario Color Splash, etc.), which RomM ingested the next day. No ROM staging directory is active on the seedbox home tree, consistent with ROM sets being one-time batch pulls rather than a continuous arr-style feed — this is not a zero-throughput (#13) failure, just an idle-by-design pipeline. Share also carries a RetroDECK BIOS Pack dir and romm-extras alongside the romm library tree.

### SI168. Verified green: mini stack fleet fully repo-faithful — STACK-MIRRORS-OK, MANIFEST-PURITY-OK, clean trees, etckeeper committed

**Host:** mini · **Component:** /opt/stacks + compose-image manifest + etckeeper · **Auditor:** repo:live-drift

Ran the fix-41 stack-mirror-check (both modes) live on mini from the verification cache clone, first confirming the clone HEAD equals origin/main 7adbd58 (== local Mac main, nothing unpushed either side). Every live /opt/stacks stack with a compose file is byte-mirrored in configs/docker-stack/stacks/ under the same filename and every live .env key exists in its repo .env.example (this covers axis-10 env parity for ALL mini stacks including the newest booklogr and journaling); the compose-images.txt image-name set exactly matches live composes. /opt/stacks and /opt/foss-setup porcelain 0, 0 unpushed commits, etckeeper unclean rc=1 (=clean).

### SI169. Verified green: checks.d 35/35 and coverage manifests 4/4 byte-identical repo↔deployed; mini and NAS manifests exactly match live container fleets

**Host:** fleet · **Component:** verification checks.d + coverage manifests · **Auditor:** repo:live-drift

md5sum of every file in mini /opt/verification/checks.d/ (35 yaml) and /opt/verification/coverage/ (mini/nas/rig.containers + seedbox.services) matches the repo at HEAD 7adbd58 exactly — no deploy lag on check definitions or coverage manifests. Triple-diff third leg: live docker ps on mini (46 containers) and NAS (31 containers incl -a) match their manifests with zero manifest-only and zero live-only names, so the 100%-coverage tripwire (mandate 2) is accurate on both hosts as of 2026-08-02 ~13:35 EDT.

### SI170. rig coverage manifest omits immich_machine_learning by documented design (glue-14) — internally consistent with the check, but a manifest-only audit would misread it as unmonitored

**Host:** rig · **Component:** verification/coverage/rig.containers · **Auditor:** repo:live-drift

Live rig docker ps -a shows 16 containers; rig.containers lists 15 — immich_machine_learning (Exited 143, day-window, known-normal) is the only live-only name. This is deliberate: containers-manifest-rig greps ^immich_machine_learning$ out of the LIVE listing (so listing it in the manifest would permanently fail the diff), and the in-file glue-14 comment pins its monitoring to the dedicated rig-immich-ml-window + immich-smart-search-consumer checks. Filed as info because the design is coherent and commented, but note the sweep expectation that every live service appear in the coverage manifest does not hold for this one container — anyone auditing coverage from the manifests alone must know to read the docker-fleet.yaml comment.

### SI171. Verified green: UNIT-DRIFT-OK plus all 13 non-tripwired rig unit files and all 4 mini /usr/local/sbin scripts byte-identical to repo; fleet-mcp.service matches its local-ai-tooling source

**Host:** fleet · **Component:** host systemd units (mini + rig) vs configs/host/ · **Auditor:** repo:live-drift

Ran unit-drift-check.sh live from mini (covers ansible-pull mini+rig, gpu-power-tune, export-manifests, immich-ml window units): UNIT-DRIFT-OK. Then extended beyond the tripwire to every '—' row in configs/host/rig/README.md: abs-ipod-stage, ai-stack-watchdog, nas-music-mirror, pcie-aer-monitor, playit-udp-guard (.service+.timer each), docker.service.d/10-remote-fs.conf, and user units ludusavi-backup.service/.timer — all 13 byte-identical to their canonical repo sources. The external-repo pointer holds too: /etc/systemd/system/fleet-mcp.service is byte-identical to ~/Documents/GitHub/local-ai-tooling/ops/fleet-mcp.service on rig. mini scripts tv-torrent-cleanup.sh, net-selfheal.sh, apply-static-ip.sh, lidarr-artist-monitor-reconcile.py all identical (units had 3 cosmetic drifts, filed separately).

### SI172. Verified green: 15 of 16 NAS compose stacks byte-identical to repo (incl. name-trap cases adguard-nas and beszel-agent→configs/nas/beszel); no live-only compose stacks

**Host:** nas · **Component:** /volume1/docker compose fleet vs repo mirrors · **Auditor:** repo:live-drift

Fetched every live compose under /volume1/docker/ (single sudo batch, 2026-08-02 ~13:41 EDT) and byte-compared: audiobookshelf, bazarr, bitmagnet, calibre-web-automated, diun, immich, jellyfin, komga, media-automation, mylar3, scrutiny, stash, syncthing all SAME; adguard-nas SAME vs configs/docker-stack/stacks/adguard-nas/ and live beszel-agent/ SAME vs repo configs/nas/beszel/ (both intentional name variances). The only other live top-level dirs (beets, bookshelf, lidarr, prowlarr, radarr, readarr, rreading-glasses, sonarr, soularr, whisparr) carry no compose file — they are config/data dirs for containers defined in media-automation/docker-compose.yml, so there are no unmirrored live stacks. shelfmark is the single (comment-only) DIFF, filed separately.

### SI173. Verified green: vault-lint OK; rig local-ai-tooling docker/.env keys all present in .env.example; rig chezmoi clean

**Host:** repo · **Component:** vault + .env.example parity · **Auditor:** repo:live-drift

python3 foss-setup/scripts/secrets/vault-lint.py passes (no unexplained empty keys, 14 documented exceptions). On rig, comm of key NAMES between local-ai-tooling docker/.env and docker/.env.example shows zero live-only keys, so the ai-tooling-env-example-parity contract holds live; mini-stack .env parity (incl. booklogr, journaling) is proven by STACK-MIRRORS-OK which one-way-checks every live .env key against its example. rig chezmoi diff is empty. Axis-10 territory is clean except the Mac ssh-config drift filed separately.

### SI174. Verified green: runner core is sound — stdout-only expect matching with re.M, per-check timeout overrides, acks flow, transition-only paging, and state files all behaving as designed

**Host:** mini · **Component:** checks_runner.py core mechanics · **Auditor:** repo:verification-suite

Audited checks_runner.py end to end against live state: expect regexes match proc.stdout only (stderr can't fake a pass) with re.M; per-check 'timeout:' override (fix-42) works and is used by 5 files; --tier/--host runs correctly write side files and never touch daily state; acks.json is pruned-on-load and empty today as expected; ntfy paging is transition-only with the daily reminder exception, exactly as documented; load_env_file parses KEY=VALUE without shell-sourcing (immune to the sec-12 JWT line). Both today's 10:23 daily run and the 13:01 audit-safe sweep (VERIFICATION_STATE_DIR redirect, --no-notify) produced complete, well-formed results.json/reopen-suggestions.json/last-summary.md. The fix-30 self-checks (verification-bin-refs-present, restic marker-writers, macos-junk sweep) all pass today. The verification-self layer's design intent is intact; the defects found are in individual checks and the triage layer, not the runner.

### SI175. Verified green: all three verification dead-mans up and pinging on schedule; fast tier has 2697 pings at 10-min cadence

**Host:** fleet · **Component:** verification dead-man tiers (Healthchecks) · **Auditor:** repo:verification-suite

Healthchecks API at 13:5x EDT: verification-mini up (last_ping 10:25 EDT today, recovered from the 08-01 incident), verification-quick-mini up (hourly, 561 pings), verification-fast-mini up (10-min cadence, 2697 pings, grace 25min). The quick and fast tiers ran continuously through the 08-01 daily-sweep outage (journal shows fast-tier completions every 10 min on 08-01), so crit user-facing liveness coverage never lapsed — only the daily deep sweep and triage were lost that day. Tier placement is broadly sane: fast tier carries user-facing liveness (caddy, adguard, dns, ha, plex-visibility, journaling readiness), heavyweight consumer probes stay daily, and no fast-tier check hits rate-limited externals (no Hardcover/completion-loop calls in any tier: fast cmd set is local curls and cheap API GETs).

### SI176. Flap analysis: only 3 result diffs between the two full runs today — 1 real recovery, 1 structural false positive, 1 rolling-window check; 26 failures stable

**Host:** mini · **Component:** check-fleet stability (10:23 daily vs 13:01 audit sweep) · **Auditor:** repo:verification-suite

Compared /tmp/verify-audit/sweep-run.json (13:01, 270/296) against results.json (10:23, 267/296). Zero new failures appeared in the audit sweep. Three checks failed at 10:23 but passed at 13:01: alert-healthchecks-none-down (genuine recovery — the verification-mini dead-man came back up when the 10:25 daily cycle pinged it, not a flap), spent-enabled-timers (the structural daily-run false positive filed separately), and soularr-not-crashlooping (greps 'docker logs soularr --since 2h' — a rolling 2h window, so soularr's 2 fatals before 10:23 aged out by 13:01; this check will flap by design whenever soularr emits intermittent fatals, and its underlying condition is already tracked by open-adjacent fix-40 state nas-soularr-failed-imports-fresh which failed in BOTH runs). Conclusion: the check fleet is not flappy — the 26 common failures are persistent真 signals for the other sweep lanes, and only soularr-not-crashlooping merits a window rethink (e.g. since-last-run or a counter threshold) when someone next touches docker-fleet.yaml.

### SI177. Tracker integrity verified green: counts coherent, all status ids resolve (330 = 251 done + 46 open + 18 deferred + 15 retired)

**Host:** repo · **Component:** foss-setup/scripts/verification/tracker-*.py · **Auditor:** repo:tracker-wiki

Ran both read-only tracker guards from a freshly pulled clean tree at ~13:00 EDT 2026-08-02. tracker-count-check.py returned TRACKER-COUNTS-OK and tracker-integrity.py confirmed full coherence across tasks.json/progress.json. gen-todo.py and gen-roadmap-pages.py also regenerate byte-identical output (zero git diff), so the committed todo.md and roadmap pages are current. The one caveat is scoped in a separate finding: these guards do not validate checks.d task_ids (dangling verify-06).

### SI178. 100% monitoring-coverage tripwire verified holding: coverage manifests exactly match live container sets on mini (46), nas (31), rig (15)

**Host:** fleet · **Component:** foss-setup/verification/coverage/*.containers · **Auditor:** repo:tracker-wiki

Three-way diffed live docker ps names (collected this session from all three docker hosts) against the repo coverage manifests: zero containers live-but-uncovered and zero covered-but-gone on every host — 92 containers total, all enumerated. The coverage layer is current even where service-catalog.yaml lags (bookshelf, shelfmark, whisparr, syncthing, bgutil-pot, bug-triage-evidence are all present in coverage), confirming the drift is isolated to the catalog artifact.

### SI179. Homepage tile layer verified healthy: DEAD_TILES=NONE, 62 tiles enumerated via API, tile set tracks the live fleet

**Host:** mini · **Component:** homepage (/opt/stacks/homepage) + verification/bin/homepage-tiles-resolve.py · **Auditor:** repo:tracker-wiki

Ran the deployed read-only dead-tile guard on mini (DEAD_TILES=NONE — no bare-docker-name tile points at a retired container) and pulled the full tile inventory from the source-of-truth API (:3010/api/services with Host header): 62 tiles across 11 groups, including current-generation services the catalog lacks (Shelfmark, Whisparr, Syncthing) and the bug-01 'Report a Problem' tile. Neutral observation: no tile exists for Bookshelf (the readarr replacement) or LibreSeerr (whose vhost still serves 200) — worth a curation decision when the catalog gap is fixed, since every other Requests/Media Automation service is tiled.

### SI180. Edge URL sweep green: 55 catalog vhosts probed, 51 healthy 2xx/3xx, zero 502s, only the two known-retired URLs dead

**Host:** fleet · **Component:** service-catalog URLs via mini Caddy edge · **Auditor:** repo:tracker-wiki

Probed every catalog url (curl -m 8, HTTP code) through the AdGuard->Caddy edge at ~13:10 EDT: 29x200, 1x301, 15x302, 2x303, 2x307 (login redirects = healthy per taxonomy), plex 401 (known-normal = up), marinara 401 (documented Host-header auth gate), mcpo root 404 by design with /docs returning 200 (verified). The only dead URLs are readarr and meme-review (000, both retired/decommissioned — filed under the catalog-drift finding, not as outages). No 502/504 anywhere, so no proxy-path incidents (taxonomy #10) in the catalog surface today.

### SI181. Docker cruft inventory (mini): 8.17GB reclaimable image space, 2.29GB fully-reclaimable build cache (96 entries), 9 unused volumes (838MB)

**Host:** mini · **Component:** docker engine · **Auditor:** repo:junk-deadpaths

Read-only docker system df at ~13:45 EDT: 62 images (42 active) totalling 26.29GB with 8.171GB (31%) reclaimable; 18 volumes with 9 unused holding 838.4MB; build cache 96 entries / 2.286GB, 100% reclaimable (likely meme-review + booklogr local builds). No pruning performed per read-only mandate — this is the baseline for a future tidy pass.

### SI182. Rig is cruft-clean: only 383MB reclaimable docker space, zero build cache, zero unused volumes, and no /tmp litter older than 7 days

**Host:** rig · **Component:** docker engine + /tmp · **Auditor:** repo:junk-deadpaths

docker system df on rig at ~13:45 EDT shows 18 images (16 active, the 2 inactive worth 382.7MB), 5/5 volumes active, no build cache. find /tmp -mtime +7 returned nothing. The rig accumulates none of the agent-session litter seen on mini.

### SI183. Repo junk-scan green: no broken symlinks, no tracked .DS_Store, no *.orig/*.rej/iCloud-conflict names, clean git status

**Host:** repo · **Component:** git working tree · **Auditor:** repo:junk-deadpaths

Full-tree scan at 13:45 EDT: zero broken symlinks; zero *.orig, *.rej, '* 2.*' or '._*' files; git status --porcelain empty. Six on-disk .DS_Store files exist (root, foss-setup, .claude, docs, configs, scripts) but all are untracked and covered by .gitignore line 3 (**/.DS_Store) — local-disk-only noise, no repo impact. The only zero-byte tracked files are the three hosts/cachyos inventory captures (flatpak.txt filed separately; the two cron files verified legitimately empty).

### SI184. Dead-script scan green: all 94 files under foss-setup/scripts/ have their basename referenced somewhere else in the repo

**Host:** repo · **Component:** foss-setup/scripts/ · **Auditor:** repo:junk-deadpaths

Scanned every file under foss-setup/scripts/ (94 entries across ai/backup/beszel/docs/dotfiles/gaming/ha/inventory/media/nas/network/reading/secrets/setup/uptime-kuma/verification/wiki) — for each, grep -rl of its basename across the repo excluding the file itself found at least one referencing file, so no fully-unreferenced scripts exist. Caveat: a reference can be a wiki/docs mention rather than an executable caller, so this rules out orphans but not soft-deprecated scripts; sampled gen-todo.py resolves to real callers (CLAUDE.md, README). The count includes one .DS_Store inside scripts/ (covered by the .DS_Store info finding).

### SI185. /opt/stacks live-only-dir sweep green apart from meme-review: backups+wiki are the only unmirrored dirs, frigate/recyclarr allowlist entries are defensible

**Host:** mini · **Component:** /opt/stacks · **Auditor:** repo:junk-deadpaths

Diffing live /opt/stacks (36 dirs) against repo mirror configs/docker-stack/stacks/ (35 dirs): live-only = backups and wiki (both expected allowlist) plus the syncthing/syncthing-node naming mismatch filed separately; repo-only = adguard-nas (NAS-deployed, filed separately). The check's extra allowlist entries are consistent with policy: frigate is staged-never-ran by design and recyclarr runs as a one-shot with no persistent container so the working-dir label match would false-positive. The only genuine orphan is meme-review (filed as the medium contradiction finding). No macOS ._*/.DS_Store junk at /opt/stacks top level (check reported junk=NONE).

### SI186. Seedbox home otherwise tidy and in active use: live syncthing (2 procs), current deluge-reaper tooling, no large stale artifacts beyond the docker leftovers

**Host:** seedbox · **Component:** ~ (home dir) · **Auditor:** repo:junk-deadpaths

Depth-1 home listing at ~13:50 EDT shows an actively-maintained layout: ~/scripts holds deluge-reaper.py + deluge-preimport-stuck.py (fix-25 tooling, mtime Jul 17), ~/logs has current reaper logs, ~/slskd-native active Jul 30, ~/files and ~/.session touched today (Aug 2 19:29 server time), and syncthing runs live from ~/apps/syncthing. Only junk found is the dead rootless-docker set and syncthing.old (filed separately). Light-touch ls only on the shared host.

### SI187. Verified green: the 07-31 rig outage was detected and paged within 12 minutes by two independent mechanisms — the fleet did NOT lose the host silently

**Host:** fleet · **Component:** rig outage detection (fast tier + Healthchecks dead-men) · **Auditor:** arch:topology

Natural-experiment review of 07-31 11:07 -> 08-01 10:25: the fast tier failed 13 checks and sent an ntfy page at 11:19 (12 min after poweroff), correctly spanning the blast radius (rig-llama-swap, rig-ai-e2e, journaling-coach-model-reachable, palworld-rest-liveness, playit-java/bedrock-public, ludusavi-backup-timer, syncthing mesh, rig-suspend-masked crit, rig-root-fs-writable crit). Independently, Healthchecks rig dead-men are tight enough to fire within ~35-40 min (ai-stack-rig period 600s/grace 1500s; playit-udp-rig 1200s/900s), and the verification-mini dead-man (86400/43200) caught the 08-01 daily-runner timeout and paged recovery at 08-02 10:25. Detection is healthy; the gaps are recovery latency and escalation (filed separately).

### SI188. Design map: five single-path cross-host mounts, each with a distinct kill chain and no fallback

**Host:** fleet · **Component:** cross-host mount dependency map · **Auditor:** arch:topology

Live mount inventory 2026-08-02: rig depends on NAS via CIFS //192.168.10.4/games -> /mnt/share/Games (ludusavi game saves) and //192.168.10.4/manga -> /mnt/nas-manga (Suwayomi -> Komga feed; persistent mount per read-18 requirement). mini depends on NAS via //nas/music ro -> /mnt/nas/music (Navidrome library), //nas/music rw -> /mnt/nas-music-rw (music mirror), //nas/youtube -> /mnt/nas-youtube (metube/pinchflat writes). NAS depends on seedbox via rclone fuse seedbox:/home/hd34/btabaska/files -> /volume1/mounts/seedbox-files (all torrent imports; pattern-#4 stall if it drops). NAS down therefore kills Navidrome, youtube ingestion, manga pipeline and game-save backup simultaneously; all mounts are soft/automount so failures are silent at mount level and only surface via consumer checks.

### SI189. Tailnet verified: 7 devices, direct (non-relay) paths for all active peers, no exit nodes; HA remains LAN-only by design so remote HA access dies with mini

**Host:** fleet · **Component:** tailnet posture · **Auditor:** arch:topology

tailscale status on mini and rig 2026-08-02: peers = macmini, cachyos (rig), nas, seedbox, macbook-air, ipad, iphone; all observed active links are 'direct' (seedbox direct 185.162.184.38:41641 — no relay fallback, consistent with foss-03 no-cloud posture). No exit nodes advertised. HA (192.168.10.50) is absent from the tailnet per declared design, which means remote access to HA depends entirely on being able to reach the LAN — and any future remote path would ride mini's Caddy. Rig also flags a MagicDNS health warning (systemd-resolved/NetworkManager wiring), cosmetic today since fixed IPs and the ts.net name are used. Design observation only.

### SI190. Verified green: edge TLS healthy — LE certs 65+ days from expiry via Cloudflare DNS-01; renewal SPOF is the CLOUDFLARE_API_TOKEN env on mini

**Host:** mini · **Component:** Caddy / Let's Encrypt renewal chain · **Auditor:** arch:topology

Probed three vhosts through mini Caddy on 2026-08-02: all serve valid Let's Encrypt certs (notAfter Oct 6 / Oct 21 2026, 65-80 days margin). The Caddyfile local_tls snippet confirms per-site DNS-01 via 'dns cloudflare {env.CLOUDFLARE_API_TOKEN}', so LAN-only vhosts renew without inbound ports. The renewal chain's single points: one Cloudflare API token in Caddy's env (scope hardening = open task sec-09) and Cloudflare NS delegation. No action needed now; a cert-days-left check exists in the edge flow.

### SI191. Verified green: DNS is NOT a mini SPOF — NAS runs a second resolver answering for *.tabaska.us and clients carry both

**Host:** fleet · **Component:** LAN DNS redundancy · **Auditor:** arch:topology

Both 192.168.10.2 (mini AdGuard) and 192.168.10.4 (NAS AdGuard, vault section adguard_nas) authoritatively answer forgejo.tabaska.us -> 192.168.10.2, and the operator Mac's resolver list includes both plus the router. This softens the mini-SPOF picture for name resolution specifically: with mini down, LAN clients still resolve (though every *.tabaska.us answer points at the dead mini Caddy, so HTTPS service is still lost — resolution survives, reachability does not).

### SI192. Verified green: export-manifests-rig 152h-old ping is normal — weekly Monday schedule with 24h grace

**Host:** rig · **Component:** Healthchecks export-manifests-rig · **Auditor:** arch:topology

Preflight flagged export-manifests-rig last_ping 152h old. Verified via the Healthchecks API: the check is cron-scheduled '0 4 * * 1' (Mondays) with grace 86400 and last pinged Mon 2026-07-27 08:09 UTC; next expected Mon 2026-08-03, status 'up'. Not stale — do not file. export-manifests-mini (last ping Jul 28) fits the same weekly cadence.

### SI193. Apollo game-streaming host verified serving — apollo.service active, Moonlight ports 47984/47989/48010 listening

**Host:** rig · **Component:** apollo.service (game streaming) · **Auditor:** gap:apollo-streaming

The one chain-matrix cell with zero lane findings, probed by the orchestrator: apollo.service (system unit) is active/running since the 08-01 boot and all three Moonlight/GameStream ports are listening on 0.0.0.0. The companion moondeckbuddy user unit is crash-looping (separate finding). No functional streaming-session probe exists (adjacent to the known BedrockConnect-style coverage gap class).
