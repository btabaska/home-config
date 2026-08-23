# Fleet-sweep worklist — 2026-08-23 — root-cause clusters

> Generated from `docs/fleet-sweep-2026-08-23.json` (951 findings, 380 actionable) by clustering into root-cause work items. Each item = one `fix-NN` task in `tasks.json` = **one Claude Code session**. Drive with `/resolve-finding fix-NN`. Work top-down by wave; within a wave, order is flexible (lowest open number = `/build-next` auto-pick).
> 571 info-level findings are green confirmations/observations and intentionally have no task. 56 findings are covered by already-open tasks (`known-issue`) and get NO new task — they reconfirm/escalate those open items (listed at the bottom).

**23 new work items** (`fix-82`…`fix-104`) covering 324 actionable findings (4 critical · 4 high · 121 medium · 251 low). 56 further findings reconfirm 17 open tasks.

| id | sev | host | wave | title | # |
|----|-----|------|------|-------|---|
| `fix-82` | 🔴 critical | mini | 0 | B2 restic object-lock immutability decayed — restore true immutability (fix-22 regression) | 7 |
| `fix-83` | 🔴 critical | rig | 0 | rig btrfs data-checksum corruption incrementing on single-device root NVMe (leading edge of the fix-20 RO | 1 |
| `fix-84` | 🟠 high | rig | 1 | Live playit SECRET_KEY (+ since-rotated ntfy token) committed to git history — scrub + rotate | 2 |
| `fix-85` | 🟡 medium | mini | 1 | BookLogr public self-registration still OPEN — lock it down | 3 |
| `fix-86` | 🟡 medium | nas | 2 | Immich phone-photo ingestion stalled — 0 new assets in 7-9 days (fix-35 regression) | 4 |
| `fix-87` | 🟡 medium | nas | 2 | Immich ffmpeg SIGSEGV nightly crash-loop on IMG_3674.mov (fix-60 regression) | 8 |
| `fix-88` | 🟡 medium | nas | 2 | whisparr->stash auto-scan silently broken (seed-13 401) + zero-throughput framing | 5 |
| `fix-89` | 🟡 medium | fleet | 2 | Degraded/zero-throughput background services — external-API auth rot + noisy failure floods | 13 |
| `fix-90` | 🟡 medium | mini | 2 | Seerr request-layer rot — 3 dangling PROCESSING requests (fix-26 regression) | 4 |
| `fix-104` | 🟡 medium | ha | 2 | HA updates pending 3+ weeks + iPhone presence pipeline frozen 4 days (fix-36 regression) | 7 |
| `fix-91` | 🟡 medium | nas | 3 | NAS Saturday backup-window IO contention cascade (fix-55 regression) | 18 |
| `fix-92` | 🟡 medium | nas | 3 | NAS /volume1/docker world-writable perms + perms-check IO-robustness (fix-23 hardening) | 7 |
| `fix-93` | 🟡 medium | fleet | 3 | Backup-set coverage gaps — service persistent data outside curated restic/Hyper-Backup sets + DR template | 11 |
| `fix-94` | 🟡 medium | nas | 3 | Media-arr acquisition hygiene — IPTorrents grab-storm worsening (fix-50) + Sonarr unmanaged 'Any' profile | 9 |
| `fix-95` | 🟡 medium | seedbox | 3 | Download/import pipeline residuals — seedbox reaper off-by-one, deluged log flood, slskd/soularr parked i | 17 |
| `fix-96` | 🟡 medium | mini | 3 | Mini host residuals — scratch/log flood, unpackerr ansible-resurrection, docker-log corruption (fix-69 re | 17 |
| `fix-97` | 🟡 medium | rig | 4 | New-service deploy completion — unsloth-studio (lai-28) + bioclip (lai-22) never finished coverage/catalo | 22 |
| `fix-98` | 🟡 medium | rig | 4 | rig listener-baseline codification — bless Steam 27036 + MoonDeckBuddy 59999 (fix-51 extension) | 7 |
| `fix-99` | 🟡 medium | repo | 4 | checks.d dead runbook paths — fleet-wide catch-all | 13 |
| `fix-100` | 🟡 medium | mini | 4 | Check-integrity hardening — liveness-masquerade + fail-open + task_id drift + stale expects (mandate #1) | 93 |
| `fix-101` | 🟡 medium | fleet | 4 | Monitoring-coverage gaps + census enrollment + deploy tripwire (mandate #2, reconfirms verify-06/fix-68) | 11 |
| `fix-102` | ⚪ low | repo | 4 | service-catalog + anti-drift documentation batch (fix-41 class) | 19 |
| `fix-103` | ⚪ low | fleet | 4 | Accepted benign residuals — log-noise, self-recovered transients, minor version-lag, game-server residual | 26 |

## Wave 0 — active incidents (do first)

### `fix-82` 🔴 B2 restic object-lock immutability decayed — restore true immutability (fix-22 regression)

*host:* mini · *track:* backups · *severity:* critical · *regression of fix-22*

All three CRITs are one root cause: the B2 restic bucket dropped from compliance to governance-mode object-lock, 1239 file versions (both repos' config packs) expired their locks, and a live delete is no longer refused 401 — a compromised key could wipe backups. The guard understates it (samples lexicographically-first 5, not newest N) and the documented repair tool (b2-apply-bucket-policy.sh --backfill) skips any already-existing version so it cannot re-lock the decayed files. Re-lock the bucket in compliance mode, fix the backfill tool to re-lock existing versions, and correct the guard to sample newest N.

**Resolves 7 findings:** `UC1` restic B2 bucket is NOT immutable — governance-mode lock, de, `UC2` bucket-restic object-lock immutability decayed: 1239 file ve, `UC3` KNOWN (fix-22): B2 restic bucket is NOT immutable — a live d, `UH1` B2 restic bucket not truly immutable (backups run, delete no, `UM13` KNOWN/re-verified: crit immutability guard still failing — n, `UM23` Documented repair tool cannot re-lock the expired files: --b, `UM33` Guard samples lexicographically-first 5 files, not 'newest N

### `fix-83` 🔴 rig btrfs data-checksum corruption incrementing on single-device root NVMe (leading edge of the fix-20 RO-cascade)

*host:* rig · *track:* ops · *severity:* critical · ⚠️ disruptive — 4-7AM window + operator approval · *regression of fix-20*

corruption_errs on nvme2n1p2 (root+/home, WDS200T) is climbing (now 5, 3+ files, latest minutes before audit) on a single-device btrfs with no ECC RAM — the exact signature that preceded the read-only cascade that took the fleet down in fix-20. Schedule a scrub + memtest86 in the maintenance window, identify/restore the corrupt files from backup, and decide on a durable device/RAID/ECC remedy before it flips RO again.

**Resolves 1 findings:** `UC4` btrfs data checksum corruption incrementing on single-device

## Wave 1 — security / exposure

### `fix-84` 🟠 Live playit SECRET_KEY (+ since-rotated ntfy token) committed to git history — scrub + rotate

*host:* rig · *track:* security · *severity:* high

A repo-committed audit report leaks a STILL-LIVE playit SECRET_KEY and a since-rotated ntfy token into git history pushed to GitHub+Forgejo. Rotate the playit key, purge the values from history on both remotes, and fix the compose comment that cites the wrong vault path. Follow security-change-guard: consumer inventory, vault-first, negative-test the old key. Separate from the arr-key (sec-10) and bookshelf-key (sec-11) leaks.

**Resolves 2 findings:** `UH2` Committed audit report leaks a STILL-LIVE playit SECRET_KEY , `UL210` Minor doc drift: compose comment cites vault path 'playit.se

### `fix-85` 🟡 BookLogr public self-registration still OPEN — lock it down

*host:* mini · *track:* security · *severity:* medium

booklogr-api still has open registration; the lock precondition (an operator account exists) is now met, and adoption is near-zero (1 book/1 user, frozen since deploy day 2026-07-28). Flip registration off and confirm existing account access, closing the open-signup exposure.

**Resolves 3 findings:** `UM11` Public registration still OPEN on booklogr-api — lock precon, `UL16` BookLogr self-registration remains OPEN (AUTH_ALLOW_REGISTRA, `UL17` Near-zero adoption / frozen since deploy day — 1 book, 1 use

## Wave 2 — broken user-facing pipelines

### `fix-86` 🟡 Immich phone-photo ingestion stalled — 0 new assets in 7-9 days (fix-35 regression)

*host:* nas · *track:* media-pipeline · *severity:* medium · *regression of fix-35*

DB dumps are fresh but the primary library has received zero new assets for 7-9 days: the phone auto-backup ingestion side of fix-35 has stalled and the 7-day dead-man tripped. Re-establish the mobile backup flow end-to-end and verify a fresh asset lands. Distinct from Kaelyn second-user onboarding (fix-71) and the nightly ffmpeg crash (fix-87).

**Resolves 4 findings:** `UM9` Immich DB dumps are fresh, but the library they protect has , `UM66` Zero new photo uploads in 7 days — ingestion side of photos-, `UM67` Phone photo backup zero-throughput: newest asset 9 days old,, `UL47` fix-35 residual re-verified: no new Immich asset in ~9d (7-d

### `fix-87` 🟡 Immich ffmpeg SIGSEGV nightly crash-loop on IMG_3674.mov (fix-60 regression)

*host:* nas · *track:* media-pipeline · *severity:* medium · *regression of fix-60*

The bundled jellyfin-ffmpeg segfaults every midnight on the same corrupt IMG_3674.mov (Aug 21/22/23), regenerating a core.gz at /volume1 root and failing thumbnail/transcode for that + corrupt-HEIC assets — the fix-60 quarantine did not hold. Re-quarantine or transcode-skip the offending asset(s), clear the recurring core dumps, and verify the nightly job completes clean.

**Resolves 8 findings:** `UM68` REGRESSION/residual: ffmpeg SIGSEGV core dump recurs EVERY n, `UM69` nas-core-dumps FAIL: recurring nightly immich_server ffmpeg , `UM70` fix-60 stuck-asset crash-loop: IMG_3674.mov segfaults Immich, `UM71` Immich ffmpeg SIGSEGV core-dump crash-loop still recurring n, `UM73` Re-verified known failure: one unread ffmpeg core.gz crash d, `UM75` RE-VERIFIED known fail fix-60: Immich ffmpeg core dump prese, `UL141` ffmpeg SIGSEGV core dump regenerated last night — IMG_3674.m, `UL144` Corrupt HEIC assets also fail nightly thumbnail generation i

### `fix-88` 🟡 whisparr->stash auto-scan silently broken (seed-13 401) + zero-throughput framing

*host:* nas · *track:* media-pipeline · *severity:* medium

The live Whisparr Connect script POSTs stash metadataScan with NO ApiKey header, so every auto-scan 401s against auth-enforcing Stash — a green-but-dead chain. Whisparr shows 0 files/0 history across 1055 tracked scenes because its sole series is monitored=False (likely operator-intent — verify framing, don't force-grab). Fix the metadataScan auth so the handoff works, and reframe the zero-throughput monitor to reflect intended state.

**Resolves 5 findings:** `UM96` Zero-throughput frozen-green: 0 files, 0 history across 1055, `UM97` seed-13 whisparr->stash auto-scan is silently broken (metada, `UL170` Zero-throughput since 2026-07-29 (taxonomy-13 checked; expla, `UL171` UNPROBED (mutation): Stash auto-scan metadataScan 401 (seed-, `UL179` Whisparr adult-acquisition pipeline frozen: 1055 scenes / 0 

### `fix-89` 🟡 Degraded/zero-throughput background services — external-API auth rot + noisy failure floods

*host:* fleet · *track:* ops · *severity:* medium

A batch of frozen-green/degraded background services, triaged real-break vs benign: musicseerr ListenBrainz 401 storm (circuit-breaker open twice daily); adguard-nas Quad9 DoH upstream EOF/502 flood (98% of logs); beszel-agent-nas 44k docker-stats timeouts degrading hub metrics; bitmagnet torznab returning 0 hits; rreading-glasses/Bookshelf metadata lookups timing out >45s under Hardcover 429 refresh-herd; beets tagging 0 items in 45+ days (benign dormant feeder — reframe monitor). Fix the auth/upstream breaks, absorb/backoff the 429s, verify search value, reframe benign monitors.

**Resolves 13 findings:** `UM20` ListenBrainz popularity API auth rot: 401 storm + circuit-br, `UM55` Persistent Quad9 DoH upstream error flood — 98% of recent lo, `UM57` Zero-throughput / frozen-green: 0 tracks tagged in 45+ days , `UM58` Persistent per-container docker-stats timeouts (44,152 error, `UM59` Torznab keyword search returns 0 hits for every tested term , `UM61` Bookshelf book/lookup metadata search times out >45s (metada, `UM83` New-book metadata lookup slow/flaky — Hardcover upstream 429, `UM84` metadata-search-canary urllib TimeoutError = slow metadata l, `UM85` metadata-search-canary consumer probe reproducibly times out, `UL131` Frozen-green corroborated: beets DB 0 items, no tagging in 4, `UL132` Beets tags zero items and its freshness monitor green-masks , `UL138` NAS secondary resolver has intermittent external-resolution , `UL155` Hardcover 429 refresh-herd throttles cold prolific-author fe

### `fix-90` 🟡 Seerr request-layer rot — 3 dangling PROCESSING requests (fix-26 regression)

*host:* mini · *track:* media-pipeline · *severity:* medium · *regression of fix-26*

seerr-request-rot re-verified: 3 rotted PROCESSING requests (2 dangling TV where the Sonarr series was deleted + 1 never-grabbed movie) — the class fix-26 reconciled. Reconcile/purge the dangling states so the request layer reflects reality.

**Resolves 4 findings:** `UM26` seerr-request-rot re-verified: SEERR_ROT 3 — 2 dangling requ, `UL12` 3 rotted Seerr requests (fix-26), `UL72` fix-26 REOPEN: 3 rotten seerr PROCESSING requests (2 danglin, `UL73` Known failure re-verified: seerr-request-rot still failing w

### `fix-104` 🟡 HA updates pending 3+ weeks + iPhone presence pipeline frozen 4 days (fix-36 regression)

*host:* ha · *track:* ops · *severity:* medium · *regression of fix-36*

Two Home Assistant issues: three updates have sat pending >=21 days (Core 2026.7.2->2026.8.3 25d, HAOS 18.1->18.2 22d, Matter Server 9.1.0->9.2.0 24d) — a fix-36 regression; and the iPhone companion presence pipeline is silently FROZEN ~4.2 days (all btiphone active sensors stuck at 2026-08-19T17:26), beyond the accepted btiphone-stale baseline, while ha-iphone-presence false-greens. Apply the pending updates in a window, re-establish the mobile_app presence feed, and tighten the presence freshness check so a 4-day freeze pages.

**Resolves 7 findings:** `UM2` 3 HA updates left pending >=21 days (fix-36 reopen candidate, `UM3` 3 HA updates pending >=21 days: Core 25d (2026.7.2->2026.8.3, `UM4` iPhone presence pipeline silently FROZEN 4.2 days — beyond b, `UM5` iPhone companion presence pipeline FROZEN ~4 days — all btip, `UL2` Re-verified: ha-updates-pending still failing — core/OS/Matt, `UL4` 3 HA updates left pending 22-26 days (Core 2026.7.2->2026.8., `UL7` 3 HA updates left pending >=21 days (fix-36); a 4th freshly 

## Wave 3 — service / infra repair

### `fix-91` 🟡 NAS Saturday backup-window IO contention cascade (fix-55 regression)

*host:* nas · *track:* ops · *severity:* medium · ⚠️ disruptive — 4-7AM window + operator approval · *regression of fix-55*

The whole downstream cascade is ONE root cause, not many highs: the routine weekly Saturday-night Hyper-Backup window drives btrfs metadata thrash on an under-memoried DS920+, transiently spiking SQLite 'database is locked' storms across sonarr/radarr/lidarr/whisparr/bookshelf/prowlarr/komga, bitmagnet-postgres slow-SQL (inserts to 868s), the sonarr 427MB WAL, scrutiny bundled-InfluxDB timeouts, and seerr's queue retry storm — all self-clearing after the window. Remediate the root (reschedule/throttle the backup window, add RAM, or btrfs tuning) rather than the symptoms.

**Resolves 18 findings:** `UM25` Download Tracker retry storm: 1766 'Unable to get queue from, `UM52` Active NAS IO storm at audit time flipped 4+ checks pass→fai, `UM56` arr SQLite 'database is locked' storm (20 in 15min) was the , `UM60` NAS I/O storm evidenced bitmagnet-side: 1068 slow-SQL≥30s (i, `UM62` bookshelf SQLite 'database is locked' storm — 1610 events si, `UM65` REGRESSION: NAS chronic I/O-saturation storm is back — root , `UM72` SQLite 'database is locked' storm hit lidarr under NAS heavy, `UM76` NAS IO storm (load15=26.57) was the routine weekly Saturday-, `UM82` SQLite 'database is locked' storm hits radarr under current , `UM86` Recurring bundled-InfluxDB write/query timeouts under NAS IO, `UM91` arr sqlite lock storm is bursty-slow, NOT import-stalling (c, `UM95` CURRENT SQLite 'database is locked' storm hitting whisparr (, `UL127` fix-55 arr 'database is locked' storm RE-OCCURRED & worsened, `UL146` Recurring SQLite HikariCP connection-pool timeouts under NAS, `UL149` fix-55 IO-storm signature actively recurring: 15-min IO load, `UL152` Recurring SQLITE_BUSY 'database is locked' errors re-confirm, `UL156` Known InfluxDB timeouts under IO load corroborated in hub lo, `UL162` Sustained + growing SQLite 'database is locked' storm with r

### `fix-92` 🟡 NAS /volume1/docker world-writable perms + perms-check IO-robustness (fix-23 hardening)

*host:* nas · *track:* security · *severity:* medium · *regression of fix-23*

The /volume1/docker share root shows 0777 POSIX (masked by the DSM synoacl which grants read+traverse only — refuted as an active exposure, but the sticky-bit/POSIX hygiene still warrants review) while the fix-23 secret/world-writable checks chronically time out (exit 124, 60s too tight) under NAS IO load and are ACL-blind and name-filtered (0644 secret files like bazarr config escape). Review the perms, and make the checks IO-robust (timeout/ionice), ACL-aware, and broaden the secret-file name filter so the invariant is actually monitored.

**Resolves 7 findings:** `UM50` /volume1/docker share root is world-writable (0777, no stick, `UM77` crit find over /volume1/docker has no timeout/ionice guard —, `UM78` Coverage gap: world-readable (0644) secret files escape the , `UM93` fix-23 NAS perms checks time out (exit 124) and the world-wr, `UM94` fix-23 secret-perms CRIT is failing on 60s TIMEOUT (IO-load , `UL174` nas-worldwritable-sweep TIMEOUT is an IO-load casualty + tim, `UL178` CRIT secrets-perms check has chronically timed out for 10+ d

### `fix-93` 🟡 Backup-set coverage gaps — service persistent data outside curated restic/Hyper-Backup sets + DR template drift

*host:* fleet · *track:* backups · *severity:* medium

Many services' persistent data sits outside the curated backup sets: caddy_data (76 LE certs), romm DB (222M), lumiverse-data (master key + user/chat/secrets), suwayomi library, unsloth-studio state volumes, comfyui-stack state, and /volume1/manga (1.9G CBZ); plus backup-consistency caveats (pinchflat/uptime-kuma hot snapshots with no pre-dump, pmtiles capturing an 18GB regenerable extract) and .handoff-secrets.yaml.example covering only 20 of 61 live vault sections. Curate these into the backup sets or explicitly exclude-with-rationale, and refresh the DR handoff template.

**Resolves 11 findings:** `UM12` caddy_data cert volume (76 LE certs) excluded from restic ba, `UM22` RomM database (romm_romm_db_data, 222M) is in no backup set , `UM24` .handoff-secrets.yaml.example covers only 20 of 61 live vaul, `UM103` lumiverse-data volume (master key + user/chat/secrets) NOT i, `UM107` Suwayomi rig-local data dir (library DB) is EXCLUDED from th, `UM109` Unsloth Studio state volumes are NOT in the rig restic backu, `UL63` Backup-consistency caveat: pinchflat SQLite DB is snapshotte, `UL64` Backup leg covers pmtiles config, and also captures the 18GB, `UL89` Backup caveat: kuma's embedded MariaDB backed up as raw live, `UL122` /volume1/manga (1.9G downloaded manga CBZ) is NOT in the Hyp, `UL212` comfyui-stack state is not in the rig restic backup set (mod

### `fix-94` 🟡 Media-arr acquisition hygiene — IPTorrents grab-storm worsening (fix-50) + Sonarr unmanaged 'Any' profiles (fix-45)

*host:* nas · *track:* media-pipeline · *severity:* medium · *regression of fix-50*

Two growing arr-acquisition residuals: the fix-50 IPTorrents junk-grab storm worsened (grab share 60->71% over 18 days, ~430 IPT searches/day), and the fix-45 Sonarr unmanaged-profile leak grew from 5 to 10 monitored series on the default 'Any' quality profile. Rein in the IPT dominance/priority and re-pin the drifted series onto managed profiles.

**Resolves 9 findings:** `UM10` IPTorrents junk-grab storm worsening: 71% of grabs (fix-50), `UM54` KNOWN fix-50 IPT storm has WORSENED (grab share 60%->70% ove, `UL153` IPTorrents monopolising the grab stream at 69% (fix-50 grab-, `UL154` arr-grab-source-not-storming (fix-50): re-verified known res, `UM88` fix-45 residual re-confirmed: 10 monitored series still on t, `UM89` fix-45 residual WORSENED: 10 monitored series on unmanaged ', `UM90` Re-verified fix-45 reopen: 10 monitored Sonarr series now on, `UL126` 5 monitored series on default 'Any' quality profile (fix-45), `UL163` Cross-ref confirmed: Animaniacs sits in BOTH deluge-preimpor

### `fix-95` 🟡 Download/import pipeline residuals — seedbox reaper off-by-one, deluged log flood, slskd/soularr parked imports

*host:* seedbox · *track:* media-pipeline · *severity:* medium · *regression of fix-45*

Batch of seedbox/NAS download-import hygiene residuals: the extracted-reaper leaves 2-5 files >7d (recurring -mtime off-by-one, ~14G), deluged.log floods to ~69-73MB/day of libtorrent WARNINGs past the fix-69 50M guard, an orphaned Deluge RPC probe ran ~21 days, deluge-relabel-imported.py drifted (repo-only), and soularr has 2 stale parked failed imports (>3d, fix-40) fed by an accumulating slskd staging dir. Fix the reaper boundary, bound the log, kill the orphan, resync the script, and drain/denylist the parked imports.

**Resolves 17 findings:** `UM119` deluged.log floods to 73MB/day of libtorrent WARNINGs while , `UM120` Check is RED live: libtorrent WARNING flood returned, deluge, `UM79` Re-verified known failure: 2 soularr failed imports parked >, `UL164` test, `UL165` fix-40 re-verified holding: 2 stale parked failed imports (>, `UL166` soularr has 2 stale parked imports (JJK Masters of Slang) th, `UL167` 2 soularr failed imports parked >3 days feeding lidarr (JJK , `UL168` nas-soularr-failed-imports-fresh RED: stale=2 (JJK, Masters , `UL169` Log-noise observation: ~500 full Python tracebacks per log r, `UL239` seedbox-extracted-reaped: 2 files >7d survive in ~/media/ext, `UL240` seedbox-extracted-reaped FAIL — 2 leftovers >7d (14G); recur, `UL241` seedbox-extracted-reaped still failing (5 stale files) — adj, `UL242` Leaked Deluge RPC probe process running ~21 days (stuck in r, `UL243` DRIFT: deluge-relabel-imported.py in repo mirror but absent , `UL244` fix-45 residual RE-VERIFIED, not worsened: extracted reaper , `UL249` Downloads staging dir accumulating (69 album dirs + growing , `UL251` Extracted leftovers >7d persist in ~/media/extracted (fix-45

### `fix-96` 🟡 Mini host residuals — scratch/log flood, unpackerr ansible-resurrection, docker-log corruption (fix-69 regression)

*host:* mini · *track:* ops · *severity:* medium · *regression of fix-69*

Cluster of fix-69-class mini host residuals: 103+ aged /tmp scratch items + 6 stale results-*.json side files past threshold; host-level unpackerr reinstalled by automated apt because the ansible package manifest still declares it; docker json-file NUL-byte corruption aborting docker-logs for seerr/uptime-kuma plus caddy's ~34h log retention; unrotated nas-docker-health.log; an orphaned 3.6G gamefaqs .old- ZIM leftover; and unbound's so-rcvbuf not granted. Clear scratch/logs, remove unpackerr from the ansible manifest, and address log-driver/retention hygiene.

**Resolves 17 findings:** `UM19` mini-scratch-hygiene red re-verified and WORSENED: 103 aged , `UM47` fix-69 residual re-verified and worsening: 103 stale /tmp sc, `UM30` fix-69 REGRESSION: host-level unpackerr reinstalled on mini , `UM31` unpackerr-host-retired red re-verified — ROOT CAUSE FOUND: a, `UL19` Docker log retention (json-file 3x10m) gives only ~34h of ac, `UL42` fix-69 mini scratch hygiene FAIL — but no auth-material comp, `UL43` 254 aged scratch files in /tmp (fix-69 mini-scratch-hygiene), `UL71` seerr docker json-log NUL corruption — 'docker logs --since', `UL83` so-rcvbuf 4MB not granted at startup — kernel rmem_max caps , `UL84` unpackerr still running on mini despite 'retired' expectatio, `UL85` Mini unpackerr not retired (fix-69) - separate from the NAS , `UL86` Host-level unpackerr resurrected by ansible-pull package-man, `UL90` Docker json-log NUL corruption: `docker logs --since` aborts, `UL94` staleresults14d=6 stale ad-hoc results-*.json side files (fi, `UL95` KNOWN (fix-69): auth-material / aged scratch piling up in /t, `UL148` docker-health log unrotated: /var/log/nas-docker-health.log , `UL181` Orphaned 3.6GB gamefaqs .old- leftover in /volume1/zim/.inco

## Wave 4 — hygiene / drift batches

### `fix-97` 🟡 New-service deploy completion — unsloth-studio (lai-28) + bioclip (lai-22) never finished coverage/catalog/wiki/baseline (fix-68 regression)

*host:* rig · *track:* verification · *severity:* medium · *regression of fix-68*

The deploy-process gap recurred: unsloth-studio and bioclip-api shipped without the anti-drift trailers — rig.containers manifest fixed in repo but never deployed to the mini runner, no service-catalog rows (unsloth + principal-ai + bioclip), no wiki service page (404), and rig.ports 8210 blessed in repo but not deployed so lan-listeners-drift-rig fails. Deploy the manifest, add catalog rows + wiki pages, push the rig.ports baseline, and harden the deploy-completion tripwire.

**Resolves 22 findings:** `UM7` lai-28 residual: rig.containers manifest updated in repo but, `UM14` Rig coverage manifest fixed in repo but never deployed — che, `UM15` rig deployed coverage manifest lags repo by one line — unslo, `UM27` lai-28 shipped unsloth.tabaska.us without a service-catalog , `UM28` lai-28 residual: unsloth.tabaska.us vhost live+committed but, `UM32` Deployed rig.containers manifest on mini lags repo — unsloth, `UM46` Port 8210 drift is a repo-vs-deployed baseline gap: rig.port, `UM48` Deployed rig.ports baseline is stale vs repo — the Aug-17 co, `UM101` unsloth-studio running on rig but missing from the verificat, `UM110` 8210 drift is a baseline DEPLOY gap: repo rig.ports blesses , `UL20` catalog-vhost-parity failing: 'unsloth' and 'principal-ai' v, `UL35` catalog-vhost-parity FAIL: unsloth + principal-ai live vhost, `UL37` catalog-vhost-parity FAIL is exactly the two known vhosts (p, `UL75` unsloth vhost live in Caddy but has no service-catalog row/u, `UL87` No service-catalog.yaml row for unsloth vhost — catalog-vhos, `UL88` unsloth-studio missing from the DEPLOYED rig coverage manife, `UL115` Deployed rig.containers coverage manifest lags repo by unslo, `UL116` Same lai-28 skipped deploy left rig.ports without 8210 — exp, `UL119` unsloth-studio has no wiki service page (404) — downstream o, `UL194` bioclip-api missing from service-catalog.yaml (lai-22 deploy, `UL196` verify-06 confirmed: unsloth-studio running on rig but absen, `UL219` rig 8210 (unsloth-studio) is repo-blessed but the deployed /

### `fix-98` 🟡 rig listener-baseline codification — bless Steam 27036 + MoonDeckBuddy 59999 (fix-51 extension)

*host:* rig · *track:* verification · *severity:* medium · *regression of fix-51*

Two all-interface rig listeners are unblessed in both repo and deployed fix-51 baselines but are known-legitimate and deliberately re-enabled: 27036 (Steam Remote Play discovery) and 59999 (MoonDeckBuddy, re-enabled 08-16). No new exposure — codify them in rig.ports (repo + deployed) so lan-listeners-drift-rig stops false-flagging.

**Resolves 7 findings:** `UM102` rig: two uncodified all-interface listeners 27036 (Steam) + , `UM111` fix-51 lan-listeners-drift-rig still failing: 27036 (Steam) , `UL189` 59999 all-interface listener is MoonDeckBuddy — legitimate M, `UL198` Two wildcard listeners on rig unblessed in BOTH repo and dep, `UL201` Port 59999 = MoonDeckBuddy, deliberately re-enabled 08-16 (c, `UL216` Port 27036 = Steam client Remote Play listener, running sinc, `UL217` 27036 all-interface listener is the Steam client Remote Play

### `fix-99` 🟡 checks.d dead runbook paths — fleet-wide catch-all

*host:* repo · *track:* verification · *severity:* medium

Dozens of checks across nearly every checks.d file point at nonexistent runbook paths — the wrong prefix (wiki/runbooks/*.md instead of wiki/docs/runbooks/) and several basenames that don't exist at all (docker.md, dns.md, backups.md, media.md, nas.md, mini.md, rig.md, photos.md, verification.md, game-saves.md), including on CRIT checks. One sweep: correct the prefix, create/point the missing runbooks, and add a lint so runbook: fields must resolve.

**Resolves 13 findings:** `UM38` Runbook wiki/runbooks/docker.md is a dead path on 5 of 12 ha, `UM40` 22 of 28 checks carry dead runbook pointers (wiki/runbooks/d, `UM44` runbook pointer 'wiki/runbooks/nas.md' is dead for 16 checks, `UM98` Dead runbook references: wiki/runbooks/backups.md (on a CRIT, `UM99` 5 of 6 dns checks reference a nonexistent runbook (wiki/runb, `UL32` runbook value 'wiki/runbooks/verification.md' does not resol, `UL55` 14 of 21 checks point at runbook 'wiki/runbooks/verification, `UL112` All 5 runbook fields point at wiki/runbooks/photos.md, which, `UL113` All 10 checks reference dead runbook paths (wrong prefix + 6, `UL184` Runbook wiki/runbooks/backups.md referenced by 5 checks (3 o, `UL185` runbook values point at wiki/runbooks/*.md — real files live, `UL187` Both game-saves checks point at a runbook file that does not, `UL224` 30/32 rig checks reference a nonexistent runbook path wiki/r

### `fix-100` 🟡 Check-integrity hardening — liveness-masquerade + fail-open + task_id drift + stale expects (mandate #1)

*host:* mini · *track:* verification · *severity:* medium

Large harness-quality batch violating standing mandate #1: liveness-masquerading-as-consumer checks (dockge/paperless/mealie/tautulli/wallabag/whisparr/stash/flaresolverr/palworld/moondeck/bug-intake, homepage SPA-shell, network raw-TCP, ansible-pull exit-status-only); fail-open/fail-green checks that pass vacuously on transport failure or when the watched target disappears; persistently-RED stale expects (rig-marinara/rig-lumiverse asserting the deprecated comfyui.tabaska.us URL); systematic task_id drift (14+ checks) and stale comments; plus assorted probe-tuning tautologies. Deepen these to real consumer/robust assertions.

**Resolves 93 findings:** `UM1` Liveness-only consumer-check gap confirmed for 4 manifested , `UM16` Dockge covered by bare HTTP-200 liveness only — no consumer , `UM21` Paperless document/OCR pipeline has NO consumer probe — whol, `UM29` Reconciler timer check's 'last run not failed' clause is a d, `UM34` locks probe fails open: unreachable/500ing arr APIs and miss, `UM35` Only verification check for paperless is liveness-grade (log, `UM36` Liveness check masquerading as substantive: name claims 'doc, `UM39` Storm tripwire is a chronic false positive: legit IPTorrents, `UM41` 8 checks decayed at bare status-code liveness despite the fi, `UM42` Systematic task_id drift: 14 checks point at the wrong tasks, `UM43` mini-homepage probes the static SPA shell (/ -> 200), a docu, `UM45` Sole network check is a raw TCP handshake (port-open livenes, `UM63` Both Bookshelf->CWA checks pass vacuously if their NAS path , `UM64` Check named 'newest immich DB dump is >1MB' actually passes , `UM74` nas-flaresolverr is liveness masquerading as a service probe, `UM80` IPTorrents imdbid ID-search through Prowlarr returns ZERO it, `UM87` shelfmark-mam-path-ready has decayed toward liveness: health, `UM100` Crit-severity DR-convergence check is exit-status-only liven, `UM104` rig-marinara-connections is STALE (asserts obsolete public-g, `UM106` Palworld covered by liveness metric only — no player-join / , `UM112` Connection checks fail as false-positives: they assert the d, `UM113` game-moondeck-buddy is TLS-listener liveness, not a Buddy AP, `UM114` polkit leg of rig-poweroff-inhibit is an always-pass tautolo, `UM115` Two ai-01 connection checks stuck permanently RED on a stale, `UM121` Disabled check's justification is stale — seedbox IS reachab, `UL21` dotfiles-content-clean cannot distinguish 'no drift' from 'c, `UL24` Stale accepted-ids baseline: all 8 'permanently cookie-gated, `UL25` empty+empty still passes green although the library is now k, `UL27` Secondary liveness-leaning checks — version/status scrapes s, `UL28` Three checks fail OPEN: transport/daemon failure yields empt, `UL29` cwa-upstream-cve-catchup conflates transient GitHub-API fail, `UL30` diun monitoring is liveness-only — no throughput/consumer ch, `UL34` Monitoring check mini-dockge is liveness-only (curl / -> 200, `UL49` MCP agent-lane probe stops at tools/list — a Memos MCP layer, `UL54` Monitoring is liveness-only — no consumer-grade check that a, `UL60` Stale 'liveness only for now ... lands in bmig-06' comments , `UL62` Crit check opens the live navidrome.db without -readonly, un, `UL65` verify-06 IPT imdbid-search=0 tonight was a TRANSIENT thrott, `UL66` min-ratio 0.85 tightening trigger has been met (live ratios , `UL76` host: url inconsistent with identical-shaped siblings using , `UL77` stash-serving name claims 'real consumer end' but only prove, `UL80` Verification check for Tautulli is liveness-only — no ingest, `UL81` Both tv-torrent checks guard a zero-throughput path: /mnt/sh, `UL91` Check window under-samples a bursty nightly storm — daily 10, `UL92` Daily Kobo-sync check probes the BASE api_endpoint (returns , `UL93` Check blind spot: bad[:5] truncation with no count silently , `UL96` Stale contradictory comment on the NAS secondary-resolver ch, `UL97` dns-mini-external: fast-tier crit with single 3s UDP try and, `UL98` dns-nas-internal: single 3s UDP try at crit against the NAS , `UL99` terraria-world-loaded's name pins world AnalogueCoop but the, `UL100` Both Assist-LLM checks carry task_id ha-12, which in tasks.j, `UL101` Stale comment on journaling-memos-mcp: yaml says OWUI filter, `UL102` fleet-fs-tools expect is a bare unanchored substring 'docker, `UL103` unsloth-studio comment block spliced inside the plant-scout-, `UL104` Hardcoded Prowlarr indexer id in URL path (/1/api) contradic, `UL105` SLOW rung of the true-state ladder conflates search ERRORS w, `UL106` Throughput leg 'fetched>=1' is a lifetime counter — permanen, `UL107` Accepted-count baseline drifted loose: threshold <=8 was set, `UL108` Retained /opt/stacks/meme-review dir still contradicts the s, `UL109` homepage-widget-errors fails OPEN: docker-logs error or miss, `UL110` terraria-tile-present asserts a bare substring over the whol, `UL111` Journal-bloat checks fail OPEN if the journalctl --disk-usag, `UL114` Several system checks carry semantically-wrong task_ids (tri, `UL118` Monitoring depth gap: only check is app-liveness (/api/info , `UL125` iptorrents-idsearch-returns-results=0 is a TRANSIENT probe f, `UL135` 50h dead-man window carries a 40-day-old 'tighten to ~30h on, `UL137` Monitoring is liveness-only — no consumer-grade check for sc, `UL139` Backup dead-man matches ANY fresh *.tar in /volume1/backups , `UL147` Fail-green substrate hazard: both absence-of-junk checks pri, `UL150` Intermediate probe: filter-file presence cannot detect prese, `UL172` Monitoring blind spot: mesh-direct check hardcodes only rig+, `UL175` Stale nas-08 comment: backup-immich-dump-fresh comment claim, `UL177` Monitoring gap: beets checks are liveness/freshness-only, ma, `UL180` Monitoring is liveness-only (/ping) — no consumer-grade whis, `UL182` Media-domain check misfiled in alerting.yaml (id media-*, ta, `UL183` Stale header comment claims the immich-dump check 'FAILS tod, `UL186` Stale comment says dns-nas-* checks 'FAIL today ... correct , `UL188` Marinara/Lumiverse connection checks FAIL but live connectio, `UL195` export-manifests-inventory-fresh is intermediate, not consum, `UL199` litellm-adjacent check fails are the KNOWN-stale ai-01 marin, `UL200` rig-lumiverse-connections FAIL is a STALE CHECK, not real br, `UL221` agent-memory-plugin MEMORY.md leg is a one-time-success latc, `UL222` Launch-chain assertion incomplete: cores asserted but the re, `UL223` rig-ml-window-catchup-clean passes vacuously if immich-ml-wi, `UL225` Checks whose own comments call a failure an 'incident' are s, `UL226` Stale check: expect regex demands https://comfyui.tabaska.us, `UL227` Two ai-01 conn checks fail on a STALE assertion — expect old, `UL228` ollama-shim rationale cites retired Obsidian consumers; shim, `UL230` stale check, `UL231` No freshness assertion in the check pair — zero-throughput l, `UL245` Hygiene finds pass vacuously if their target directory disap, `UL246` Hardcoded 100G headroom threshold assumes quota -s always re, `UL250` seed-01 disable rationale LAPSED — seedbox SSH now reachable

### `fix-101` 🟡 Monitoring-coverage gaps + census enrollment + deploy tripwire (mandate #2, reconfirms verify-06/fix-68)

*host:* fleet · *track:* verification · *severity:* medium

100%-coverage tripwire gaps: services/surfaces with no consumer or freshness probe (MeTube yt-dlp staleness, bedrock-connect DNS-rewrite, unbound DNSSEC validation, sys-disk-smart-health freshness, mini host timers, whisparr media-watchable canary); notify-only Diun with detect+deliver unprobed; the edge WAN exposure sweep frozen at a 22-port list while the fleet grew to ~90 ports; and census enrollment gaps for host units (ollama systemd shim, rig syncthing user-service, rig host timers). Add the missing consumer/freshness checks, enroll the host units, refresh the exposure baseline, and codify a deploy-completion coverage tripwire.

**Resolves 11 findings:** `UM37` WAN exposure sweep probes a 22-port list frozen at the 2026-, `UM49` Diun coverage is container-liveness only — the notify-only s, `UL10` Re-surfacing the one practical UNPROBED gap: MeTube yt-dlp i, `UL15` Monitoring gap: the AdGuard featured-server DNS-rewrite leg , `UL57` Two mini host timers have no direct check (one outcome-cover, `UL69` Monitoring gap: sys-disk-smart-health asserts presence+statu, `UL82` No check asserts DNSSEC validation — a silent validation reg, `UL176` Coverage gap: the 'class canary' sweeps Radarr+Sonarr only, , `UL203` Coverage census gap: ollama (host systemd unit) is not enrol, `UL213` Three rig host units have no verification check — the monito, `UL229` rig syncthing user-service has no coverage-manifest entry (m

### `fix-102` ⚪ service-catalog + anti-drift documentation batch (fix-41 class)

*host:* repo · *track:* ops · *severity:* low · *regression of fix-41*

Batch of catalog/anti-drift doc gaps: stale/inaccurate service-catalog rows (metube host-network, beets ui:false despite :8337, unpackerr port:null despite :5656, beszel agent-undercount, stash 'no widget', comfyui model count, deluge port) and missing rows (adguardhome-nas, nas diun, bookshelf Homepage tile); plus real live-vs-repo drift (ollama override.conf env vars unmirrored, rig /opt/stacks/palworld not a git repo, musicseerr .env.example gap, recyclarr config comment). Reconcile catalog to live and mirror the drifted configs.

**Resolves 19 findings:** `UL56` Stale service-catalog note: claims "host-network" but metube, `UL59` Repo-mirror gap: musicseerr/.env.example tracked in /opt/sta, `UL67` Stale/contradictory config comment: header warns plex-tmdb i, `UL74` Catalog note undercounts beszel agents (says only mini agent, `UL133` No Homepage tile for bookshelf while every other arr backend, `UL136` Catalog understates beets: says ui:false/port:null but a web, `UL157` Catalog gap: no row for adguardhome-nas / secondary DNS reso, `UL158` Catalog note stale: claims 'No API key in vault - no widget', `UL159` Minor catalog inaccuracy: unpackerr port:null though contain, `UL160` NAS diun instance not represented in service-catalog (catalo, `UL202` Anti-drift gap: live ollama override.conf (7 env vars incl K, `UL204` Anti-drift gap: rig /opt/stacks/palworld is NOT a git repo a, `UL214` Catalog notes credit only the mini agent as feeding the Besz, `UL215` Catalog documents only the original 3 image models; live Com, `UL247` Catalog lists Deluge port 8112 — another tenant's port per t, `UL248` Catalog port field stale: deluge row says port 8112 but web , `UL1` ESPHome not deployed in HA — no config_entry, zero entities,, `UL5` service-catalog note for home-assistant is stale (still clai, `UL6` service-catalog note for home-assistant is stale (claims pro

### `fix-103` ⚪ Accepted benign residuals — log-noise, self-recovered transients, minor version-lag, game-server residuals

*host:* fleet · *track:* ops · *severity:* low

Triage catch-all for low-impact, mostly monitor-only findings: benign log-noise/tracebacks (tautulli KeyError, abs Patreon RSS, bazarr/jellyfin ffprobe on junk rips, cwa cosmetic errors, soularr per-peer noise, searxng CAPTCHA flaps); self-recovered transients (arr-queue/unpackerr fetch errors under IO, immich-ml night-window CUDA OOM, scrutiny publish timeouts where data lands); truthful stable residue (navidrome 46/3525 greyed tracks, sonarr RetroToon indexer down w/ redundancy, OWUI bake-off capability-flag caveat); minor version-lag (kometa 2 patches behind, duplicate Plex playlists, libreseerr Greek-script author-gate); and known-stable rig game-server residuals (palworld UE SIGSEGV restarts, playit UDP register errors ~1/day self-healing, fix-34). Note-and-close or accept-with-rationale; reframe monitors that green-mask them.

**Resolves 26 findings:** `UL11` 46/3525 (1.3%) greyed-out missing tracks across 4 albums — s, `UL14` Two transient, self-recovered API failures since 2026-08-02 , `UL50` Running v2.4.6, upstream newest is 2.4.8 (two patch releases, `UL51` Stale duplicate playlists in Plex from a 2026-07-10 run (DC , `UL52` Author gate rejected a legitimate request over Greek-vs-Lati, `UL61` 46/3525 tracks flagged missing (grey in UI) across 4 albums , `UL68` Daily 06:01 publish POST times out client-side on 12 of 21 d, `UL70` External-engine failure noise: startpage persistently CAPTCH, `UL79` Sporadic clear_recently_added_queue KeyError tracebacks (23 , `UL124` 3 stale duplicate franchise playlists linger in Plex beside , `UL128` Intermittent podcast RSS fetch errors for Patreon-gated feed, `UL129` Recurring ffprobe 'cannot analyze this video file' errors on, `UL134` Recurring cosmetic log noise: author display-order errors, a, `UL145` Recurring ffprobe failures on a few malformed FMA Brotherhoo, `UL161` One indexer (RetroToon via Prowlarr) unavailable — single he, `UL173` Transient arr-queue fetch errors (10 in ~22 days) under NAS , `UL190` Bake-off fairness caveat: chat carries full UI capability fl, `UL193` Continue 2.0.0 exthost logs missing ort-wasm-simd-threaded.w, `UL197` Transient CUDA BFC allocation failures (OOM) at night-window, `UL205` Root cause of the 9 restarts: intermittent UE engine SIGSEGV, `UL206` Palworld public path: playit UDP register-error persists (kn, `UL207` KNOWN fix-34: playit UDP-claim register error recurred (REGI, `UL208` playit UDP register-error recurs ~1/day (fix-34) — re-verifi, `UL209` playit UDP register-error class recurred once in 24h — known, `UL211` Old transient exit-1 failures on record (playit-udp-guard 08, `UL220` Known-failing check re-verified: 1 playit UDP-claim register

## Reconfirmed open tasks (no new fix-NN)

> These findings re-verify conditions already tracked by open tasks. No new task; the note records current state (still-open-valid / worsened / now-actionable).

- **`sec-09`** — still-open-valid — verification runner env still holds the WRITE-capable Cloudflare token; no read-only DNS token minted (1 findings: `UM8`)
- **`sec-10`** — still-open-valid — 4 arr API keys still committed cleartext in unpackerr.conf (live + repo mirror pushed to GitHub) (4 findings: `UH3`, `UH4`, `UM81`, `UM92`)
- **`sec-11`** — still-open-valid — leaked bookshelf key rotation UNPROBED/unconfirmed (1 findings: `UL18`)
- **`fix-70`** — worsened — NAS Plex now ~103 builds / 2 upstream releases behind; edge-plex-version-current stays green (2 findings: `UM53`, `UL151`)
- **`fix-71`** — still-open-valid — Kaelyn Tabaska still 0 photos/0 videos (human onboarding leg) (4 findings: `UL123`, `UL140`, `UL142`, `UL143`)
- **`fix-73`** — still-open-valid, item churned — stuck pre-import grab is now Animaniacs S01 (not the filed Only Murders); Teen Titans Go S06E32 is a related stall the preimport check misses (9 findings: `UM116`, `UM117`, `UM118`, `UL232`, `UL233`, `UL234`, `UL235`, `UL236`, `UL237`)
- **`fix-74`** — still-open-valid + aging — mini kernel/libc reboot pending, uptime 44-45d (disruptive: needs 4-7AM reboot) (3 findings: `UM18`, `UL44`, `UL58`)
- **`fix-75`** — still-open-valid — Linux RTC mitigation holding (offset ~0s) but durable Windows RealTimeIsUniversal cure not yet applied (1 findings: `UL191`)
- **`fix-76`** — still-open-valid — alert SEND path green but device RECEIPT still unprobed; several lane units lack OnFailure paging (4 findings: `UL13`, `UL41`, `UL46`, `UL48`)
- **`fix-77`** — still-open-valid, draining — Bazarr wanted backlog ~2154 episodes/2 movies, actively draining (not worsened) (3 findings: `UL120`, `UL121`, `UL130`)
- **`fix-78`** — still-open-valid (deferred) — 15 of 19 Suwayomi library series still 0 downloaded chapters (was 16, not worsened) (3 findings: `UM108`, `UL192`, `UL218`)
- **`fix-79`** — still-open-valid — no Uptime-Kuma monitor for Syncthing (hub GUI or mini node) (1 findings: `UL78`)
- **`fix-80`** — still-open-valid — /opt/foss-setup clone stale w/ uncommitted regenerated manifests, /opt/stacks in-flight WIP, and the phantom triliumnext/trilium in compose-images.txt awaits the fix-80 commit leg (13 findings: `UM6`, `UM17`, `UL8`, `UL9`, `UL22`, `UL23`, `UL26`, `UL36`, `UL38`, `UL39`, `UL40`, `UL53`, `UL117`)
- **`fix-81`** — still-open-valid — nvidia-cdi-refresh.service enabled but reboot-recovery still unproven (1 findings: `UM105`)
- **`media-10`** — now-actionable — zero readarr torrents remain on betty but 'readarr' still in ARR_LABELS (repo + live) (1 findings: `UL238`)
- **`media-13`** — still-open-valid — both stale 2026-07-02 @sharesnap snapshots (vol2/vol3) still pinning reclaimable space (1 findings: `UM51`)
- **`ha-19`** — still-open-valid (lower risk) — 3 docker bridge networks still squat 192.168.0.0/16 incl. the HA VLAN; none on routable VLANs (4 findings: `UL3`, `UL31`, `UL33`, `UL45`)
