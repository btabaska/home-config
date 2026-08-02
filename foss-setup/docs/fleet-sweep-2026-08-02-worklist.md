# Fleet-sweep worklist — 2026-08-02 — root-cause clusters

> Generated from `docs/fleet-sweep-2026-08-02.json` (318 findings) by clustering into
> root-cause work items. Each item = one `fix-NN` task in `tasks.json` = **one Claude Code
> session**. Drive with `/resolve-finding fix-NN`. Work top-down by wave; within a wave, order is flexible.
> 193 info-level findings are green confirmations/observations and intentionally have no task; 5 findings are covered by already-open tasks (`known-issue`) and get no new task — but note the sec-12 cluster (SH3) materially escalates that open task's urgency.

**21 work items** covering all 120 actionable findings (2 critical · 19 high · 58 medium · 46 low, minus 5 known-issue).

| id | sev | host | wave | title | # |
|----|-----|------|------|-------|---|
| `fix-49` | 🔴 critical | mini | 0 | Navidrome total library wipeout: bad .ndignore written by the fix-28 guard + one empty-root CIFS scan flagged  | 1 |
| `fix-50` | 🔴 critical | nas | 0 | Bitmagnet DHT junk-grab storm: arrs re-grabbing owned titles hourly, foreign-audio junk imported into the libr | 3 |
| `fix-51` | 🟡 medium | mini | 1 | LAN exposure batch: rogue nc -lvnp 9999 listener on mini (17 days), ~85 fleet ports on 0.0.0.0 bypassing Caddy | 3 |
| `fix-52` | 🟠 high | seedbox | 1 | Seedbox Syncthing: syncs nothing (0 folders, 0 peers, 0 bytes ever) while its plaintext-HTTP GUI is open to th | 1 |
| `fix-53` | 🟡 medium | nas | 1 | File-permission regressions: mylar3 writes 0644 secret-bearing config + world-writable cache (fix-23 regressio | 3 |
| `fix-54` | 🟠 high | seedbox | 2 | Movies/TV import stall: torrent payloads deleted under live torrents, move_completed wedge, 3-4 day arr retry  | 8 |
| `fix-55` | 🟠 high | nas | 2 | NAS chronic I/O pressure + SQLite 'database is locked' storm degrading 5 arr apps, killing soularr, hanging do | 7 |
| `fix-56` | 🟡 medium | nas | 2 | Music acquisition hygiene: soularr failed-import backlog cycling, junk MusicBrainz albums grinding every 5 min | 3 |
| `fix-57` | 🟠 high | nas | 2 | Books request layer broken-quiet: last successful request 07-20, 12/30 libreseerr requests errored, one grabbe | 4 |
| `fix-58` | 🟠 high | nas | 2 | Manga chain silently severed at BOTH ends: Komga scheduler scans a deleted library-id (279 new chapters invisi | 6 |
| `fix-59` | 🟠 high | nas | 2 | Bazarr has ZERO subtitle providers enabled — 2868 wanted episodes can never fetch while the check stays green  | 1 |
| `fix-60` | 🟡 medium | nas | 2 | Immich cluster: nightly ffmpeg segfault on one corrupt .mov (5 nights), second household user has 0 photos eve | 5 |
| `fix-61` | 🟠 high | mini | 3 | Verification framework repair: daily run killed by its own 30-min timeout mid-incident (dead-man dark, no self | 9 |
| `fix-62` | 🟠 high | fleet | 3 | Check quality + coverage batch: 4 structurally-broken checks (plex-version, stash auth, immich-backup 60s find | 10 |
| `fix-63` | 🟠 high | mini | 3 | Alerting-plane architecture: everything that could report a mini outage lives ON mini; rig auto-recovery only  | 5 |
| `fix-64` | 🟠 high | rig | 3 | Rig host stability: 27h operator poweroff (power key honored on a 24/7 host), RTC 4h skew corrupting timelines | 11 |
| `fix-65` | 🟠 high | rig | 3 | Config control-plane drift: local-ai-tooling Forgejo 16 commits behind (ai-03 regression), ansible perpetual c | 8 |
| `fix-66` | 🟠 high | mini | 3 | mini cannot reach the IoT VLAN: journaling docker bridge 192.168.16.0/20 swallows 192.168.20.0/24 (net-05 regr | 3 |
| `fix-67` | 🟡 medium | mini | 3 | Small-pipeline regression batch: kometa IMDb 403s (29 errors), pinchflat bot-check strandings, CWA cover, edit | 8 |
| `fix-68` | 🟠 high | repo | 4 | Tracker/docs truth repair: 20 done tasks failing checks with zero formal reopens, wiki-drift from a same-commi | 11 |
| `fix-69` | 🟡 medium | fleet | 4 | Fleet hygiene batch: meme-review check-vs-policy contradiction, log floods (synologand 7k, deluged 1.1/s, ufw) | 10 |

## Wave 0 — active incidents (do first)

### `fix-49` 🔴 Navidrome total library wipeout: bad .ndignore written by the fix-28 guard + one empty-root CIFS scan flagged all 3495 tracks missing

*host:* mini · *track:* media-pipeline · *severity:* critical

Since 2026-08-01 05:18 every track in Navidrome is greyed out/unplayable (missing=3495/3495, library root itself flagged missing): the hourly quick scan observed the CIFS root as empty and quick scans can never un-miss files; compounding it, /mnt/nas/music/.ndignore (written Aug 1 05:00 by the fix-28-era guard) contains '#recycle' which is a gitignore COMMENT, not a pattern. Fix the guard to write a real pattern, run a full scan (-f) to clear missing flags, and harden the scanner against transient empty-mount reads (mount-gate the scan). fix-28 regression.

**Resolves 1 findings:** `SC1` Entire Navidrome library (3495/3495 tracks) flagged missing 

### `fix-50` 🔴 Bitmagnet DHT junk-grab storm: arrs re-grabbing owned titles hourly, foreign-audio junk imported into the library today; indexer also timing out via Prowlarr

*host:* nas · *track:* media-pipeline · *severity:* critical · ⚠️ disruptive — removes wrongly-imported library files + changes indexer config; 4-7AM window + operator approval for deletions

Every recent grab in radarr (hourly) and sonarr (every ~30min) is from the Bitmagnet (DHT) indexer: junk re-releases of already-owned titles (MegaPeer/seleZen re-encodes, RUS/MULTi dubs), some of which imported into the movie library TODAY — active library pollution plus wasted seedbox bandwidth. Simultaneously Bitmagnet is failing/timing out through Prowlarr (>6h, seed-12 regression) and its dedicated check dies at the 60s runner budget with unbounded inner curls. Rein in the indexer (quality/seeders profiles, or demote from RSS/auto-grab), purge today's junk imports, and give the check a realistic budget. Also the top steady I/O consumer on the NAS — coordinate with fix-55.

**Resolves 3 findings:** `SC2` Active Bitmagnet-DHT junk-grab storm: arrs re-grab owned tit, `SM6` Bitmagnet indexer failing through Prowlarr for >6h — corrobo, `SM27` bitmagnet-torznab-via-prowlarr TIMEOUT verified: searches ta

**✅ RESOLVED 2026-08-02** — Bitmagnet demoted to interactive-only via a new Prowlarr App Sync Profile `Interactive-Only (fix-50)` (RSS+auto off, propagated to radarr+sonarr); 9 foreign-audio junk imports purged from the movie library (file+record deleted, release blocklisted) + 9 junk queue grabs blocklisted/removed; radarr immediately re-grabbed CLEAN English copies from IPTorrents/OnlyEncodes (self-healed). SM6/SM27: `bitmagnet-torznab-via-prowlarr` time-boxed (`timeout:90`, inner curls `-m`) — now completes in ~11s reporting true state. New checks: `bitmagnet-demoted-interactive-only` (regression) + `arr-grab-source-not-storming` (class). See commit + progress.json.


## Wave 1 — security / exposure

### `fix-51` 🟡 LAN exposure batch: rogue nc -lvnp 9999 listener on mini (17 days), ~85 fleet ports on 0.0.0.0 bypassing Caddy auth, BookLogr registration still open

*host:* mini · *track:* security · *severity:* medium

An orphaned 'nc -lvnp 9999' has been listening on 0.0.0.0 on mini for 17 days (likely leftover from a debug session — identify provenance, kill, and add a listener-drift check). The wider posture: ~30 mini + ~20 rig + ~35 NAS service ports bound to 0.0.0.0 on the flat LAN, including unauthenticated GPU/AI endpoints whose only auth lives in Caddy — direct-port access bypasses it. BookLogr registration remains OPEN (AUTH_ALLOW_REGISTRATION=True), the planned lockdown never executed. Define the intended-exposure baseline, close the accidental ones, codify as a check.

**Resolves 3 findings:** `SM56` Orphaned 'nc -lvnp 9999' listening on 0.0.0.0 for 17 days on, `SM58` Flat-LAN exposure: ~30 mini + ~20 rig + ~35 NAS service port, `SM24` BookLogr registration still OPEN (AUTH_ALLOW_REGISTRATION=Tr

### `fix-52` 🟠 Seedbox Syncthing: syncs nothing (0 folders, 0 peers, 0 bytes ever) while its plaintext-HTTP GUI is open to the public internet

*host:* seedbox · *track:* security · *severity:* high

The seedbox syncthing process is pure dead weight — zero folders beyond the default stanza, zero peers, zero lifetime bytes — yet its GUI listens on all interfaces and is reachable from the public internet at betty.bysh.me:12104 over plaintext HTTP. Either retire it or wire it properly into the foss-03 mesh with loopback/tailnet-only binding + auth. Adjacent to open task sec-04 (seedbox hardening) but not covered by it.

**Resolves 1 findings:** `SH5` Syncthing syncs nothing (0 folders, 0 peers, 0 bytes ever) y

### `fix-53` 🟡 File-permission regressions: mylar3 writes 0644 secret-bearing config + world-writable cache (fix-23 regression), HA offsite tars group-writable to every NAS group

*host:* nas · *track:* security · *severity:* medium

The Jul 27 mylar3 deploy reintroduced the fix-23 failure class: config.ini (23 credential-class keys, currently empty values) is 0644 and app-rewritten so chmod alone regresses within hours, plus 5 world-writable cache/ComicTagger files — fix the container umask/PUID at source and re-green nas-secret-file-perms (crit) + nas-worldwritable-sweep. Separately the HA offsite backup tars on /volume1/backups grant write+delete to every NAS group including http and household.

**Resolves 3 findings:** `SM2` nas-secret-file-perms crit failure = mylar3 config.ini mode , `SM3` nas-worldwritable-sweep=5: all five world-writable paths are, `SM42` HA offsite backup tars grant full write+delete to every NAS 


## Wave 2 — broken user-facing pipelines

### `fix-54` 🟠 Movies/TV import stall: torrent payloads deleted under live torrents, move_completed wedge, 3-4 day arr retry loops, sample files back in the library

*host:* seedbox · *track:* media-pipeline · *severity:* high · ⚠️ disruptive — removes wedged torrents/queue records and deletes junk sample files; 4-7AM window + operator approval

Sonarr has been retrying 'path does not exist' every few minutes for 3-4 days on two grabs whose payloads no longer exist on seedbox disk despite deluge showing 'Seeding 100%' (investigate what deleted them — deluge-reaper and the 88%-consumed user quota, real headroom only ~321G, are suspects); HotD S02E07 is wedged with move_completed never fired; radarr holds 9 stale stuck records; Leverage S05 sample-file imports are back (fix-27 regression); radarr also churns ffprobe failures on a PAL file. Clear the wedges, root-cause the payload deletion + quota pressure, restore preimport-reaper coverage, and make the arr queue self-clean stale records. Regressions of fix-25/fix-27/verify-06.

**Resolves 8 findings:** `SH2` Sonarr stuck=16 classified: two grabs from Jul 29-30 never m, `SH9` Sonarr queue wedged unrecoverably: 2 torrents 'Seeding 100%', `SM4` Radarr stuck=9 classified: 6 stale 'not an upgrade' decision, `SM26` HotD S02E07 wedged at 100% in state=Downloading since Jul 30, `SM28` Preimport-stuck set churned hard since 10:23: 5 of the named, `SM17` User quota 88% consumed (2541G of 2862G soft / 2909G hard) —, `SL3` Radarr repeatedly failing ffprobe/mediainfo on a Professor L, `SL17` media-arr-file-quality bad=3: Leverage S05E01/E04/E05 librar

### `fix-55` 🟠 NAS chronic I/O pressure + SQLite 'database is locked' storm degrading 5 arr apps, killing soularr, hanging docker CLI and healthchecks

*host:* nas · *track:* nas-foundation · *severity:* high · ⚠️ disruptive — may restart NAS DB-backed containers; 4-7AM window

Every NAS arr except sonarr logs recurring 'database is locked' (lidarr: 1254 errors in 30h) failing scheduled tasks and 500ing APIs; soularr crash-exits on those 500s (verify-06 regression), mini's lidarr reconcile unit flaps on them, CWA's 3s container healthcheck fails streak-7, and docker CLI operations (logs/system df) hang for minutes. The sweep measured 78% iowait load 15-20 at 13:2x (partly self-inflicted) but the chronic baseline is real, with bitmagnet the top steady consumer. Measure per-container blkio quietly, relocate/throttle the hogs, tune SQLite busy-timeouts where exposed, and add an I/O-pressure check.

**Resolves 7 findings:** `SH1` Recurring 'database is locked' across 5 arr apps — scheduled, `SH10` Lidarr SQLite 'database is locked' storm — 1254 errors in 30, `SM35` NAS is I/O-saturated (load 15-20, 78.6% iowait) with no scru, `SM31` docker logs calibre-web-automated hangs indefinitely (--sinc, `SM52` NAS 'docker system df' hung past a 2-minute timeout — docker, `SM10` CWA container marked unhealthy (healthcheck exceeds its 3s t, `SM11` lidarr-artist-monitor-reconcile flaps: 10 failures in 7 days

### `fix-56` 🟡 Music acquisition hygiene: soularr failed-import backlog cycling, junk MusicBrainz albums grinding every 5 minutes, 3 albums stuck partial

*host:* nas · *track:* media-pipeline · *severity:* medium

Soularr's failed-import backlog has grown to 6 permanently-skipped albums with Camera + Heat Waves cycling past the staleness threshold (fix-40 regression); three junk Chinese-titled MusicBrainz albums monitored under Charli xcx make soularr grind and fail every 5-minute cycle; lidarr holds 2 importFailed album grabs (one 5 days old) and 3 albums stuck partial (fix-28 regression). Clean the wanted list, unmonitor/replace the junk MB entries, drain the backlog. Depends on fix-55 (DB-locked storm) for the underlying 500s.

**Resolves 3 findings:** `SM7` Lidarr queue: 2 importFailed album grabs, one stuck 5 days (, `SM29` Soularr failed-import backlog has grown to 6 albums permanen, `SM30` Three junk Chinese-titled MusicBrainz albums monitored under

### `fix-57` 🟠 Books request layer broken-quiet: last successful request 07-20, 12/30 libreseerr requests errored, one grabbed book lost pre-import for 13 days

*host:* nas · *track:* reading · *severity:* high

Libreseerr shows 12 of 30 requests in error state and the last SUCCESSFUL request was 2026-07-20 — the 07-28 user session failed 6/6 on Hardcover lookups; 'Adrift' (K.T. Konkoly) sits 100% complete in the deluge bookshelf label for ~306h with zero trace in Bookshelf or Calibre (lost import from the bmig-05 migration day); 'The Rotten Romans' is wanted-monitored with no forward progress for 13 days; the Kobo sync payload also carries a stray bare-string element for both devices. Restore request→grab→import flow end to end and recover the lost book. Regressions adjacent to fix-26/books pipeline.

**Resolves 4 findings:** `SH11` Grabbed book 'Adrift - K. T. Konkoly' 100% complete, parked , `SM5` Libreseerr: 12 of 30 requests in error state; last successfu, `SL19` 'The Rotten Romans' is the sole wanted-missing book, monitor, `SM32` Kobo sync payload for BOTH devices contains a stray bare-str

### `fix-58` 🟠 Manga chain silently severed at BOTH ends: Komga scheduler scans a deleted library-id (279 new chapters invisible 6 days) and Suwayomi's bind raced the CIFS mount into an empty view

*host:* nas · *track:* reading · *severity:* high · ⚠️ disruptive — Komga library-id surgery + container restart ordering changes on rig; 4-7AM window

Komga's scheduler resolves 'Manga' to the pre-read-18 library id deleted at re-homing — every 6h it errors 'Library does not exist' (28x/week) while the real library got ZERO scans, leaving 279 downloaded chapters invisible to readers for 6 days. On rig, the 08-01 boot started suwayomi 5s BEFORE mnt-nas-manga.mount, so the container captured the empty pre-mount dir (rprivate) — its downloads view is empty and new chapter downloads would miss the NAS. Also 63x HTTP 500 thumbnail errors from orphaned .tmp cache entries, and 16/19 in-library manga have 0 chapters downloaded under the current policy. Fix the scheduler id, add mount-ordering (After/BindsTo remote-fs) to the container unit, rescan, deepen the too-shallow chain checks (series>=1 / mount-touch thresholds).

**Resolves 6 findings:** `SH12` Komga Manga library has NEVER been periodically scanned — sc, `SH13` Suwayomi container raced the CIFS mount at 08-01 boot — bind, `SM21` Suwayomi library thumbnails broken: 63x HTTP 500 across 19 m, `SL16` Suwayomi logging recurring thumbnail FileNotFoundException (, `SL20` 16 of 19 in-library manga have 0 chapters downloaded — compl, `SM34` Manga-chain checks green while both ends of the chain are br

### `fix-59` 🟠 Bazarr has ZERO subtitle providers enabled — 2868 wanted episodes can never fetch while the check stays green (media-12 regression)

*host:* nas · *track:* media-polish · *severity:* high

enabled_providers=[] live, /api/providers returns empty, and download history total=0 — no subtitle has ever been fetched in this deployment, against a wanted backlog of 2868 episodes + 27 movies. The green bazarr-synced-from-arrs check only asserts arr-sync liveness, the exact mandate-1 gap. Re-enable/configure Podnapisi (the chosen sole provider), verify one real subtitle lands beside media, and extend the check to assert provider-count>=1 + recent download throughput.

**Resolves 1 findings:** `SH7` Bazarr has ZERO subtitle providers enabled — 2868 wanted epi

### `fix-60` 🟡 Immich cluster: nightly ffmpeg segfault on one corrupt .mov (5 nights), second household user has 0 photos ever, bogus 4501 date tops the timeline, pg-dumps unrotated

*host:* nas · *track:* photos · *severity:* medium

immich_server's bundled ffmpeg dumps a 23MB core at 00:00 EVERY night on the same 2021 IMG_3674.mov (fix-45 regression — quarantine or repair the asset and stop the infinite retry); the second household user (Kaelyn) has 0 photos/0 videos ever — her phone backup never flowed and no check can catch a per-user zero (add one); one asset with fileCreatedAt 4501-01-01 permanently tops date-descending views; pg dumps accumulate ~254MB/day with no observed rotation; newest asset overall is 3+ days old (watch the trend). fix-35/fix-45 adjacent regressions.

**Resolves 5 findings:** `SM1` immich_server ffmpeg segfaults every night at 00:00 on the s, `SM36` Second household Immich user has 0 photos and 0 videos ever , `SL5` One Immich asset carries a bogus future capture date (fileCr, `SL22` Zero new photo uploads in the last 3+ days (newest asset 202, `SL29` Immich pg dumps accumulate with no observed rotation (~254MB


## Wave 3 — service & infra repair

### `fix-61` 🟠 Verification framework repair: daily run killed by its own 30-min timeout mid-incident (dead-man dark, no self-page), triage 91% nonfunctional, chronic false-positive + flapping checks

*host:* mini · *track:* verification · *severity:* high

On 08-01, the daily sweep was killed by TimeoutStartSec=30min mid-LLM-triage during the rig outage — the dead-man ping was skipped (verification-mini dark ~12h), no OnFailure alert existed, and this morning's crit was the (correct) delayed self-detection. LLM triage returned malformed-JSON fallbacks for 68/75 verdicts over 5 runs while its e2e guard passes, and its 15-verdict cap is file-ordered so the day's only crit got no verdict. spent-enabled-timers false-positives on verification.timer during every daily run (5 lanes filed it); the healthchecks Django banner pollutes check output; fast-tier crit checks flapped 8+ page/recover cycles overnight (29 pages in 12h = alert fatigue); the reopen bridge is write-only (its documented consumer doesn't exist) and 22 checks carry a nonexistent task_id (verify-06). Raise/split the unit timeout, add OnFailure paging (after sec-12), fix triage parsing + crit-first capping, de-flap with retries, repair the two false-positive checks, wire the bridge into the session-start protocol for real. Regressions of fix-30/fix-39/sec-03.

**Resolves 9 findings:** `SH8` Aug 1 daily verification sweep silently died on its 30-min g, `SH15` Aug 01 daily verification run timed out (30min cap) during L, `SH17` LLM auto-triage 91% nonfunctional (68/75 verdicts are malfor, `SM22` spent-enabled-timers chronically false-positives on verifica, `SM46` Django 5.2 shell auto-import banner ('18 objects imported au, `SM23` Crit-severity fast-tier checks flap: 8+ page/recover cycles , `SM38` Alert-fatigue flapping: ~29 pages in 12h on the verification, `SM47` The reopen bridge is write-only in practice: docs claim 'the, `SM50` 22 checks carry task_id verify-06 which does not exist in ta

### `fix-62` 🟠 Check quality + coverage batch: 4 structurally-broken checks (plex-version, stash auth, immich-backup 60s find, esde), Stash no-op self-heal page storm, liveness-only quartet, filed monitoring gaps

*host:* fleet · *track:* verification · *severity:* high

edge-plex-version-current greps the XML declaration so it alarms forever while Plex is actually current (fix-24 'regression' is a check bug); stash-serving 401s (Stash gained auth ~07-22) with empty diagnostics — the app is healthy and effectively unmonitored since, while a mislocated self-heal 'compose up' no-op paged homelab-alerts every 15min for 8.5h; nas-immich-backup-freshness runs a 7-minute find against a 60s budget (flagship photo signal permanently dark — backups verified healthy by hand); rig-esde-romm-library omits wiiu and can't detect single-platform loss; immich smart-search crit check has zero timeout margin; paperless/wallabag/mealie/tautulli remain bare liveness probes; OWUI knowledge API shows populated collections as empty and wiki-rag-sync never re-verifies attachment (needs a retrieval-level check); HA /api/conversation/process and BedrockConnect have zero functional coverage (both paths verified working this sweep). One session: fix the broken five, relocate+fix the self-heal semantics with backoff, deepen the quartet, add the two missing e2e checks.

**Resolves 10 findings:** `SM8` edge-plex-version-current is structurally broken — grep pick, `SM9` stash-serving check fails with empty output because Stash no, `SM55` Stash self-heal is a no-op loop paging every 15 minutes: 'co, `SH14` nas-immich-backup-freshness check is dead (find cannot compl, `SL21` Smart-search crit check has zero timeout margin: an identica, `SL32` rig-esde-romm-library check omits the live wiiu platform fro, `SL35` mini-paperless / mini-wallabag / mini-mealie / mini-tautulli, `SM44` No e2e check for /api/conversation/process — Assist rig-LLM , `SM45` BedrockConnect console-player path has ZERO verification cov, `SL46` OWUI knowledge API renders populated collections as empty (f

### `fix-63` 🟠 Alerting-plane architecture: everything that could report a mini outage lives ON mini; rig auto-recovery only in the daily tier; ntfy history 12h; no alert-delivery proof

*host:* mini · *track:* ops · *severity:* high

ntfy, Healthchecks, Uptime Kuma, and all three verification tiers are co-located on mini together with Caddy (sole TLS edge), primary DNS and the Forgejo deploy remote — mini down means no https, no DNS, and no alert can say so. Rig-down detection is 10 minutes but WoL recovery lives only in the daily tier (up to 24h latency); ntfy's cache retains ~12h so incident history evaporates; the only published Kuma status page is an empty placeholder; and nothing proves a page ever reaches a device (mandate-2 gap). Design an off-mini dead-man (external Healthchecks-style or phone-native), move/extend WoL self-heal to the fast tier, extend ntfy retention, publish a real status page, and add an operator-confirmed alert-delivery drill.

**Resolves 5 findings:** `SH19` Entire alerting/observability plane co-located on mini with , `SM54` Rig auto-recovery (WoL) only exists in the daily tier — dete, `SL45` ntfy message cache retains only ~12h — alert history for any, `SL23` Kuma's only published status page 'test' is an empty placeho, `SM39` Monitoring gap: no synthetic alert-reached-a-device test — d

### `fix-64` 🟠 Rig host stability: 27h operator poweroff (power key honored on a 24/7 host), RTC 4h skew corrupting timelines, boot-race + catch-up failures, crash-loop and segfault batch

*host:* rig · *track:* ops · *severity:* high · ⚠️ disruptive — logind/RTC changes + possible rig reboot; 4-7AM window

The 27h outage was a clean plasma-shutdown poweroff — logind still honors power-key/desktop shutdown on a 24/7-mandate host (inhibit or redirect it); the RTC held time 4h off so the next boot's journal lied until NTP stepped (fix set-local-rtc/UTC + timer ordering after time-sync); post-step catch-up ran the ML night-window unit in daytime and failed the playit self-heal start. Batch the rest: moondeckbuddy crash-looping every 10s for weeks (76k+ restarts, missing AppImage), avahi hostname-conflict storm (1856/boot, cachyos.local broken), containerd-shim SIGSEGV killed lumiverse once, palworld segfaulted twice in 4 days, UFW block-flood noise, 3-reboots-in-7-days pattern review. Also decide the operator protocol: powering the rig off must be announced/gated.

**Resolves 11 findings:** `SH4` Rig dark ~27h (Fri 07-31 11:07 → Sat 08-01 ~14:26 real EDT):, `SM12` 3 reboots in 7 days: 07-25 was an abrupt crash-like end; 07-, `SM53` Rig 23h outage root cause: physical power-key press — logind, `SM33` Rig booted 2026-08-01 with clock 4h behind (RTC held local t, `SM13` containerd-shim SIGSEGV ('fatal error: fault') killed lumive, `SM14` moondeckbuddy crash-looping every ~10s for weeks — AppImage , `SM15` avahi hostname-conflict storm: 1,856 conflicts this boot, mD, `SM25` Palworld server segfaulted (SIGSEGV) 2026-08-01 ~18:32 EDT; , `SL9` PalServer segfaulted twice in 4 days (07-29 19:27, 08-01 18:, `SL10` Persistent timer catch-up ran the NIGHT(on) unit at 14:26 in, `SL12` UFW BLOCK flood: 8,220 kernel log lines this boot, including

### `fix-65` 🟠 Config control-plane drift: local-ai-tooling Forgejo 16 commits behind (ai-03 regression), ansible perpetual changed=1 root-caused, Mac ssh-config 3-layer drift where an apply would delete live aliases

*host:* rig · *track:* ops · *severity:* high

local-ai-tooling's Forgejo remote is a strict 16 commits behind GitHub (the whole ai-10 body of work exists only on the cloud remote — push both, and consider a pre-push/tripwire hardening beyond the existing check); ansible-site-converged-mini's perpetual changed=1 is the chezmoi task's creates: guard checking /root while running as btabaska (fix the guard, un-red fix-42's check); the Mac ~/.ssh/config is a 3-layer drift where a blanket chezmoi apply would DELETE the live rig/rig-code/forgejo aliases (reconcile source vs live NOW before an accidental apply); dotfiles GitHub origin 2 behind Forgejo (inverse gap); /opt/stacks .gitignore's top-level dir-exclude defeats the n8n workflow-source negation (workflow source silently unversioned); rig flatpak.txt inventory is zero bytes vs 8 live apps; rig manifest loop degraded (pkglist lookup failing every run + export-manifests stale 152h on its Healthchecks slot).

**Resolves 8 findings:** `SH16` local-ai-tooling Forgejo remote is 16 commits behind HEAD/Gi, `SM40` ansible-site-converged perpetual changed=1 root-caused: chez, `SM41` Mac ssh-config three-layer drift: live config (tailnet + for, `SL8` ansible-site-converged-mini changed=1 is solely the known-no, `SL28` dotfiles GitHub origin is 2 commits behind Forgejo — inverse, `SL15` Top-level 'journaling/n8n/' dir-exclude defeats the '!n8n/*., `SL39` Tracked rig flatpak inventory is zero bytes while the live r, `SM16` Rig manifest loop degraded: ansible-pull non-convergent (cha

### `fix-66` 🟠 mini cannot reach the IoT VLAN: journaling docker bridge 192.168.16.0/20 swallows 192.168.20.0/24 (net-05 regression) + HA appliance 3-min overnight network loss

*host:* mini · *track:* smart-home · *severity:* high

net-trusted-to-iot-reachable's 'tok=BAD' is a routing failure, not auth: the journaling stack's docker bridge claimed 192.168.16.0/20 which contains the IoT subnet 192.168.20.0/24, so mini routes Hue-bridge traffic into the bridge and every IoT probe from mini dies while HA (different host) controls the lights fine. Recreate the network with a non-overlapping subnet (mind the sys-docker-subnet-squat=3 check, adjacent to open task ha-19) and re-green net-05. Also: HA lost all network for ~3 minutes overnight (00:40-00:43, self-recovered — watch for recurrence) and core 2026.7.2→.7.4 + HAOS 18.1→18.2 updates are pending.

**Resolves 3 findings:** `SH6` mini cannot reach the IoT VLAN: journaling docker bridge 192, `SL13` HA appliance lost all network for ~3 minutes overnight (00:4, `SL14` Update posture note: core 2026.7.2 -> 2026.7.4, HAOS 18.1 ->

### `fix-67` 🟡 Small-pipeline regression batch: kometa IMDb 403s (29 errors), pinchflat bot-check strandings, CWA cover, edited-memo journaling hole, bug-intake residue, syncthing hub inotify, Terraria tile

*host:* mini · *track:* media-polish · *severity:* medium

Seven small independent regressions/holes, one session: kometa's 29 run errors are 7 IMDb list fetches 403-blocked (fix-37 regression — auth/UA or replace the lists); pinchflat has a new bot-check-stranded video beyond the accepted 7 (id 3076, abandoned since 07-20, fix-37 regression); 'Wuthering Heights' lacks a cover on disk and on the Kobo shelf (fix-38 regression); a #journal tag added by EDIT is silently never analyzed (memo 36 permanently unprocessed — n8n only triggers on create); stale synthetic bug-intake issue #14 open since 07-27 with no residue sweeper and the ntfy 'bugs' notify branch has zero coverage; the NAS syncthing hub's inotify watcher is dead on game-saves (periodic-scan only); Terraria has no Homepage tile.

**Resolves 8 findings:** `SM19` Kometa run errors (29) are a single root cause: 7 IMDb list , `SM20` New pinchflat media item stuck on YouTube bot-check beyond t, `SL4` cwa-library-covers nocover=1 identified: book id 99 'Wutheri, `SM37` A #journal tag added by editing a memo after creation is sil, `SL25` Stale synthetic probe issue #14 open since 2026-07-27 — e2e , `SL27` Real-report notify branch (ntfy 'bugs') has zero monitoring , `SL30` Hub filesystem watcher dead on game-saves: 'failed to set up, `SL24` Terraria server (Up 5 days) has no Homepage tile while sibli


## Wave 4 — hygiene & drift batches

### `fix-68` 🟠 Tracker/docs truth repair: 20 done tasks failing checks with zero formal reopens, wiki-drift from a same-commit violation, catalog lagging 6 live services, stale-path/plan-era prose

*host:* repo · *track:* wiki · *severity:* high

The tracker asserts 20 done tasks closed while their checks fail (the sweep's regression ledger — this queue reopens them as fix-49..69; add the missing process: formal reopen annotations in progress.json); wiki-drift is red because ai-04's commit 554c560 added a check without regenerating (re-run generators, recommit, and consider a pre-push hook); service-catalog.yaml misses 6 live services and still lists retired readarr as live with a dead URL; README still narrates the 10-stack plan era vs 46 live containers; ~/Documents/Home persists in 8 places across 4 wiki pages; rig README still calls local-ai-tooling GitHub-only (superseded); syncthing hub compose header still documents relays as a 'harmless fallback' contradicting the hardened posture; plus cosmetic unit-file drift and the syncthing-node/adguard-nas mirror-naming traps. wiki-05 regression.

**Resolves 11 findings:** `SH18` Regression ledger: 20 done tasks have 29 failing checks; tra, `SM48` wiki-drift reproduced: checks pages stale because ai-04 comm, `SM49` Service catalog (axis 6) lags the fleet: 6 live services mis, `SL31` Hub compose header still documents relays/global-discovery a, `SL33` shelfmark compose drifts from repo mirror (comment-only): li, `SL34` Three cosmetic repo-vs-live drifts in mini host config: stal, `SL36` README still describes the plan-era fleet: 10-stack mini lis, `SL37` Stale repo path ~/Documents/Home persists in 8 locations acr, `SL38` rig README still frames local-ai-tooling as a GitHub-only ex, `SL42` Mirror-dir naming mismatch: live stack dir is 'syncthing' bu, `SL43` adguard-nas (a NAS-deployed stack) is filed under the mini d

### `fix-69` 🟡 Fleet hygiene batch: meme-review check-vs-policy contradiction, log floods (synologand 7k, deluged 1.1/s, ufw), stale units/kernel, /tmp session litter incl. cookies, dead experiments

*host:* fleet · *track:* docker-host · *severity:* medium

Batchable cleanups: stacks-orphan-dirs flags meme-review whose data retention was deliberate — align check allowlist or archive the dir; DSM synologand geo-lookup floods /var/log/messages (7156 lines) on every tailnet login; deluged.log is 99% one libtorrent warning at 1.1/sec; mini has a stale snap-lxd mount unit keeping failed-units red, a kernel installed 24 days without reboot, 53 stale /tmp agent artifacts including two session-cookie files, and 12 stale ad-hoc results-*.json in the verification state dir; a stale host-level unpackerr on mini polls a wrong-subnet IP (retire it — the NAS container is the real one); seedbox carries dead rootless-docker artifacts; NAS has a zero-byte scheduled-task file. Nothing urgent; one sweep-and-codify session.

**Resolves 10 findings:** `SM51` stacks-orphan-dirs check and decommission policy contradict , `SM18` deluged.log is a retry-storm flood: 1649 of 1655 lines in a , `SL1` DSM abnormal-login geo-lookup fails on every tailnet-source , `SL2` Zero-byte DSM scheduled-task file 6.task — a scheduler slot , `SL6` Stale failed unit snap-lxd-38800.mount left over from lxd sn, `SL7` Reboot-required pending 24 days: kernel 5.15.0-186 + libc6 i, `SL18` unpackerr polls Radarr/Sonarr at 192.168.1.2 (wrong/old subn, `SL40` 53 stale agent-session artifacts in mini /tmp older than 7 d, `SL41` 12 stale ad-hoc results-<suite>.json side files (Jul 14-21) , `SL44` Dead rootless-docker experiment artifacts in seedbox home (d
