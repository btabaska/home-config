# Quality-gate worklist — root-cause clusters

> Generated from `docs/quality-gate-2026-07-16.json` (303 findings) by clustering into
> root-cause work items. Each item = one `fix-NN` task in `tasks.json` = **one Claude Code
> session**. Drive with `/resolve-finding fix-NN`. Work top-down by wave; within a wave, order is flexible.
> 113 info-level findings are green confirmations and intentionally have no task.

**26 work items** covering all 190 actionable findings (3 critical · 30 high · 62 medium · 95 low).

| id | sev | host | wave | title | # |
|----|-----|------|------|-------|---|
| `fix-20` | 🔴 critical | rig | 0 | Recover rig root btrfs read-only incident + durable OS-NVMe fix | 12 |
| `fix-21` | 🟠 high | seedbox | 1 | Close public exposure of seedbox torrent clients (Deluge RPC/web, qBittorrent, slskd) | 3 |
| `fix-22` | 🟠 high | backblaze-b2 | 1 | Make restic B2 backups actually immutable (default retention) + lock hyper-backup bucket | 4 |
| `fix-23` | 🟡 medium | nas | 1 | Secrets & filesystem-permission hygiene (world-readable env, stale local secret dumps) | 5 |
| `fix-24` | 🟡 medium | mini | 1 | Close unintended public exposure: WAN-reachable Plex 32400 + public A-record to LAN IP | 2 |
| `fix-25` | 🟠 high | nas | 2 | Fix the silent "grabbed → never imported" class (download-client import + reaper label coverage) | 8 |
| `fix-26` | 🟠 high | mini | 2 | Reconcile stuck request-layer states (seerr/libreseerr/musicseerr dangling & unmonitored) | 4 |
| `fix-27` | 🟠 high | nas | 2 | Remediate "green but not watchable": sample-file imports + unextracted RARs | 7 |
| `fix-28` | 🟡 medium | nas | 2 | Fix Plex/Navidrome library correctness (unmatched items, missing tracks, #recycle indexing) | 3 |
| `fix-29` | 🟠 high | fleet | 2 | Close the liveness-vs-reality monitoring gap (end-to-end checks for the failure classes just found) | 3 |
| `fix-30` | 🟡 medium | mini | 3 | Repair the verification framework itself (LLM triage, false positives, deploy drift) | 6 |
| `fix-31` | 🟠 high | nas | 3 | Restore UPS/NUT power-loss protection (or cleanly retire the dead client) | 3 |
| `fix-32` | 🟠 high | mini | 3 | Fix Caddy reverse-proxy routes (ha.tabaska.us 400, llamaswap not reloaded, stray placeholders/vhosts) | 6 |
| `fix-33` | 🟠 high | mini | 3 | Unfreeze Miniflux (all 52 feeds excluded from polling) + remove leftover bootstrap admin | 2 |
| `fix-34` | 🟡 medium | rig | 3 | Fix AMP scheduled backups (silently failing) + backup-bloat in restic + playit UDP churn | 3 |
| `fix-35` | 🟠 high | nas | 3 | Immich: start real phone backups (empty library) + lock down the unused second admin | 4 |
| `fix-36` | 🟡 medium | ha | 3 | Home Assistant health: unavailable entities, dead integrations, pending updates | 5 |
| `fix-37` | 🟡 medium | mini | 3 | Media-aux service config fixes (navidrome backup, kometa, pinchflat/bgutil, RomM empty) | 4 |
| `fix-38` | 🟡 medium | nas | 3 | Reading/CWA: reconcile Kobo store-passthrough state + note fork-image supply-chain risk | 3 |
| `fix-39` | 🟡 medium | mini | 4 | mini host cleanup: dead Pterodactyl LEMP + root cron, broken crons, dead stack dirs, reclaimable docker | 4 |
| `fix-40` | 🟡 medium | nas | 4 | NAS host hygiene: timezone drift, soularr parked import, core dumps, junk files, single-disk note | 5 |
| `fix-41` | 🟡 medium | mini | 4 | Repo-vs-live drift codification (forgejo stack, manifests, .env keys, ansible units) | 4 |
| `fix-42` | 🟡 medium | mini | 4 | Make off-site DR reproducible (ansible backup role is a no-op diverged from live) | 1 |
| `fix-43` | ⚪ low | device | 4 | Repo junk & dead-path cleanup (tracked pycache, stale root files, worktree, retired-service remnants) | 24 |
| `fix-44` | ⚪ low | device | 4 | Tracker + wiki drift cleanup (stale generated pages, orphan ids, arithmetic, recurring wiki-drift red) | 4 |
| `fix-45` | ⚪ low | mini | 4 | Fleet hygiene batch: host junk, core dumps, stale caches, log/backup bloat (mini/rig/seedbox) | 65 |


## Wave 0 — active incident (do first)

### `fix-20` 🔴 Recover rig root btrfs read-only incident + durable OS-NVMe fix
*host:* rig · *track:* audit-fixes · *severity:* critical · ⚠️ disruptive → 4–7AM window + approval

OS btrfs on the marginal NVMe (74:00.0) hit corrupt-leaf 22:49 EDT 2026-07-15 and remounted read-only; cascade took down restic, ansible-pull, palworld, litellm-db/LiteLLM, open-webui + mini wiki-rag-sync. Recover the FS (btrfs check / restore from restic), then execute the long-deferred reseat/replace so it cannot recur.

**Resolves 12 findings:** `C1` Rig root filesystem is mounted READ-ONLY right now; journald, `C2` Rig root filesystem hit BTRFS metadata corruption and is mou, `C3` Root btrfs remounted read-only after BTRFS 'corrupt leaf' on, `H22` Palworld server down (REST dead even from localhost, contain, `H23` Rig restic backups failing — last success 2026-07-15 05:40 U, `H25` litellm-db segfaulted (exit 139) 52 min after RO remount; do, `H26` LiteLLM effectively DOWN for all virtual-key clients: 503 no, `H27` rig restic backup missed its nightly run under the RO incide, `I104` systemd-failed-rig failing hourly since ~04:40 UTC: ansible-, `I105` llama-swap fully functional under RO FS; verification LLM-tr, `M54` wiki->OWUI RAG sync failing since 2026-07-16 05:14 UTC (OWUI, `M56` open-webui serves and reads OK but is write-dead: sqlite dat


## Wave 1 — security & exposure (low blast radius)

### `fix-21` 🟠 Close public exposure of seedbox torrent clients (Deluge RPC/web, qBittorrent, slskd)
*host:* seedbox · *track:* security · *severity:* high

Deluge RPC 3254 + deluge-web 5945 (plain HTTP) + qBittorrent 13091 + slskd all bind 0.0.0.0 on the public IP betty.bysh.me; passwords cross the WAN in cleartext. Bind to loopback/tailnet, front with TLS, retire the vestigial qBittorrent.

**Resolves 3 findings:** `H2` Deluge RPC (3254), deluge-web (5945, plain HTTP) and qBittor, `L9` qBittorrent-nox running since Jun 27 with zero torrents load, `M25` slskd API driven over plaintext HTTP to a public IP (API key

### `fix-22` 🟠 Make restic B2 backups actually immutable (default retention) + lock hyper-backup bucket
*host:* backblaze-b2 · *track:* security · *severity:* high

bucket-restic has fileLock enabled but NO default/per-file retention → nothing is lock-protected; the append-only key is the only guard while the laptop holds a delete-capable master key. Set GOVERNANCE 30d default retention; evaluate lock on bucket-hyper-backup; delete orphan bucket-rustic + ao-verify test snapshots.

**Resolves 4 findings:** `H20` bucket-restic has fileLock enabled but NO default retention , `L57` Leftover 8-byte 'ao-verify'/'ao-verify2' test snapshots in b, `L58` Orphan empty bucket 'bucket-rustic' (apparent typo of bucket, `M37` Confirmed still true: bucket-hyper-backup has NO Object Lock

> **RESOLVED 2026-07-17** — GOVERNANCE 30d default retention set + 1174 existing versions backfilled (H20); `bucket-rustic` deleted (L58); 3 ao-verify snapshots forgotten (L57); `bucket-hyper-backup` documented accepted-unlocked — retention would break HB Smart Recycle rotation (M37). Master key retired from the vault, replaced day-to-day by a scoped read-only `b2-ops` key. Checks `b2-restic-immutable` (crit, live delete-probe → 401), `b2-bucket-policy`, `restic-snapshot-hygiene-{mini,rig}` all green. See `wiki/docs/runbooks/backup-restore.md` § Immutability.

### `fix-23` 🟡 Secrets & filesystem-permission hygiene (world-readable env, stale local secret dumps)
*host:* nas · *track:* security · *severity:* medium

health.env is 0777 with an ntfy token; broad 0777 across /volume1/docker; a 15GB migration-snapshot with live Plex/secret material sits in iCloud-synced ~/Documents; vault keys that live services need are blank (forgejo admin while Forgejo is the deploy control-plane; soulseek/soularr). Tighten perms; purge/relocate the snapshot; populate or document the empty keys.

**Resolves 5 findings:** `M7` health.env is world-readable (0777) and contains an ntfy pub, `M26` Vault drift: soulseek.* empty while slskd is live, whisparr , `M43` 15 GB stale migration snapshot with live secrets sits in iCl, `M44` Vault forgejo.admin_user/admin_password are empty while Forg, `M45` All 4 soulseek vault keys empty while soularr is live on NAS

### `fix-24` 🟡 Close unintended public exposure: WAN-reachable Plex 32400 + public A-record to LAN IP
*host:* mini · *track:* network · *severity:* medium

Plex :32400 answers from the home WAN IP (edge not fully closed); www.tabaska.us has a PUBLIC A record pointing at private 192.168.10.2. Close the port at the edge; fix/remove the public record.

**Resolves 2 findings:** `L53` www.tabaska.us has a PUBLIC A record pointing at private LAN, `M61` Plex port 32400 is directly reachable from the public intern


## Wave 2 — broken user-facing pipelines

### `fix-25` 🟠 Fix the silent "grabbed → never imported" class (download-client import + reaper label coverage)
*host:* nas · *track:* media-pipeline · *severity:* high

Radarr grabs vanish from Deluge with no error (3 movies, 10d); a Readarr book sits 100% complete+seeding but fell out of tracking; 273/375 seedbox torrents stuck in pre-import labels because the reaper only covers sonarr labels; Post-Import Category missing on readarr/whisparr Deluge clients. Restore the completion-detection + import path across all *arr, extend reaper/category coverage, add a >48h-stuck alarm.

**Resolves 8 findings:** `H3` 3 movie requests stuck PROCESSING 10 days: Radarr grabs vani, `H5` Book 'Naamah's Curse' fully downloaded on seedbox (100%, see, `H6` Libreseerr adds authors unmonitored (addOptions monitor:none, `H14` Phantom 'downloading' request: 3OH!3 - 3OH!3 stuck since 202, `H16` 4 book requests stuck 'processing 0%' >48h with zero readarr, `L42` 273 of 375 torrents are 100% done >48h but still in pre-impo, `M13` Phantom 'downloading' request: 3OH!3 self-titled stuck since, `M23` Post-Import Category (queue-clog fix) not applied to readarr

### `fix-26` 🟠 Reconcile stuck request-layer states (seerr/libreseerr/musicseerr dangling & unmonitored)
*host:* mini · *track:* media-pipeline · *severity:* high

seerr request points at a deleted Sonarr series (404, stuck PROCESSING forever); another has zero Radarr history; libreseerr statuses only refresh on UI POST; a Naamah grab imported into a misspelled duplicate book record. Add reconciliation that detects dangling/rotten links and surfaces or re-drives them.

**Resolves 4 findings:** `H4` Seerr request 12 (New Teen Titans) points at a Sonarr series, `H15` Naamah's Curse grab imported into duplicate misspelled book , `M12` Seerr request 10 (A Virtual Princess Bride Reunion) has zero, `M36` Request statuses only update on UI-triggered POST /api/reque

### `fix-27` 🟠 Remediate "green but not watchable": sample-file imports + unextracted RARs
*host:* nas · *track:* media-pipeline · *severity:* high

177 tracked-green items have only a junk sample on disk (Gossip Girl worst: 120 samples over 43GB of unextracted RARs); All About My Mother mismapped to Mamma Mia; two ISO "imports" unplayable; 606 unextracted rars inside library roots; unpackerr has no whisparr block and is invisible to monitors. Re-grab/extract, fix mappings, add an extraction-backlog + min-filesize acceptance check.

**Resolves 7 findings:** `H11` Gossip Girl: all 120 'imported' episode files are Sample/*.a, `H12` 6 movies live with sample-file imports (6-129MB) as their mo, `H13` Radarr movie 'All About My Mother' is mapped to the Mamma Mi, `H30` Gossip Girl signature quantified: 177 items tracked green bu, `M27` Unpackerr has no [[whisparr]] block — whisparr archives will, `M31` Two ISO 'imports' (81GB total) are green in Radarr but invis, `M60` 606 unextracted rar/r00 files inside the Plex library roots:

### `fix-28` 🟡 Fix Plex/Navidrome library correctness (unmatched items, missing tracks, #recycle indexing)
*host:* nas · *track:* media-polish · *severity:* medium

11 Plex movies with no external-id match, 4 Sonarr series missing/mismatched in Plex, Marshall Mathers LP missing a track, Navidrome indexing the Synology #recycle bin + ghost/missing rows, Plex credit-marker gaps, an empty duplicate album folder.

**Resolves 3 findings:** `M32` 11 Plex movies have no external-ID match, including two fres, `M33` 4 more Sonarr series with files are missing or mismatched in, `M34` The Marshall Mathers LP is incomplete: 17/18 tracks on disk,

### `fix-29` 🟠 Close the liveness-vs-reality monitoring gap (end-to-end checks for the failure classes just found)
*host:* fleet · *track:* verification · *severity:* high

Every liveness signal stayed green while services were functionally dead (docker "healthy" on a segfaulted DB and a write-dead host; ai-stack ping up during the outage; unpackerr invisible; whisparr monitor has no notification channel; homepage tiles false-pos/neg; beszel email is a dead path). Add consumer-end checks per class and fix the broken monitors/notifications.

**Resolves 3 findings:** `M17` Homepage Maintainerr tile points at a nonexistent container , `M21` New 'NAS Whisparr' monitor (id 56) has no notification chann, `M57` All AI-stack monitoring still green during the outage: ai-st


## Wave 3 — service/infra repair

### `fix-30` 🟡 Repair the verification framework itself (LLM triage, false positives, deploy drift)
*host:* mini · *track:* verification · *severity:* medium

LLM auto-triage 404s on a retired Ollama endpoint; restic-fresh-rig throws false-positive STALE after a reboot; self-referential systemd-failed check; quick-tier --host resurrects disabled checks; ntfy tier label bug; /opt/verification has drifted from the repo in both directions (a naive rsync --delete would delete live-only scripts); stale README/env.

**Resolves 6 findings:** `H24` LLM triage layer silently dead: /etc/verification/env pins q, `M19` Verification LLM auto-triage broken since ai-01 Ollama demot, `M20` restic-snapshot-fresh-rig is a FALSE POSITIVE: backup succee, `M38` Deployed verification tree has drifted from the repo in BOTH, `M39` False-positive STALE in today's daily run: rig backup actual, `M53` Four live scripts in /opt/verification/bin are not in repo v

### `fix-31` 🟠 Restore UPS/NUT power-loss protection (or cleanly retire the dead client)
*host:* nas · *track:* nas-foundation · *severity:* high

NAS DSM UPS server is disabled and no UPS is physically attached, so mini upsmon has retried every 5s for 7+ days (~120k journal errors, 3.9G journal). Attach/enable a UPS and repair the netclient, or retire upsmon and clear the journal bloat.

**Resolves 3 findings:** `H1` UPS monitoring dead for 7+ days: upsmon cannot reach ups@192, `H29` Root cause of dead UPS chain: DSM UPS support is disabled AN, `M59` mini nut-monitor is a permanently dead client: active servic

### `fix-32` 🟠 Fix Caddy reverse-proxy routes (ha.tabaska.us 400, llamaswap not reloaded, stray placeholders/vhosts)
*host:* mini · *track:* ops · *severity:* high

ha.tabaska.us returns 400 (HA lacks trusted_proxies for mini); llamaswap.tabaska.us vhost is on disk but caddy was never reloaded; stash sends a literal {server_port}; deptrack.tabaska.us is a dead name/vhost. Configure HA trusted_proxies, reload caddy, prune dead routes.

**Resolves 6 findings:** `H8` llamaswap.tabaska.us vhost added to Caddyfile but caddy neve, `H9` ha.tabaska.us returns 400 Bad Request — HA rejects the proxy, `H18` llamaswap vhost added to Caddyfile on disk but caddy never r, `H19` ha.tabaska.us returns 400 Bad Request from HA — trusted_prox, `H21` ha.tabaska.us returns 400 for every request — HA has no trus, `M10` ha.tabaska.us is a dead path: caddy proxies to HA but HA rej

### `fix-33` 🟠 Unfreeze Miniflux (all 52 feeds excluded from polling) + remove leftover bootstrap admin
*host:* mini · *track:* apps · *severity:* high

Every Miniflux feed has been excluded from polling since 2026-07-09 — zero articles for 6+ days; a leftover CREATE_ADMIN bootstrap account still exists. Re-enable polling, remove the bootstrap account, add a "last successful feed refresh" check.

**Resolves 2 findings:** `H7` Miniflux silently frozen: all 52 feeds excluded from polling, `L23` Leftover bootstrap: CREATE_ADMIN creds still active in .env 

### `fix-34` 🟡 Fix AMP scheduled backups (silently failing) + backup-bloat in restic + playit UDP churn
*host:* rig · *track:* gaming · *severity:* medium

AMP Minecraft backups have silently failed since 2026-07-10 (backup-count limit + ReplacePolicy=DoNothing); 12G of frozen AMP zips in /opt are shipped off-site by restic; playit throws UDP-claim register errors ~daily. Fix retention policy, prune/exclude bloat, monitor tunnel health.

**Resolves 3 findings:** `H10` AMP scheduled Minecraft backups silently failing since 2026-, `M29` 12G of frozen AMP backup zips dominate /opt game data and ar, `M30` playit currently connected (3 tunnels, verified) but UDP reg

### `fix-35` 🟠 Immich: start real phone backups (empty library) + lock down the unused second admin
*host:* nas · *track:* photos · *severity:* high

Immich has ZERO assets — the mobile app was never paired, so no backup has ever flowed since the Jul 2 deploy; a second full-admin account (kaelyn92) has never logged in and both accounts are still flagged shouldChangePassword; server pinned behind latest. Pair devices, right-size the second account, add an "assets/backup freshness" check.

**Resolves 4 findings:** `H17` Immich contains ZERO assets — no phone backup has ever flowe, `H28` Root cause of zero assets: Immich mobile app was never paire, `I109` Immich pinned at v2.7.5 while the server's own update check , `M58` Second user (kaelyn92@icloud.com) was created with full admi

> **RESOLVED 2026-07-18** — upgraded v2.7.5 → **v3.0.3** live+repo while the DB was empty (I109; migrations clean, VectorChord digest unchanged, Valkey re-pinned; pre-upgrade dump taken; repo's hardened `${IMMICH_VERSION:?}` compose finally deployed live). Root cause H17/H28 re-confirmed (0 assets, 0 mobile sessions) — **pairing is deliberately deferred** (operator decision: prep now, pair later), guarded by two consumer-end checks in `nas-services.yaml`: `nas-immich-backup-freshness` (statistics API + on-disk original <7d, via new least-privilege `verification-monitor` key scoped `server.statistics`, vault `immich.verify_api_key`) and `nas-immich-mobile-paired` (≥1 iOS/Android session). Both warn **by design** until a phone pairs — the ntfy alert is the reminder. M58 **accepted**: kaelyn92 keeps admin intentionally; `shouldChangePassword` resolves itself at her first login. Runbook `wiki/docs/runbooks/photos.md` (pairing steps + rotation).

### `fix-36` 🟡 Home Assistant health: unavailable entities, dead integrations, pending updates
*host:* ha · *track:* smart-home · *severity:* medium

11 iPhone companion sensors + 8 Hue lights unavailable; a HomeKit client rejected from an off-subnet; dead Roomba/Matter integrations; HA Core/OS/Matter updates pending; /api/error_log now 404s (breaks scrapers).

**Resolves 5 findings:** `M9` HA Core 1 monthly release behind; HAOS two major versions be, `M11` All 11 iPhone companion-app sensors unavailable (only device, `M40` 8 of 71 Hue lights unavailable — 7 continuously since HA sta, `M41` HomePod<->hub gap: bridge is running and paired to 2 clients, `M42` 11 of 18 iPhone companion-app sensors unavailable since 2026

### `fix-37` 🟡 Media-aux service config fixes (navidrome backup, kometa, pinchflat/bgutil, RomM empty)
*host:* mini · *track:* media-polish · *severity:* medium

Navidrome nightly DB backup silently disabled (no path); Kometa MDBList 401 every run + dead config paths; pinchflat not wired to the bgutil POT provider and burning retries on impossible videos; RomM library completely empty.

**Resolves 4 findings:** `M14` YouTube bot-check failures on 2026-07-14 while pinchflat is , `M15` Nightly DB backup silently disabled: ND_BACKUP_SCHEDULE set , `M16` Kometa daily run completes but MDBList list fetches fail 401, `M18` RomM library is completely empty — 0 ROMs in DB, NAS games s

### `fix-38` 🟡 Reading/CWA: reconcile Kobo store-passthrough state + note fork-image supply-chain risk
*host:* nas · *track:* reading · *severity:* medium

CWA config_kobo_proxy=1 (store passthrough ENABLED) contradicts the documented intentional disable of 2026-07-09; CWA runs a fork image from a typosquat-style 7-month-old GitHub account; minor library junk (split authors, foreign editions).

**Resolves 3 findings:** `I68` CWA runs a third-party fork image ghcr.io/new-usemame/calibr, `L47` Library junk: split author identities, one duplicate title, , `M35` Kobo store passthrough is live-ENABLED (config_kobo_proxy=1)


## Wave 4 — hygiene, drift & cleanup (batchable)

### `fix-39` 🟡 mini host cleanup: dead Pterodactyl LEMP + root cron, broken crons, dead stack dirs, reclaimable docker
*host:* mini · *track:* docker-host · *severity:* medium

A dead Jun-2025 Pterodactyl LEMP+redis stack still runs a per-minute root cron; a btabaska cron executes a directory nightly; dead stack dirs (litellm/tdarr/maintainerr/dependency-track); ~9.3G reclaimable docker data; a failed one-shot timer; etckeeper index.lock races; dead SBOM pipeline; AppleDouble junk.

**Resolves 4 findings:** `M1` Dead Pterodactyl panel from Jun 2025 still runs a full LEMP+, `M2` etckeeper commits intermittently fail on /etc/.git/index.loc, `M3` One-shot media maintenance (unpackerr wedge clear) FAILED on, `M62` Broken daily cron entry '0 0 * * * /home/btabaska/bin' execu

### `fix-40` 🟡 NAS host hygiene: timezone drift, soularr parked import, core dumps, junk files, single-disk note
*host:* nas · *track:* nas-foundation · *severity:* medium

NAS timezone is US/Pacific vs the fleet Eastern (DSM schedules 3h off); soularr re-runs a parked failed import every 5 min; core dumps litter /volume1 root; macOS junk + .bak sprawl in service dirs; volumes are single-disk (no RAID) — a documented risk to reaffirm.

**Resolves 5 findings:** `M4` All three data volumes are single-disk with no RAID redundan, `M5` NAS host timezone is US/Pacific while the entire fleet + all, `M6` soularr parked on the same failed import for 5 days, re-runn, `M24` Soularr failed import parked since 2026-07-10, re-skipped ev, `M28` AdGuard-NAS healthy and genuinely used (52k queries/24h) but

### `fix-41` 🟡 Repo-vs-live drift codification (forgejo stack, manifests, .env keys, ansible units)
*host:* mini · *track:* ops · *severity:* medium

The forgejo control-repo stack runs live with NO repo mirror; compose-images manifest polluted by a stray .bak + phantom images; NAS compose copies diverged; 6 mini stacks have live .env keys missing from repo examples; ansible-pull.timer is an older revision. Reconcile repo ↔ live so rebuilds do not drop config.

**Resolves 4 findings:** `M48` forgejo stack (the ansible-pull control-repo server itself) , `M49` compose-images manifest polluted: junk libreseerr 'digest' c, `M50` NAS compose drift: calibre-web-automated repo copy stale (NE, `M51` .env key drift on 6 mini stacks: live-added keys missing fro

### `fix-42` 🟡 Make off-site DR reproducible (ansible backup role is a no-op diverged from live)
*host:* mini · *track:* backups-offsite · *severity:* medium

The ansible backup role is gated on a SOPS file that does not exist (no-op) and contradicts the live restic setup in several ways; hosts manifests exist only for macmini. Bring the role in line with live so DR is rebuildable from ansible.

**Resolves 1 findings:** `M52` Known issue 7 quantified: ansible backup role is a no-op (it

### `fix-43` ⚪ Repo junk & dead-path cleanup (tracked pycache, stale root files, worktree, retired-service remnants)
*host:* device · *track:* wiki · *severity:* low

Tracked __pycache__ .pyc; stale root files (agent-fix-tasks.md, keynote.html); a leftover detached-HEAD worktree; iCloud conflict dupes in wiki/docs; dependency-track/litellm phantom remnants across repo, homepage tiles, service-catalog and script comments.

**Resolves 24 findings:** `L1` Nightly SBOM->Dependency-Track pipeline is dead: timer disab, `L2` Orphan stack dirs with no running container (litellm, tdarr,, `L6` Scheduled 04:22 ansible-pull run failed on stale playbook pa, `L24` deptrack.tabaska.us is a dead path: in vault + wildcard DNS,, `L27` Forgejo docker json-log is corrupted (NUL byte) — `docker lo, `L52` deptrack.tabaska.us is a dead name: Dependency-Track retired, `L61` wiki-drift check FAILING in today's daily run: committed gen, `L68` Four compiled __pycache__ .pyc files are tracked in git desp, `L69` agent-fix-tasks.md is stale, superseded junk that still poin, `L70` keynote.html is an unrelated one-off ('Apple Hearth' marketi, `L71` Generated wiki roadmap index still claims it mirrors the ret, `L72` Four dead stack dirs on mini: dependency-track, litellm, tda, `L73` Dependency-Track fully retired live, but vault creds + 3 rep, `L74` Homepage LiteLLM tile still describes the phantom 'mini fall, `L75` service-catalog.yaml has no llama-swap entry and stale ollam, `L77` Published wiki roadmap shows a negative open count (ops trac, `L78` media-03/media-04 are 'REMOVED FROM PLAN — won't-do' but sit, `L79` Generated roadmap index still says it mirrors 'docs/index.ht, `L80` tracker-meta.json has no programmatic consumer and is alread, `L81` foss-analogue-progress-2026-07-05.json is a byte-identical d, `L82` Leftover detached-HEAD worktree .claude/worktrees/libreseerr, `L83` Two iCloud conflict-copy dupes live in wiki/docs and will be, `L85` Four orphan stack dirs with leftover .env but no compose (li, `L86` Installed ansible-pull.timer on both mini and rig is an olde

### `fix-44` ⚪ Tracker + wiki drift cleanup (stale generated pages, orphan ids, arithmetic, recurring wiki-drift red)
*host:* device · *track:* wiki · *severity:* low

Committed generated wiki pages are stale vs regeneration (keeps the daily wiki-drift check red); orphan done id nas-00e; status-classification nits; tracker-meta missing the ai track; duplicate/backup json files; negative open count + todo.md arithmetic.

**Resolves 4 findings:** `M22` Real wiki drift on main: 2 generated script-doc pages are st, `M46` Orphan done id nas-00e — closed in progress.json but the tas, `M47` Committed wiki man-page for publish-deploy.sh is stale — doc, `M55` wiki-drift failing since the 2026-07-15 daily sweep — commit

### `fix-45` ⚪ Fleet hygiene batch: host junk, core dumps, stale caches, log/backup bloat (mini/rig/seedbox)
*host:* mini · *track:* docker-host · *severity:* low

Cross-host low-severity cleanup: 131G extracted leftovers + 1.7G stale *arr tmp on the seedbox, 17.9G unreferenced GGUFs on rig, dangling OWUI RAG rows, truncated journald history, corrupted docker json-logs, #recycle bloat. Batchable, non-urgent.

**Resolves 65 findings:** `L3` Verification units exit 1 on any warn/crit check, then the n, `L4` macOS junk (.DS_Store, ._AppleDouble files) and a test artif, `L5` .bak backup copies accumulating alongside live scripts and c, `L7` Persistent journal history truncated to 2 boots (~46.5M, old, `L8` ~1.7G of dead *arr self-update/backup dirs and orphaned dotn, `L10` deluged.log is 0 bytes — daemon error logging effectively di, `L11` 8 of 73 Hue lights unavailable (integration itself healthy), `L12` Error log is quiet: only 15 entries since ~06-27, all transi, `L13` Stale UI clutter: 1 week-old failed-login notification (mini, `L14` Libreseerr request status only refreshes on UI-driven POST /, `L15` Navidrome indexes the Synology #recycle bin of the music sha, `L16` 70 tracks flagged missing in Navidrome DB (whole Chappell Ro, `L17` Kometa config dead paths: nonexistent 'Anime' Plex library, , `L18` 3 Oban retry jobs at attempt 18/20 grinding on permanently-i, `L19` Leftover empty /opt/stacks/pinchflat/downloads directory (re, `L20` ~14h docker-DNS outage window on mini 2026-07-08 21:18 -> 20, `L21` Wallabag past incident (resolved): ~2 days of per-request CR, `L22` Mealie docker log file corrupted with NUL bytes — full-histo, `L25` Homepage siteMonitors false-negative on Sunshine/Apollo (sel, `L26` stash vhost sends literal '{server_port}' as X-Forwarded-Por, `L28` Beszel email notifications are a dead path: user_settings li, `L29` Uptime-kuma 16h uptime explained: clean operator restart 202, `L30` NAS system timezone is US/Pacific (PDT) while the fleet stan, `L31` Radarr health warning: update available (only non-empty heal, `L32` Single wanted/missing album stalled 5 days: The Marshall Mat, `L33` 45 unmapped folders in /movies root — untracked junk: '- Cop, `L34` 25 unmapped folders in /tv root, incl. loose per-episode rel, `L35` Whisparr effectively inert (1 series, zero lifetime history), `L36` Plex credits detection failing on ~31% of items with 'incomp, `L37` Stale core dumps at /volume1 root incl. Plex Transcoder (Jul, `L38` Dead crontab entry on mini executes a directory nightly: '0 , `L39` Residue from this morning's RAG recovery: 239 dangling knowl, `L40` ~17.9GB of unreferenced GGUFs sitting in /opt/llm/models out, `L41` Apollo healthy and auth works, but journal shows constant Av, `L43` Junk/unmanaged content in library roots: ~45 unmapped folder, `L44` Navidrome indexes the Synology recycle bin: 2 deleted YouTub, `L45` Junk empty duplicate album folder '/volume1/music/Eminem/The, `L46` Ghost duplicate albums in Navidrome DB: 4 missing albums / 7, `L48` Pinchflat burning retries on 3 permanently-impossible member, `L49` MeTube manual downloads work, but every audio file it ever p, `L50` //nas/youtube #recycle holds 1357 deleted video files consum, `L51` Five process core dumps sitting at /volume1 root, including , `L54` Secondary AdGuard (NAS) forwards to Quad9 DoH instead of an , `L55` stash vhost sends literal '{server_port}' as X-Forwarded-Por, `L56` Rig restic fresh and nightly-consistent (0.19.1, dailies 07-, `L59` NAS timezone is US/Pacific while the fleet/operator timezone, `L60` Crash core dumps littering /volume1 root: qbittorrent-nox (x, `L62` macOS AppleDouble junk files shipped to /opt/verification (b, `L63` Fast-tier dead-man ping URL is not recorded in the secrets v, `L64` Dead path: Roomba (192.168.10.231) onboarding failed with ba, `L65` Matter server + integration loaded with ZERO devices/entitie, `L66` Pending updates: HA Core, HA OS and Matter Server all have u, `L67` /api/error_log (and /api/error/all) return 404 on core 2026., `L76` Two scripts still cite the retired handoff docs as their rat, `L84` Two junk cron entries execute nothing useful: btabaska runs , `L87` Stale vault entry (deluge.port 58846 vs live 3254) and hosts, `L88` Fast-tier ntfy pages are titled 'Verification [None tier]' —, `L89` Scheduled quick tier runs with --host (operator-override sem, `L90` skills/ is live (consumed by llm_triage.py) but carries stal, `L91` README materially stale (LLM endpoint, 'Known state 2026-07-, `L92` Confirmed: no [[whisparr]] block in unpackerr.conf although , `L93` Seedbox residue: ~20 extraction leftovers delete_delay never, `L94` Unpackerr liveness is invisible to every external monitor: p, `L95` 2 monitored Sonarr series sit on the unmanaged 'Any' quality, `M8` 131G of extracted/renamed media leftovers accumulating in ~/
