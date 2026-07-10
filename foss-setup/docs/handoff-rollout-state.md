# Rollout handoff state

### Radarr collections fixed + rclone retune staged + WINDOW JOB SCHEDULED 08:30 UTC 07-11 (2026-07-10 late afternoon)

- **Radarr misconfig FIXED (live, non-disruptive)**: the 11 movie collections pointing at nonexistent `/data/movies` (migration leftover, surfaced by the new radarr-pipeline check) repointed to `/movies` via 11 individual `PUT /api/v3/collection/{id}` (202s; individual PUTs preserved each one's own qualityProfileId — a bulk update would have clobbered them). All 93 collections now on `/movies`; `MovieCollectionRootFolderCheck` health error gone. Only remaining Radarr health = the transient IPT indexer backoff (query-cap self-heal).
- **rclone mount RETUNE staged (NOT yet applied — needs a remount = window)**: the mount script was tuned for the DS920+'s old 4 GB; it now has ~20 GB. Changed `--vfs-cache-mode minimal→full` (+`--vfs-cache-max-size 50G` +`--vfs-cache-max-age 24h`), `--dir-cache-time 1m→3m`, `--buffer-size 32M→64M`. `full` caches file DATA locally so Sonarr's repeated reads + the import-copy stop re-fetching over SFTP (the network-read-under-SQLite-lock that drove the freezes). Architecture kept deliberately (a SEEDING seedbox needs a live read-mount; rsync/Syncthing would clone the 9.9 TB seed set or break seeding). Repo + NAS on-disk updated (backup `rclone-seedbox-mount.sh.bak-preretune`); the RUNNING mount keeps old flags until remounted.
- **WINDOW JOB scheduled — `media-window-maint.timer` on mini fires 2026-07-11 08:30 UTC (04:30 ET)**. Script `scripts/media/window-maint-unpackerr-rclone.sh` (deployed `/opt/verification/bin/`, runs as btabaska for the `nas` alias). Two GATED phases, ntfy at every step, `fail()` stops + high-priority pages naming the step (no silent 4AM outage):
  - **Phase A**: `systemctl restart pkg-ContainerManager-dockerd.service` (the confirmed DSM 7.2 dockerd unit; synopkg not in sudo PATH) → clears the unpackerr wedge (bounces all 23) → `docker compose up -d` recreates unpackerr WITH the healthcheck+webserver → verifies unpackerr `healthy`.
  - **Phase B** (only if A passes): lazy-unmount + remount rclone with the retuned flags → verify listable → `compose restart sonarr radarr lidarr readarr unpackerr` to rebind the fresh mount → verify sonarr sees `/seedbox/tv` end-to-end.
  - Self-cleans (disables its own timer on success). **DRY_RUN=1 tested green** (pre-flight 23 containers, both staged configs detected, ssh/sudo/ntfy paths work). **If it pages FAILED overnight, inspect before re-firing; log `/var/log/media-window-maint.log` on mini.** Concurrent session: heads-up, this bounces all NAS containers ~04:30 UTC-4.
- Note: media tier (`--host media --notify`) already runs hourly in verification-quick.service → the 5 new checks + music-dupes run every hour; transition-based paging means the known music-dupes won't re-page.

### *arr import-pipeline monitoring (job-level, not container-level) + unpackerr healthcheck staged (2026-07-10 afternoon)

- **Hardening #1 DONE (live, verified)** — 5 checks added to `checks.d/media.yaml` (domain `media`, hourly via the quick tier). They probe the pipeline's FUNCTION so the healthy-container/dead-job class (musicseerr, soularr, unpackerr — all "Up" while broken) can't hide:
  - `sonarr-queue-stuck` / `radarr-queue-stuck` (warn): >5 items stuck in `trackedDownloadStatus=warning` → catches a dead unpackerr / dead mount / broken mapping a day before a human notices. Tool-agnostic. THE canary.
  - `sonarr-pipeline-health` / `radarr-pipeline-health` (warn): Sonarr/Radarr `/health` for DownloadClient/RootFolder/RemotePathMapping/ImportMechanism sources only (re.match ANCHORS at start → excludes indexer-availability flap AND MovieCollectionRootFolderCheck).
  - `seedbox-mount-listable` (crit): the rclone SFTP mount — the shared SPOF — lists within 15s (catches stale/hung FUSE handles a `mount|grep` misses).
  - Keys `SONARR_API_KEY`/`RADARR_API_KEY` added to mini `/etc/verification/env` (vault `arr_api_keys.*`, via stdin not argv). host:url checks curl nas over LAN; mount check is host:mini→ssh nas sudo.
  - **Caught two REAL issues on first run** (checks earning their keep, like the fleet/music ones): (a) **Radarr misconfig** — 11 movie *collections* point at root `/data/movies` which doesn't exist in-container (stack uses `/movies`); leftover from the Ubuntu→NAS migration (`MovieCollectionRootFolderCheck`). Scoped OUT of the pipeline check (different subsystem) but **needs a real fix**: repoint or remove those collections. (b) the concurrent session's `music-library-dupes` flagged a genuine new dupe `mgk lost americana` vs `…(2025)` — their workstream, left alone.
- **Hardening #4 STAGED (not yet live — coupled to the unpackerr recreate)** — `[webserver] metrics=true listen :5656` added to `unpackerr.conf` + a compose `healthcheck` wget-probing it (repo + NAS on-disk, compose validates). A fully-wedged unpackerr stops answering HTTP → container `unhealthy` → existing `containers-health-nas` pages. **Activates when unpackerr is recreated** — which needs the **NAS dockerd restart (window)**: confirmed today that `docker rm -f unpackerr` TIMES OUT (exit 124) — the wedge is unremovable without a daemon bounce (ctr task-delete didn't reconcile dockerd's view). Fleet verified intact after the failed rm (23 up, none unhealthy). **Interim coverage is live**: `*-queue-stuck` catches the symptom regardless.
- **Window task (unchanged, now also applies #4)**: restart NAS dockerd (bounces 23 containers, 4-7AM) → `cd /volume1/docker/media-automation && docker compose up -d` → unpackerr comes back healthy WITH the webserver+healthcheck. Verify: `docker inspect unpackerr` shows healthy + it extracts the backlog.
- **Noted, pre-existing (not fixed)**: `unpackerr.conf` carries the four *arr API keys in PLAINTEXT in the repo — a secret-hygiene gap (they're not .env-referenced like other secrets). Flag for a rotation/vault pass.

### Music library dedup + duplicate tripwire + NAS→rig mirror (2026-07-10 midday)

- **3 duplicate album folders removed from the NAS master** (pre-Lidarr manual copies coexisting with Lidarr's year-suffixed folders): Olivia Rodrigo GUTS + SOUR, Chappell Roan Midwest Princess. Deleted the no-year orphans (verified media-only contents first, and that Lidarr's DB indexes ONLY the year-suffixed folders → invisible to pipeline). ~460MB reclaimed; orphans were mostly lower-quality (SOUR orphan 69MB lossy vs 193MB FLAC kept).
- **Duplicate-library TRIPWIRE** `verification/bin/music-dupes.py` + check `music-library-dupes` (checks.d/media.yaml, host mini against ro CIFS `/mnt/nas/music`): normalizes each artist/album folder (NFC-unicode → strip trailing `(YYYY)` → casefold) and fails listing any collision. Skips `#recycle`/`@eaDir`/`YouTube`. Fails LOUDLY if mount empty (no vacuous pass). Negative-tested: caught all 3 dupes pre-deletion (exit 1), went DUPES_OK albums=63 after. Hourly via new `--host media` line in verification-quick.service. Rationale: Lidarr is the single door and can't dup itself, so any collision = something wrote around Lidarr.
- **NAS→rig music mirror** `configs/host/rig/music-mirror/{service,timer}` (daily 05:30 ET): `rsync -rt --delete-after` from `/mnt/nas-music-ro/` → `~/Music/` makes the Rhythmbox/iPod source a true mirror (additions AND deletions propagate → no drift/dupes downstream). `-rt` not `-a` (CIFS has no owners/symlinks). Dead-manned healthchecks `music-mirror-rig` (vault `healthchecks.music_mirror_rig_ping_url`). First runs applied the dedup to `~/Music` (SMB cache lagged one run; now consistent across NAS/mini-mount/rig-mount/rig-local). NOTE the NAS `YouTube/` (beets rips) DOES sync to rig — user may want excluded.
- **iPod**: still needs a one-time wipe+resync from the now-clean `~/Music` (runbook `scripts/media/ipod-sync-cachyos.md`), user-driven.
- Fixed stale `alert-healthchecks-checks-defined` (hardcoded `[6-9]` ceiling; now 10 dead-mans → floor regex). Sweep 76/76.

### Sweep back to 75/75 + alerting hardened (root-guard, transition paging, acks); AMP licence RCA'd to random MACs (2026-07-10 midday)

- **User was being re-paged for the same 4 failures** (alert-kuma-none-down, git-stacks-clean, playit-java/bedrock-public) and mandated fix + hardening ("failures like this are unacceptable"). All four cleared; full sweep **75/75**, one "all recovered" ntfy confirmed sent. Two of today's pages were agent-inflicted (a root sweep → 14 false failures incl. 3 fake crits; see hardening below).
- **Rig Minecraft down RCA**: nightly ansible-pull converge (glue-08) applied daemon.json log-caps/pools on the RIG at 04:35 → one-time docker daemon restart (same one-time propagation mini had on 07-09; checked journals — NOT nightly) → **docker 26+ assigns a NEW RANDOM MAC on container (re)start and AMP's licence fingerprint includes it → NoMatchingMachineId** on BOTH instances; MinecraftCross01 crash-looped `exit 32 (NO_LICENCE)` at boot (Start-on-Boot flag was fine all along; the hostname pin alone was insufficient). **Fix**: `mac_address: 5e:c4:36:bf:b4:43` pinned in rig `/opt/stacks/amp/compose.yaml` (container recreated) + BOTH instances reactivated (`docker exec -u abc amp ampinstmgr reactivate <inst> <key>`, vault `cubecoders_amp.license_key`). Verified: Paper 26.1.2 answers mc-status-ping on LAN, Kuma "Rig Minecraft Java" up 14:41Z. Repo mirror `configs/gaming/amp/compose.yaml` updated. **Pattern: ANY docker-restarting event on the rig used to nuke the AMP licence — now identity (hostname+MAC) survives restarts and recreates.**
- **git-stacks-clean**: 9 macOS AppleDouble `._*` files in /opt/stacks (8 silently TRACKED for who knows how long); purged, `._*`/`.DS_Store` gitignored, committed+pushed (docker-stacks `a440c3b`). Complements the runner's dotfile-skip from the morning session.
- **Alerting hardening (deployed to mini, repo + runbook updated)**:
  1. `run-checks.sh` now **REFUSES to run as root** (exit 2, nothing runs, nothing pages) — the old warn-and-continue paged that fake 14-failure outage and poisoned the state diff; `VERIFY_ALLOW_ROOT=1` for deliberate root runs.
  2. `checks_runner.py` pages on **transitions only** (NEW failures / recoveries, per tier via its own state file); an unchanged persistent failure set no longer re-pages hourly. The unfiltered daily sweep still pages while anything fails — one reminder/day, nothing rots silently.
  3. **Ack mechanism** for known/accepted outages: `ack-check.sh <id> <hours> [reason]` / `--list` / `--clear` (state `/var/lib/verification/acks.json`, auto-expiry). Acked checks keep running + recording, just don't page. **playit-java-public + playit-bedrock-public acked 24h (to 07-11 ~14:45Z)** for the user-confirmed upstream outage — they flap pass/fail as playit's claim leg degrades (both PASSED in the 14:50Z sweep). Clear early with `--clear` once playit confirms recovery.
- **Sonarr fixes APPLIED (user-approved) — see the dedicated entry below.**

### Sonarr queue drained 20→0 + IPT query cap; unpackerr wedge worked around (2026-07-10 midday³)

- **Queue 20→0, all imported and verified on disk.**
  - **Archer S04 season pack (13 rows)**: files named `01 Title.mkv` → Sonarr couldn't map them. Manual-imported via `POST /api/v3/command` `ManualImport` (mapped by leading number → episodeIds 27708–27720, `importMode: copy`, S04 Extras skipped). All 13 in `/volume3/tv/Archer (2009)/Season 04/`, renamed, full Bluray sizes (`hasFile` 13/13).
  - **7 rar'd releases** (Archer S10E03/E04/E07, S12E01/E05, S13E01, Hacks S01E01): extracted MANUALLY on betty (`unrar x` per `~/files/tv/<release>/`) because unpackerr was wedged; Sonarr auto-imported all 7. **Cleanup owed on betty**: the extracted `.mkv`s now sit beside the seeding rars (derived, NOT in the torrent → safe to delete; unpackerr's delete_delay normally does this).
  - **unpackerr wedge (root cause, PARTIAL fix)**: pid 1448 hung; `docker restart/stop/inspect` all HANG against it (DSM containerd task stuck STOPPED, dockerd won't reconcile). Killed pid + `ctr task delete` (137) but dockerd still says "Up 2 days" → **needs a full dockerd restart on the NAS (bounces 23 containers) → deferred to 4-7AM window** unless waived.
- **IPT query cap LIVE + already firing correctly**: Prowlarr idx1 `queryLimit=600/day`, `grabLimit=50/day`. Measured trailing-24h = **1,563 queries (2.6× cap)** from repeated overnight Search-Alls → Prowlarr now 429s IPT, Sonarr health = "all indexers unavailable". **This is the cap WORKING**; self-heals as the 00:42–04:58 EDT burst ages out of the 24h window (~clear 01:00 EDT 07-11). RSS paused till then; steady-state IPT RSS (~250-400/day) fits under 600.
- No new SQLite `database is locked` since the queue cleared (the 6 are all 04:51–05:07 this morning); ProcessMonitoredDownloads back to **0.1s** (was 25-28s/min with the clog) → freeze pressure gone.
- **Hardening writeup delivered to user (see next session / their decision):** (1) 2nd TV indexer is the real fix — IPT alone can't fill the 832-ep backlog (Search-All returns ~0, and it's what triggered the 2.6× burst); (2) job-level arr-pipeline checks — proposal in scratchpad `arr-pipeline-checks-proposed.yaml`, **fold into the concurrent session's new `checks.d/media.yaml`** (queue-stuck, health-clean, db-not-locked, mount-listable); (3) stop using Search-All on big backlogs; (4) unpackerr full restart in-window + consider the healthcheck the compose lacks.

### Soularr import leg fixed + backlog drained; runner hardened; playit upstream OUTAGE ongoing (2026-07-10 morning)

- **Soularr fixed and validated end-to-end**: `[Slskd] download_dir` was betty's local path (nonexistent in-container) → every completed download crashed the run at import; broken since the 07-02 deploy, zero alerts (healthy container, dead job — same class as musicseerr). Fix: `download_dir = /seedbox/slskd` (backup: config.ini.bak-wrong-path). Watched live: mgk ×3 + Eminem imported through Lidarr's DownloadedAlbumsScan; overnight the whole stranded backlog drained to "No releases wanted". One album (MMLP soulseek copy) ended "Skipping failed import" after a junk .m3u requeue loop — bounded, correct. Stranded leftovers on betty `~/files/slskd` = disk cruft, clean opportunistically.
- **New job-level check `soularr-not-crashlooping`** (docker-fleet.yaml): greps 2h of soularr logs for "Fatal error" — catches the healthy-container/dead-job class hourly.
- **Verification runner hardened, two real bugs**: (1) `subprocess` strict UTF-8 → one bad byte in any check output kills the sweep — now `errors="replace"`; (2) macOS AppleDouble junk (`._mini-services.yaml`, binary) in checks.d crashed yaml load — **the sweep was dead ~13h overnight and the `verification-quick-mini` dead-man CAUGHT it** (phone alert ~01:15). Loader now skips dotfiles; junk file removed. If scp-ing checks from a Mac, watch for `._*` droppings.
- **Failed-unit checks earned their keep on first real run**: rig `restic-backup.service` failed (stale repo lock from 07-09 15:22 interrupt) → `restic unlock` + rerun = success, backup window recovered. mini `etckeeper.service` = transient index.lock races with the concurrent docs session's /etc commits — reset, not a defect, may recur while both sessions run.
- **PLAYIT UPSTREAM OUTAGE (unresolved, not ours)**: the claim-leg degradation from last night progressed to hard failure — agent control plane fine, tunnels "loaded", but claim host 69.9.181.2:4378x drops ~50% of TCP connects (measured from mini AND rig; WAN 0% loss incl. to the edge IP) and ALL end-to-end game pings fail. Container restart (last night's fix) no longer helps. playit status page still green. Friends cannot join Java or Bedrock. Checks `playit-java-public`/`playit-bedrock-public` correctly red. ACTION: report to playit support (evidence above); re-test periodically — nothing fixable locally.
- git-stacks-clean failing = concurrent docs session's WIP on mini /opt/stacks (theirs to commit).
- **Playit outage fallout**: user couldn't join Palworld from HOME — palworld.tabaska.us LAN rewrite deliberately points at the playit edge (:1105 only exists there), so the outage broke local play too. Workaround deployed: `ufw allow from 192.168.10.0/24 to any port 8211 proto udp` on rig + direct connect `192.168.10.12:8211`. Consider documenting the direct-connect fallback on the address card. **Palworld 1.0 auto-update landed clean overnight** (v1.0.0.100427, Robits Farm healthy) — the update playbook from the 07-09 session was not needed.

### MusicSeerr "Couldn't sync the library" — v1.4.2 crypto bug, fixed via env key (2026-07-10 early)

- **Symptom**: library sync Failed since 07-09 00:37, search dead, yet settings page said "Connected to Lidarr". Logs: every Lidarr call 401, circuit breaker 'lidarr' stuck OPEN (which is what killed search).
- **Root cause (confirmed in app code)**: musicseerr v1.4.2 half-shipped encryption-at-rest — saving settings encrypts `lidarr_api_key` in config.json (Fernet, `config/.env` DATA_ENC_KEY), but `core/config.py load_from_file()` never decrypts, so after any restart the app literally sends the ciphertext as the API key. The UI "Test" validates the plaintext form value → false green. Reproduced deterministically: plaintext in file = works, encrypted = 401s.
- **Upstream is a dead end**: project rebranded to DroppedNeedle in v2.0.0 and REMOVED Lidarr support entirely (native library instead). v2 is a migration decision (affects the lidarr+soularr+slskd pipeline), not an upgrade. Pinned at v1.4.2.
- **Durable fix**: `LIDARR_API_KEY` env var (pydantic BaseSettings reads it) + key REMOVED from config.json — file loader only overrides keys present in the file. Compose + stack `.env` on mini (gitignored), mirror synced, vault `lidarr.api_key` added. Restart-tested twice: all 200s. **Gotcha: if anyone re-saves the Lidarr settings page in the UI it writes an encrypted key back into config.json which would override the env on next restart — delete `lidarr_api_key` from config.json again if MusicSeerr breaks after a settings save.**
- Backups left in place: `config.json.bak-encrypted-key` (pre-fix state).

### SESSION CLOSE — monitoring at 100% surface; NEXT MANDATE: documentation debt sweep (2026-07-09 night²)

- **Monitoring session closed at 74/74 sweep, 53 Kuma monitors all up, 9 healthchecks dead-mans all up.** User confirmed alert receipt and signed off on the coverage matrix (every container/native unit/job/network path — see the three entries below for the full architecture: layered AI-stack coverage → playit protocol pings → fleet manifests+tripwire).
- **USER MANDATE for the next session**: full documentation audit — "documentation tech debt is equally concerning to no monitoring." **The LIVE service stack is the source of truth**; docs must be corrected to match reality (not vice versa), except where live state is itself a known defect (then it's a task, not a doc fix).
- **Known drift found this session (seed list for the audit)**: wiki/docs/hosts/rig.md said "LiteLLM on the mini, fleet-wide front door + fallback model" — never existed; litellm runs on the rig, and mini's /opt/stacks/litellm dir is an orphaned never-deployed stack (decide: deploy-as-fallback or remove + doc). checks.d/rig.yaml header claims "mini->rig SSH blocked by tailnet ACL" — stale, LAN ssh works and host:rig checks run. Older handoff/audit docs still describe Kuma as 50 liveness monitors / daily-only sweep. seed-monitors.sh comments predate the premium SRV:1105 discovery. tdarr/maintainerr (inert), frigate (undeployed stack dir), SBOM/dependency-track (retired but dtrack containers still run on NAS + stack docs remain) — reconcile each: retire fully or document why kept.
- Session cleanups already done: hung beets one-off removed (nas), sbom-nightly disabled+reset (rig), stale kuma playit TCP monitor deleted.

### 100% surface coverage: fleet manifests + tripwire, every container/unit now monitored (2026-07-09 late⁴)

- **User mandate**: "100% surface coverage across every service. If anything stops working I need to know. Period." Full inventory (71 containers on mini 38 / nas 23+1 stuck / rig 8, plus native units) diffed against all monitoring: ~25 port-less workers and sidecars had ZERO coverage (beets, kometa, soularr, unpackerr, diun×2, bedrock-connect, bgutil-pot, rreading-glasses, every db/redis/tika sidecar), plus 3 unmonitored web UIs (RoMM, AMP panel, Synology DSM) and recyclarr's weekly cron whose failures went only to a log file.
- **Blanket mechanism, not 30 hand-made monitors** — `checks.d/docker-fleet.yaml` (domain runs hourly via quick tier + daily; state file results-docker-fleet.json):
  - per-host MANIFEST check: running containers must equal `verification/coverage/<host>.containers` (repo + mini:/opt/verification/coverage/). Catches any crashed/stopped container by name AND any NEW un-manifested container — the tripwire that keeps coverage at 100% as the fleet grows. **Deploy/retire a service ⇒ update the manifest** (runbook updated).
  - per-host HEALTH check: no unhealthy or restart-looping containers (broken-but-running class).
  - `systemd-failed-{mini,rig}`: any failed native unit fails the sweep.
  - NAS access: `NAS_SUDO_PASSWORD` added to mini /etc/verification/env (vault sudo.nas_password); rig via mini→rig LAN ssh. `LC_ALL=C sort` everywhere (mac/linux collation differs — bit me once).
  - **Negative-tested**: stopped diun → both mini checks failed naming it → restarted, state reset cleanly.
- **Kuma +3** (53 active, all up): Mini RoMM :8998, Rig AMP panel :8080, NAS DSM :5000 (`add_web` section in add-functional-monitors.sh).
- **recyclarr weekly cron dead-manned**: healthchecks `recyclarr-sync-mini` (timeout 7d, grace 1d, vault `healthchecks.recyclarr_sync_mini_ping_url`), crontab now curls the ping after successful sync; armed with an initial ping.
- **Cleanups**: removed a HUNG beets one-off on nas (`media-automation-beets-run-*`, `beet version` stuck "Up 33 hours" — compose-run leftovers are excluded from manifests via `-run-` filter, but watch for these hanging); disabled+reset retired `sbom-nightly.timer` on rig (was the only failed unit in the fleet, SBOM retired in audit f9251f9).
- **Deliberately NOT covered (documented)**: job-level failures inside long-running workers (kometa's nightly run, beets imports — container up, job failing; needs log scraping/exit-hook work); Synology native pkg failures (DSM self-manages; Beszel watches host vitals; DSM web UI now Kuma-monitored); seedbox = Deluge+slskd Kuma only (no root on betty); Palworld public UDP path (REST covers the server, playit-bedrock-public is the UDP-tunnel canary). And the standing SPOF: all alerting lives on mini — HA-based external watcher still recommended (user decision pending).

### Playit tunnel: wedged TCP claims found + fixed by the new checks; upstream claim degradation ongoing (2026-07-09 late³)

- **The new public-path probing immediately caught a REAL silent outage**: Java public path (69.9.181.17:1105) dead — TCP connects accepted by the edge but real MC status pings timed out. Agent logs: "timeout connecting to claim address" per connection while claiming "connected; tunnels loaded, 0 pending". **The known UDP claim-wedge gotcha applies to TCP claims too**; `docker restart playit` fixed it. Every local check and playit's own dashboard stayed green throughout — nobody could join while everything looked fine.
- **Port monitors are structurally useless against the playit edge**: connects are accepted even when claims are wedged, and 25565 there is hostname-routed (`*.mcjoin.link`) so bare probes flap. Removed the Kuma TCP monitor (added earlier this session, wrong tool); replaced with REAL protocol pings in the sweep url tier (hourly + daily): `playit-java-public` (MC handshake+status via `mc-status-ping.py`) and `playit-bedrock-public` (RakNet unconnected ping via `mc-bedrock-ping.py`), both `scripts/gaming/` → deployed to mini `/opt/verification/bin/`.
- **ONGOING upstream degradation at session close**: playit's claim leg (69.9.181.2:43782, DC 41) drops ~50% of connection attempts — measured from BOTH mini and rig; our WAN is 0% loss incl. to the edge IP itself; playit status page green. Friends' Java AND Bedrock joins are coin-flip-per-attempt tonight (Palworld likely same mechanism). Nothing fixable locally — worth reporting to playit if it persists. The sweep checks retry 4× and page only on hard outage; the try-count in check output shows degradation without alert flapping.
- url tier now 9/9 (both public paths pass within retries). Kuma back to 50 active monitors, all up.

### Monitoring gap audit after the UFW incident — layered functional coverage + a second silent failure found (2026-07-09 late²)

- **User mandate**: no more silent regressions — audit every monitoring layer, make the UFW class impossible to miss. Findings: Kuma's 50 monitors were ALL liveness (port/200/ping, zero keyword checks); the deep sweep ran once daily 07:15 PT; Beszel = metrics only; Healthchecks = cron dead-mans only. Nothing probed function, and nothing probed from inside the rig.
- **SECOND SILENT FAILURE FOUND during the alert-path test**: Healthchecks' ntfy notifications had NEVER fired — every dispatch errored "Connections to private IP addresses are not allowed" (Django blocks private-IP integrations by default; `api_notification` table full of failures incl. same-day real flips). All 6 dead-man checks were decorative. **Fixed**: `INTEGRATIONS_ALLOW_PRIVATE_IPS=True` in healthchecks compose (recreated, mirrored to repo + /opt/stacks committed). Verified: recovery notification dispatched with empty error; user's phone got a labeled "ai-stack-rig UP" test.
- **New layered coverage (all deployed + verified)**:
  - `ai-stack-watchdog.timer` **on the rig** (every 10 min): probes container→host ollama from INSIDE open-webui (the only vantage that sees the UFW hop), pings Healthchecks `ai-stack-rig` (timeout 10m/grace 25m), `/fail` with diagnosis on breakage → ntfy. Zero GPU. Files: `configs/host/rig/ai-stack-watchdog/`, env `/etc/ai-stack-watchdog.env` (vault `healthchecks.ai_stack_rig_ping_url`).
  - `verification-quick.timer` **hourly** on mini (`--host url --notify`, runner patched with `--notify` flag + per-tier titles; ad-hoc filtered runs stay silent). Own state file, own Healthchecks dead-man `verification-quick-mini`. First run 7/7.
  - **Kuma keyword monitor** "Rig LiteLLM models (auth)": GET /v1/models with a SCOPED litellm virtual key (vault `litellm.kuma_monitor_key`, alias kuma-monitor, models chat+utility — not the master key), keyword `"chat"`, 60s → catches "no models"/config/DB/auth breakage in ~1 min. + "Playit Java public (69.9.181.17)" TCP 25565 300s — the friends' path; local port checks stay green when the playit tunnel dies (same silent-gap class). Script: `scripts/uptime-kuma/add-functional-monitors.sh`. Both UP.
  - **Healthchecks project API key generated** (was never set, length 0 — API unusable before): vault `healthchecks.api_key`.
- **Detection envelope now**: UFW/container→host class ≤ ~35 min (watchdog) · litellm "no models" class ≤ ~4 min (Kuma keyword) · any url-tier functional break ≤ ~1h (quick sweep) · deep/backup/etc daily. Alert paths: Kuma→ntfy (proven), runner→ntfy (proven), Healthchecks→ntfy (proven NOW, was broken since deploy).
- **Known remaining gaps (recommendations, not deployed)**: (1) mini is the alerting brain (Kuma+ntfy+Healthchecks+Beszel all on it) — if mini dies, silence; recommend an HA automation (separate host .50 + companion-app push) pinging mini, or a free external service (healthchecks.io/UptimeRobot) — user decision, and HA is the concurrent Run 5 session's turf. (2) UDP public game paths (Bedrock :1111, Palworld :1105) unprobed — Kuma gamedig could work, untested, parked to avoid alert flapping. (3) wiki drift: mini "fleet front-door LiteLLM + fallback model" was never deployed (stack dir exists, container never created) — real litellm is rig-only; triage `LLM_BASE_URL` already points at rig ollama directly. (4) `rig-ai-e2e`/watchdog flake vector: NUM_PARALLEL=1 queueing behind a long user generation — both have retry/grace headroom, but a >25-min continuous generation could false-fire the e2e (not the watchdog — it does no inference).
- Runbook `wiki/docs/runbooks/verification.md` updated: two-tier design + "probe what the user experiences / which vantage point sees this break" principle.

### ai.tabaska.us "no models" — rig UFW blocked docker→host ollama; fixed + new e2e check (2026-07-09 late)

- **RCA**: the 07-09 rig UFW hardening ("scoped to LAN+tailnet, dropped Anywhere rules") silently cut off docker containers → host-native Ollama. Containers (open-webui, litellm) reach `host.docker.internal:11434` from `172.19.0.x`; with INPUT default-deny and only `192.168.10.0/24` + `100.64.0.0/10` allows on 11434, that traffic dropped. Open WebUI's model list came up empty while **every external port probe stayed green** (sweep was 63/63 the whole time — the broken hop was container→host, which nothing tested).
- **Fix (live + persistent)**: `ufw allow from 172.16.0.0/12 to any port 11434 proto tcp comment "docker containers -> host ollama"`. Verified: owui container fetches all 17 ollama models; litellm completion returns; ai.tabaska.us 200. Rule of thumb now in `wiki/docs/hosts/rig.md`: any host-native service that containers must reach needs its own `172.16.0.0/12` allow.
- **New check `rig-ai-e2e`** (checks.d/rig.yaml, deployed to mini): real chat completion through litellm→ollama using `LITELLM_MASTER_KEY` added to mini `/etc/verification/env` (from vault `litellm.master_key`). Flake note: NUM_PARALLEL=1 means a busy GPU can queue past the 50s budget (saw one timeout while the user's 23GB model was generating) — retry before calling it an outage. url-subset sweep 7/7 after fix.
- **Pre-existing noise, not fixed**: open-webui logs a 401 "missing bearer" on an enabled-but-unconfigured default OpenAI connection (`OPENAI_API_BASE_URL`/`OPENAI_API_KEY` env empty, nothing in DB config). Harmless — models come via the direct Ollama connection. Optional cleanup: set `ENABLE_OPENAI_API=false` (needs container recreate) or point it at litellm with the master key to expose the curated `chat/code/utility` aliases in the UI.
- Also noticed while in there: `wiki/docs/hosts/rig.md` said "LiteLLM on the mini" — live reality is litellm runs on the rig (container, port 4000). Not corrected beyond the new UFW section; flag for the next docs pass.

### SESSION CLOSE — gaming stack complete; state roll-up + tonight's Palworld 1.0 (2026-07-09 night)

- **Gaming stack is DONE and fully verified.** Final address card: Java `minecraft.tabaska.us` (portless) · Bedrock `bedrock.tabaska.us:1111` · Palworld `palworld.tabaska.us:1105` ("Robits Farm", simple password chosen by user, vault synced) · Switch at home = BedrockConnect via any featured tile. All paths protocol-ping verified except a live Palworld client join (user connected successfully — confirmed working).
- **TONIGHT: Palworld 1.0 releases.** Update playbook: container has `UPDATE_ON_BOOT=true` + `AUTO_UPDATE_ENABLED` cron `0 4 * * *` (30-min player warning) → it self-updates by 4AM, or immediate = `ssh rig 'sudo docker restart palworld'` (steamcmd pulls 1.0 on boot, takes minutes). **Take a manual backup first for a save-format-migrating major patch** (`docker exec palworld backup`); hourly tarballs + nightly restic (saves are in rig BACKUP_PATHS) are the standing net. Friends' Steam clients force-update → server must update promptly or nobody can join. If the agent runs this: backup → restart → watch logs → verify version via REST `:8212/v1/api/info` (basic auth, vault palworld.admin_password) → confirm "Robits Farm" healthy.
- **Monitoring state**: Kuma 50 monitors all-up → ntfy `homelab-alerts` (phone verified); Beszel mini/nas/rig with Status/Disk/Memory alerts; sweep checks incl. kuma/beszel-none-down. Baseline at last full run: 63/63, but see the audit entry below — **2 pre-existing crits were open** (immich-dump-nas + ansible-pull-mini healthchecks, jobs dead since 07-08; do NOT blindly re-enable ansible-pull-mini until the netplan/net-selfheal fixes are folded into the ansible role).
- **Known open items (agent-side)**: AMP Minecraft world offsite backup gap (restic on rig covers Palworld saves but NOT /opt/stacks/amp — HIGH, flagged in audit) · mini static-IP apply (staged, 4-7AM window, UniFi reservation done) · audit report follow-ups (docs/research/12-full-audit-2026-07.md) · sbom-nightly MemoryMax fix awaiting go-ahead · Cloudflare token + AMP panel password rotations (transcript exposure) · ntfy phone-user password in ps output (rotate + netrc).
- **Known open items (user-side, todo-guide)**: Kobo device config (Task 08 card has steps; CWA server half done, token in vault `cwa.kobo_api_endpoint_admin`) · iPod physical sync at the rig (tools installed; runbook `scripts/media/ipod-sync-cachyos.md`; NAS music mount on rig still missing — agent adds on request) · Apollo/Moonlight Deck pairing (Task 03) · TMDb + IGDB keys → vault (Tasks 04/05) · Bitwarden→Vaultwarden migration (Task 06).
- Memory updated: new `game-hosting-stack` memory (playit/AMP/Palworld/BedrockConnect gotchas + split-horizon pattern) so future sessions don't relearn any of it.

### bedrock.tabaska.us + Palworld renamed "Robits Farm" (2026-07-09 eve³)

- **bedrock.tabaska.us LIVE**: +2 NS records in Cloudflare (→ ns1/ns2.playit-dns.com, now 6 total game-domain NS records), LAN rewrites → 69.9.181.17 on both AdGuards (playit IP, NOT the rig — the shared `:1111` only exists on the edge, same reasoning as palworld). Verified: public + both LAN resolvers → 69.9.181.17, RakNet **pong via `bedrock.tabaska.us:1111`**. BedrockConnect's "Remote/playit" entry repointed to the domain (container restarted, repo mirror synced).
- **Palworld renamed** `SERVER_NAME=Robits Farm` (.env edit + container recreate; REST verified `servername: Robits Farm`, healthy).
- **Held the line on COMMUNITY=false**: user tried to find the server in the in-game community browser — that requires registering with Pocketpair's public list, which advertises the **home WAN IP** (server self-detects; knows nothing of playit) and invites randoms. Join method = **direct connect** `palworld.tabaska.us:1105` + server password (vault `palworld.server_password`). If a future session is asked to enable community listing, surface the home-IP leak first.
- User-facing address card now: Java `minecraft.tabaska.us` · Bedrock `bedrock.tabaska.us:1111` · Palworld `palworld.tabaska.us:1105` ("Robits Farm") · Switch = BedrockConnect at home.
- **Palworld password DRIFT found + fixed**: user got "incorrect password" — the deployed `.env` SERVER_PASSWORD, the generated `PalWorldSettings.ini` value, and the vault `palworld.server_password` were THREE different values (md5-compared; the deploy session vaulted one string but shipped another — another docs-vs-reality instance for the audit pattern). User chose a simple game password; set in `.env` + recreate, verified live in PalWorldSettings.ini, vault synced to match. Lesson: after env-driven deploys, verify the *generated* config matches the vault, not just the compose input. (User's choice; it's a video-game password, in-transcript by user's own hand.)

### Game domains LIVE: minecraft/palworld.tabaska.us via playit-dns delegation (2026-07-09 eve²)

- **NS delegation, not A/CNAME**: playit external domains work by delegating the subdomain to their nameservers. Added 4 NS records in Cloudflare via API (`minecraft.tabaska.us` + `palworld.tabaska.us` → ns1/ns2.playit-dns.com, TTL 300). playit-dns now serves both names (A=69.9.181.17; for minecraft also SRV `_minecraft._tcp` → :1105). **Records under those names are managed in the playit dashboard from now on, not Cloudflare.**
- **Verified public**: `minecraft.tabaska.us` resolved exactly like a Java client (SRV → 69.9.181.17:1105) → real status ping → Paper 26.1.2. `palworld.tabaska.us` → 69.9.181.17 (game join still needs a live client test).
- **LAN split-horizon (both AdGuards)**: exact rewrites `minecraft.tabaska.us → 192.168.10.12` (direct, port 25565 matches) and `palworld.tabaska.us → 69.9.181.17` (deliberately NOT the rig: friends' address carries :1105 which only exists on the playit edge; pointing LAN at the rig would break the port). PLUS filter rule `||_minecraft._tcp.minecraft.tabaska.us^` on both resolvers — without it, LAN Java clients would follow the PUBLIC SRV to rig:1105 (dead). Verified: SRV empty + A=rig via both resolvers; rig 25565 open.
- **The user-facing addresses now**: Java `minecraft.tabaska.us` (portless, everywhere) · Palworld `palworld.tabaska.us:1105` (everywhere) · Bedrock `fun-diamonds.nyc.at.playit.plus:1111` (no domain — Bedrock ignores SRV; a bedrock.tabaska.us would still need the port, offered to user as optional).
- **Pattern for future games**: create tunnel in playit dashboard → add `<game>.tabaska.us` external domain there → agent tells me the NS records are already in place if under an existing delegated name, else add 2 more NS records in Cloudflare → add LAN rewrite (rig-direct only if the public port matches the local port; otherwise point at 69.9.181.17).
- Todo-guide TASK 10 → done. Runbook updated (connect section rewritten).

### playit PREMIUM cutover — all 3 tunnels re-verified on the dedicated IP (2026-07-09 eve)

- **User upgraded to playit.plus and RECREATED the tunnels** (old free addresses `analysis-conditioning.gl.joinmc.link:14450` / `stop-spain.gl.at.ply.gg:58804` are DEAD). New, all on dedicated IP **69.9.181.17**, allowance now 16 TCP + 16 UDP, account email now **verified**:
  - **Java** `filter-unthawed.nyc.mcjoin.link` (premium hostname routing, default port 25565 — verified with a real MC status ping: Paper 26.1.2)
  - **Bedrock** `fun-diamonds.nyc.at.playit.plus:1111` (verified RakNet pong)
  - **Palworld** `filter-unthawed.nyc.at.playit.plus:1105` (tunnel loaded + local REST healthy "Tabaska Palworld" v0.7.3; UDP unprobeable — needs one real client join as final proof)
- **Incident during cutover**: agent flapped `tunnel_count` 2↔3 and the Bedrock UDP tunnel timed out from outside even when "loaded". **Fix = restart the playit container after all tunnels show assigned** — the UDP claim only establishes on a fresh control connect. Took 2 restarts (first one raced the flapping). Verify tunnels with real protocol pings, never the dashboard alone.
- **BedrockConnect remote entry updated** (mini `/opt/stacks/bedrock-connect/config/custom_servers.json` → new Bedrock address, container restarted, repo mirror synced). Runbook `configs/gaming/minecraft-crossplay-finish.md` rewritten with the new addresses + the restart gotcha.
- Still open: `mc.tabaska.us` external domain (user has premium now — dashboard Domains → add domain → paste me the requested DNS record and I do Cloudflare + AdGuard LAN split-horizon) · Palworld/Bedrock could move to default ports (19132/8211) on the dedicated IP if the dashboard allows port choice — nice-to-have.

### Audit remediation applied — sweep back to 63/63 (2026-07-09, Fable 5)

Acting on the audit below + user direction ("retire SBOM, fix hygiene, take care of all
recommended fixes, run the window items tonight"). All verified; full table in research/12.
(playit/Palworld public access = the concurrent session's entry above — my M4 finding is
resolved by that work; playit email is now verified there too.)

- **glue-08 FIXED** — ansible-pull failed on `apt-get update` (the `ondrej/php` PPA releaseinfo
  Label change). `apt-get update --allow-releaseinfo-change` cleared it; a real converge ran
  `ok=30 failed=0` and pinged green. **NOTE:** that first successful converge applied daemon.json
  log-caps → **restarted docker once → bounced all mini containers** (~1 min, all 38 verified back
  healthy). Future converges are idempotent.
- **SBOM RETIRED** (user) — `sbom-nightly.timer` disabled+stopped on mini+rig; `sbom` role removed
  from `ansible/site.yml`. sbom-01/02/04 moved to a new `retired` block in progress.json.
- **sbom-03 (etckeeper) FIXED** — the recurring wedge has TWO root causes, now understood: (1) a
  **ref-lock race** between the `etc-watch.path` auto-committer and manual/other commits, and (2)
  the auto-committer using bare `git commit` (not `etckeeper commit`), leaving `.etckeeper`
  perpetually dirty → flapping `git-etckeeper-clean`. Cleared the lock + settled `.etckeeper` by
  briefly stopping `etc-watch.path` for a clean commit. **Durable fix still open:** point etc-watch
  at `etckeeper commit` and/or serialize /etc commits.
- **immich dead-man FIXED** — hardcoded `/bin/curl` in the NAS `immich-db-dump.sh` (DSM cron's
  minimal PATH couldn't find bare `curl`, so the scheduled ping never landed though the dump ran).
  `immich-dump-nas` is now up.
- **fix-19 regression FIXED** — the ansible docker role template omitted `default-address-pools`,
  so every converge stripped fix-19 and bounced docker. Restored pools in the role + on-disk
  daemon.json (take effect on next docker restart; not forced now).
- **Hygiene:** mini `/opt/stacks/*/.env` world-readable 21→0; seedbox `slskd.yml.bak` → 600; rig
  `/boot` retention lowered (MAX_SNAPSHOT_ENTRIES 8→4); verification `run-checks.sh` now warns when
  run as root (the root-run false-failure trap that briefly looked like a "NAS outage").
- **static IP (M2) SCHEDULED for tonight** — guarded auto-reverting apply
  (`/usr/local/sbin/apply-static-ip.sh` + `apply-static-ip.timer`, fires **08:35 UTC = 04:35 EDT**).
  Self-tests IP+gateway+external+DNS; reverts to DHCP + ntfy on any failure. ⚠️ **Still needs the
  UniFi Fixed-IP reservation** for `98:5a:eb:ca:b2:ef`→.2 (success ntfy reminds you).
- **Left to user:** rotate the NAS `health.env` NTFY_TOKEN (it surfaced in audit output).
  **Final sweep: 63/63, 0 crit.**

### Full independent fleet audit — read-only sweep (2026-07-09, Fable 5)

Report: `docs/research/12-full-audit-2026-07.md`. Swept mini/nas/rig/seedbox + the public
game surface, treating every "done/live/verified/backed-up" claim as a hypothesis. **Fleet is
in good shape — no CRIT.** The prior sessions' scary items held up: rig NVMe fix + AER monitor
real and working; AMP Minecraft world **and** Palworld saves confirmed in rig restic→B2 (snapshot
`39763ef8`); NAS HyperBackup→B2 offsite (07-08 20:02) covers Immich photos+DB+docs+homes; both
AdGuards consistent; BedrockConnect hijack live on both; Minecraft Java+Bedrock listening.

- **Reopened 3 tasks (regressed, evidence in progress.json `reopened`):**
  - `glue-08` — ansible-pull on mini fails exit 2 **every night** (timer fires+fails; Healthchecks
    `ansible-pull-mini` down since 07-08). Fleet not self-converging on mini; DHCP fixes still not
    in the role. **Do NOT force a converge** without checking it won't clobber netplan/net-selfheal.
  - `sbom-02` — SBOM→Dependency-Track dead on BOTH hosts (mini OOM Jul 04-08 + upload/DNS fail;
    rig `sbom-nightly.service` failed on a missing env file).
  - `sbom-03` — `etckeeper-commit.service` FAILED on mini (git ref lock mismatch); /etc not being
    auto-committed. 3rd+ recurrence.
- **Two monitoring checks lie in opposite directions:** `immich-dump-nas` is falsely DOWN — the
  DB dump runs fine + is offsite, but the DSM-scheduled run's dead-man ping doesn't land (ping URL
  matches vault; a manual run pinged OK). `ansible-pull-mini` down is REAL. So `alert-healthchecks
  -none-down` (crit) fires for one false + one real reason. **nas-08 kept DONE** (backup healthy;
  only the monitor needs repair).
- **True sweep state = 61/63** as the timer runs it (`User=btabaska`), not the 63/63 the last
  scheduled run logged (etckeeper + healthchecks regressed since 14:15 UTC). ⚠️ The sweep is
  fragile as **root**: `sudo run-checks.sh` yields 9 false failures (root has no known_hosts / ssh
  aliases → "NAS down" artifact). Run it as btabaska.
- **DOC CORRECTION:** the rig OS drive is a **WD Blue SN770** (`WDS200T3X0C-00SJG0`), NOT an SN570.
  Same PCI addr `0000:74:00.0`, so the AER monitor target is correct — only prior notes' model
  string was wrong. Corrected in memory `rig-nvme-pcie-link`.
- **Other opens:** Palworld public access still needs the playit dashboard UDP-8211 tunnel (only
  the 2 MC tunnels exist) + playit account email unverified; rig `/boot` 68% (snapper skipping boot
  entries); 21/31 mini `.env` world-readable w/ secrets; mini static-IP still staged.
- **Hygiene slip this session:** the NAS `health.env` `NTFY_TOKEN` (homelab-alerts topic) surfaced
  in the audit shell output — **rotate it** and re-vault.
- No fixes applied to live services (read-only posture) beyond doc/tracker corrections. `ssh seedbox`
  alias is broken — reach betty via `ssh -o HostKeyAlias=seedbox.tailb31641.ts.net btabaska@100.119.134.94`.

### Palworld gameplay tuning + AMP world now has offsite backup (2026-07-09 late⁴)

- **Palworld settings (per user)**: `DIFFICULTY=Hard`, `PAL_DAMAGE_RATE_DEFENSE=0.8` (pals take 0.8× damage — tankier), `ENEMY_DROP_ITEM_RATE=2.0` (2× dropped items); everything else left at image/vanilla defaults (ExpRate/capture/attack all 1.0). Set as **non-secret env in compose.yaml** (not .env), mirrored to repo. Verified in the compiled ini after full restart: `Difficulty=Hard, PalDamageRateDefense=0.8, EnemyDropItemRate=2.0`. **Gotcha**: `compile-settings.sh` rewrites the ini from env on every start, but Palworld also rewrites the ini on clean shutdown — so during a `compose up` recreate there's a brief window where the ini shows the OLD values (old container's shutdown write) before the new container recompiles. Read the ini only after the server is fully up (RCON answers), or you'll misread a race.
- **AMP Minecraft world now has an offsite backup (fixes the gap flagged below)**: added `/opt/stacks/amp/config/.ampdata/instances/MinecraftCross01` to rig `BACKUP_PATHS`, **excluding** `…/Backups` (rotating hourly zips, up to 28×~458MB≈12GB, poorly dedupable — restic is the offsite mechanism now) and `…/AMP_Linux_x86_64` (re-downloadable binary). Verified in snapshot `39763ef8`: the world (`Minecraft/world/level.dat`, dimensions…) is present, 0 backup-zip entries. Repo `scripts/backup/restic-backup.env.example` updated to document the rig set. So AMP's world is now covered both locally (AMP hourly zips) and offsite (nightly restic→B2). ⚠️ still NOT covering: AMP "Main" panel instance config, and all of the rest of /opt — intentionally (only game-world state is backed up under /opt).

### Palworld dedicated server LIVE on the rig (2026-07-09 late³)

- **Deployed `palworld` on the rig** (`/opt/stacks/palworld`, `ghcr.io/thijsvanloef/palworld-server-docker:latest` — the glibc container, NOT AMP: AMP's Alpine/musl can't run the steamcmd/Palworld glibc binaries). Compose + `.env` (secrets only) on host; repo mirror at `configs/gaming/palworld/` (compose + `.env.example`, real `.env` gitignored). RAM was a non-issue — rig has 62G total / 53G free. Server up: **v0.7.3.90464, "Tabaska Palworld", 0/16 players**; container **healthy**, `restart=unless-stopped`.
- **Secrets generated + vaulted**: `palworld.server_password` (20ch) / `palworld.admin_password` (28ch). Never printed. `COMMUNITY=false` (not on the public browser), `PLAYERS=16`, hourly image backup cron, nightly steamcmd auto-update at 04:00 ET, `AUTO_REBOOT=false`.
- **Ports**: `8211/udp` game (published 0.0.0.0 → this is what playit forwards) · `8212/tcp` REST API (LAN, admin basic-auth — used for monitoring) · `127.0.0.1:25575/tcp` RCON (localhost admin/backup tooling). **Dropped the Steam query port (27015)** — Palworld has **no A2S responder at all** (verified: A2S on 8211 and 27015 both silent from LAN and host loopback). The game port only answers a real client handshake, so a raw UDP probe never responds — don't chase it.
- **gamedig gotcha**: gamedig's `palworld` type queries the **REST API on 8212 with basic auth** (`admin` + admin password), NOT A2S/the game port. That's why an 8211 gamedig query fails. Verified working from the mini's Kuma container → `{name:"Tabaska Palworld",players:0,max:16,ping:1}`.
- **Image healthcheck was BROKEN in `:latest`** — its declared `CMD healthcheck.sh` isn't present in the image (exit -1 "not found"), would flip the container to unhealthy after the 900s start period. **Overridden** in compose with a REST curl: `curl -fsS -u admin:$$ADMIN_PASSWORD http://127.0.0.1:8212/v1/api/info` (the `$$` keeps compose from substituting the secret at parse time; container shell expands it at runtime — no secret in the file). Now reports healthy.
- **BACKUPS — corrected a false handoff claim**: the rig restic `BACKUP_PATHS` was **`/etc /home/btabaska` only — `/opt` was NOT backed up** (the AMP entry's "/opt is in BACKUP_PATHS" was WRONG). Added the Palworld save dirs (`/opt/stacks/palworld/game/Pal/Saved` + `/game/backups`) to `/etc/restic/env` (backup at `env.bak-prepalworld`), kept steamcmd binaries excluded (re-downloadable). Ran a snapshot — **`ac8b7a7f` includes both paths, integrity check clean**. Plus the image's own hourly local backup cron (manual `backup` verified → tarball written). ⚠️ **The AMP Minecraft world at `/opt/stacks/amp` is STILL not in restic** — same false-claim gap, out of scope here; flag for the user (its only offsite copy does not exist; only AMP's local hourly backups protect it).
- **Uptime Kuma monitor added**: "Rig Palworld" (id 50) = HTTP+basic-auth against `http://192.168.10.12:8212/v1/api/info` (gamedig-in-Kuma can't send the REST auth, so plain HTTP monitor instead). Green (200), ntfy-linked (49 links). Seed script `scripts/uptime-kuma/seed-monitors.sh` extended with `add_http_basic` + optional `PALWORLD_ADMIN_PW` env (vault `palworld.admin_password`).
- **PUBLIC ACCESS = human step (playit dashboard)**: agent API key is read-only (verified — 2 existing tunnels: MC Java/Bedrock, both shared-IP; no dedicated IP on the account yet). User must add the Palworld tunnel: **playit.gg dashboard → Add Tunnel → Palworld (UDP 8211) → local `127.0.0.1:8211`** on the existing rig agent (allows 4 UDP, 2 used). Then verify: `POST https://api.playit.gg/tunnels/list` w/ `Authorization: agent-key <vault playit_gg.secret_key>`, or gamedig the public host once known.
- **Sweep**: 60/63 at first run — all 3 regressions were **pre-existing, NOT Palworld**: a snap-nvim auto-refresh (4813→4820) left a stale failed mount unit + uncommitted /etc (both cleared: `reset-failed` + etckeeper commit after removing the recurring stale `/etc/.git/index.lock` — 3rd time now). Remaining **crit is pre-existing**: Healthchecks `immich-dump-nas` + `ansible-pull-mini` both last-pinged 2026-07-08 (scheduled jobs stopped — NOT self-clearing from grace as a prior session expected). Do NOT blindly trigger `ansible-pull-mini` — the netplan/net-selfheal DHCP fixes aren't folded into the ansible role yet.


### BedrockConnect LIVE — consoles join MinecraftCross with zero device config (2026-07-09 late²)

- **Deployed `bedrock-connect` on the mini** (`/opt/stacks/bedrock-connect`, strausmann/minecraft-bedrock-connect, UDP **19132** — free on mini since Geyser's 19132 is on the rig; NODB=true, custom server list at `config/custom_servers.json` pre-seeded with `MinecraftCross (Home)` = 192.168.10.12:19132 and a playit fallback entry). Verified: RakNet pong "Join To Open Server List"; custom-server data confirmed loaded in logs.
- **DNS hijack instead of console DNS settings**: 10 featured-server domains (hivebedrock.network, geo.hivebedrock.network, mco.mineplex.com, org.mineplex.com, mco.lbsg.net, play.inpvp.net, mco.cubecraft.net, play.galaxite.net, play.pixelparadise.gg, play.enchanted.gg) rewritten → 192.168.10.2 on **both** AdGuards (mini: YAML edit + container restart — no API creds for mini AdGuard in vault; NAS: `/control/rewrite/add` API). Verified both resolvers answer 192.168.10.2 for the hijacked names. **Consequence: real featured servers are unreachable from the LAN** while rewrites are on (acceptable per user; scope per-device later if anyone misses The Hive).
- Console flow (works for ANY Bedrock console on home WiFi, not just Switch): Minecraft → Play → Servers → open any featured tile → BedrockConnect list → MinecraftCross (Home). Off-LAN the hijack doesn't apply (featured servers resolve normally).
- Repo: /opt/stacks committed+pushed on mini (compose only — config/ is gitignored there); full mirror incl. custom_servers.json at `configs/docker-stack/stacks/bedrock-connect/`. todo-guide TASK 09 → done.
- Note for next agent: mini AdGuard rewrites now include these 10 + `*.tabaska.us`; if AdGuard config is ever regenerated, re-add (NAS list is API-managed, mini's is in the YAML).

### playit.gg public access LIVE + AMP sleep-mode gotcha (2026-07-09 late)

- **Decision: friends connect via playit.gg tunnels** (not raw static-IP port-forward, not Tailscale — consoles can't run TS). Agent container on rig `/opt/stacks/playit` (ghcr.io/playit-cloud/playit-agent, host network, SECRET_KEY in on-host .env + vault `playit_gg.secret_key`; repo mirror configs/gaming/playit/). One agent, many tunnels — account allows **4 TCP + 4 UDP**; Palworld etc. = just more dashboard tunnels later.
- **Both tunnels VERIFIED end-to-end from off-host** (real MC status ping + RakNet pong through the public edge): Java `analysis-conditioning.gl.joinmc.link:14450` (SRV → port optional in client) · Bedrock `stop-spain.gl.at.ply.gg:58804`. Agent API key is READ-ONLY (`NotAllowedWithReadOnly` on tunnels/create) — tunnel creation is dashboard-only.
- **Gotcha found while verifying — AMP sleep mode**: `Limits.SleepMode=True` (default, 5-min empty timeout) stopped the app mid-verification; AMP's wake listener answers **Java protocol only** on 25565 (MOTD "Powered by AMP") — so (a) a Java status ping is NOT proof the real server is up, and (b) **Bedrock/Geyser is completely dark while asleep** and Bedrock joins can never wake it. Set `Limits.SleepMode=False` (rig is 24/7). If sleep is ever wanted again, know that it silently breaks the Bedrock side.
- **User's playit account email still unverified** (agent logs `account_status=email_not_verified`) — remind to verify or playit may cap/expire things.
- **User DECIDED: no whitelist** — mitigation = backups instead: AMP's built-in hourly-backup trigger ENABLED (retention MaxBackupCount=28), sticky baseline backup "baseline-pre-launch" taken (465MB), and the world is inside the rig's nightly restic→B2 (`/opt` is in BACKUP_PATHS). Griefing recovery = AMP UI → Backups → restore. Flip whitelist later only if a stranger shows up.
- Still open: BedrockConnect for Switch (todo Task 09) · mc.tabaska.us (Task 10).

### AMP white-screen fixed + Minecraft crossplay server LIVE, fully automated (2026-07-09 night)

- **White screen root cause**: after the rig's reboots, the AMP container came up but the ADS panel instance ("Main") had **no start-on-boot flag** → nothing on :8080 → Caddy 502 → blank browser. Fixed durably: `ampinstmgr --SetStartBoot` set for BOTH Main and MinecraftCross01; verified by a full container recreate (panel came back unattended).
- **The "first instance must be born in the UI" claim is DEAD**: `docker exec -u abc amp ampinstmgr …` bypasses the BusyBox `su` failure (that failure was root-exec-only), and `--CreateInstance` takes the licence key as an argument. Created `MinecraftCross01` (friendly "MinecraftCross") entirely from the CLI. Gotchas: ampinstmgr refuses create/rebind/setboot while ADS runs (stop Main briefly); the CLI's [Port] arg is the instance's WEB port, not the game port (rebound web→8081, game stays 25565).
- **Licence is machine-id-bound** — container recreate invalidated it (NoMatchingMachineId) until reactivated; compose now **pins hostname c5f46f35aee3** so future recreates keep activations. Reactivate cmd in the runbook.
- **Java saga (all persisted)**: Alpine image has no java → openjdk21 via `INSTALL_PACKAGES` env (survives recreates). Minecraft 26.x demands **Java 25** → Temurin 25 musl JRE at `/config/java/jdk-25.0.3+9-jre` behind wrapper `/config/java/java25-paperfix.sh` (strips `--log-strip-color`, which AMP module 2.8 passes but Paper 26.x removed). Instance `Java.JavaVersion` → wrapper.
- **Version matrix that actually works**: Paper **26.1.2** + Geyser 2.10.1-b1183 + Floodgate 2.2.5. Geyser latest does NOT support MC 26.2 (ExceptionInInitializerError in shaded incendo/cloud on enable) — AMP's manifest "26.2-rc-2" and real Paper 26.2 both fail the same way. Real Paper versions: `fill.papermc.io/v3` (v2 API is sunset). Plugins installed as jars from the GeyserMC download API into `Minecraft/plugins/`. eula.txt seeded.
- **VERIFIED from the mini**: Java TCP 25565 reachable; **Bedrock RakNet unconnected-ping → real pong** ("Powered by AMP", 0/20, protocol 26.32). Compose now maps 25565 + 19132/udp (they were never published before — LAN players couldn't have connected). Kuma monitor **"Rig Minecraft Java"** added (48 total, all up, ntfy-linked).
- **API path for instance management** (documented in runbook): panel `/API/Core/Login` → proxied instance login at `/API/ADSModule/Servers/{id}/API/Core/Login` → proxied SetConfig/UpdateApplication/Start/GetUpdates. Instance auth is ADS-delegated; rig `.mc-admin-password` is unused.
- **Repo**: configs/gaming/amp/compose.yaml mirror updated (hostname pin, java envs, port maps; secrets stay ${AMP_*}); minecraft-crossplay-finish.md rewritten as live-state runbook; todo-guide TASK 02 marked done; progress.json game-02 → done (140/223 — concurrent sessions closed more tasks today; len(done)==meta count verified).
- **Hygiene note**: the rig's live /opt/stacks/amp/compose.yaml has the panel PASSWORD and LICENCE as literals (pre-existing); they surfaced in a session transcript today — rotate the panel password when convenient.
- **Still open (user decisions)**: BedrockConnect self-host for Switch 2 (todo Task 09) · mc.tabaska.us (Task 10) · whitelist before sharing the address. AMP image/module update would obsolete the java wrapper — retest after module >2.8.

### Kuma + Beszel pass COMPLETE — fleet-wide monitoring live (2026-07-09 evening)

- **Uptime Kuma: 11 → 47 monitors, ALL UP** (todo-guide TASK 07 closed). Seeded via direct MariaDB inserts + container restart (v2 loads at startup) — script: `foss-setup/scripts/uptime-kuma/seed-monitors.sh` (idempotent by name; run with `NTFY_TOKEN` from vault `ntfy.kuma_token`). Coverage: every catalog service on mini/NAS/rig/HA/seedbox by direct host:port (status codes probed live first — seerr-family 3xx, mcpo 404-on-/, apollo https+ignore_tls), 3 full-chain vhost checks (home/vault/books.tabaska.us → DNS+Caddy+LE-cert expiry alerts), DNS checks, 5 host pings. **Gotchas encoded in the script**: container→host-IP UDP hairpin TIMES OUT on mini, so "DNS AdGuard mini" + "DNS Unbound mini" are TCP checks by container name (`adguardhome:53`, `unbound:5335` on the shared edge network); NAS AdGuard is a real dns-type query. Notification = ntfy type via `http://ntfy:80` (edge network, no Caddy/DNS dependency), topic `homelab-alerts` (phone subscribed), `is_default=1` + linked to all 47 via monitor_notification. **Maintainerr was NOT seeded — it's removed from the fleet but still in service-catalog.yaml (stale entry, cleanup pending).**
- **Beszel: mini + NAS + rig all registered and UP with alerts.** Root cause of the stale "only MacBook shows" state: the sole system record ("MacBook", 192.168.10.253) had the fingerprint token that the MINI's agent connects with — i.e. it was mini data mislabeled (no agent runs on the MacBook; port closed). Renamed that record to `mini`/192.168.10.2 (agent connection preserved). Created `nas` + `rig` systems + fingerprint records via PocketBase superuser API (auth `/api/collections/_superusers/auth-with-password` with vault beszel.admin_*), tokens in vault `beszel.agent_token_nas/_rig`. Agents deployed in **WebSocket mode** (dial hub, no inbound port): rig `/opt/stacks/beszel-agent/`, NAS `/volume1/docker/beszel-agent/` (Synology doesn't auto-create bind dirs — mkdir first; scp subsystem broken to NAS, use `ssh nas 'cat > file'`). Repo: `configs/host/{rig,nas}/beszel-agent/` (+.env.example; real .env with token never committed). Alerts: Status(5m)/Disk(85%)/Memory(90%) × 3 systems, webhook = shoutrrr `ntfy://:<token>@ntfy:80/homelab-alerts?scheme=http` in user_settings; **test-verified end-to-end via `POST /api/beszel/test-notification` → 200 → phone**.
- **ntfy: two new admin tokens** (labels uptime-kuma, beszel) → vault `ntfy.kuma_token` / `ntfy.beszel_token` (follows fleet convention of labeled admin tokens).
- **Sweep: 63/63 pass, 0 crit** (2 new checks: `alert-kuma-none-down`, `alert-beszel-none-down`; the latter needs BESZEL_ADMIN_USER/PASSWORD in mini `/etc/verification/env` — added + etckeeper-committed). Cleared en route: stale `/etc/.git/index.lock` on mini (recurring issue — second time now) which had also failed `etckeeper-commit.service` (reset).
- Note: Kuma monitors live in its MariaDB (data, not compose) — re-seed from the script on rebuild. Beszel "MacBook" is gone as a name; if the user wants the MacBook genuinely monitored, install an agent there and add a 4th system.

### rig NVMe fix APPLIED (out of window, user-authorized) + AER→ntfy monitor live (2026-07-09)

- **NOTE for the concurrent session**: the NVMe kernel-param fix is **DONE** — do NOT re-apply it in the 4-7AM window (the earlier RCA entry's "await window" is superseded).
- **Applied to rig `/etc/default/limine` `KERNEL_CMDLINE[default]`** (backup at `/etc/default/limine.bak-preaspm`): added `nvme_core.default_ps_max_latency_us=0` (disable NVMe APST) + `pcie_aspm=off`. Ran `limine-update`, verified generated `/boot/limine.conf` default entries carry the params + `root=UUID` intact, **rebooted rig** (came back clean in ~40s).
- **VERIFIED**: `/proc/cmdline` has both params; APST latency now `0`; **PCIe AER errors = 0** over 2 min uptime (was **8-16 in the first 2 min** pre-fix). So the RxErr storm is stopped. (`pcie_aspm=off` still shows "ASPM L1 Enabled" in lspci LnkCtl, so APST was the dominant trigger; errors stopped regardless.)
- **Drive mapping is by PCI addr, not nvmeX** (the number reshuffles on reboot): `0000:74:00.0` = WD Blue SN570 = OS drive (root btrfs `/`,`/home`,`/var/*` + `/boot`). Currently enumerates as `nvme2`. Use SMART/PCI, never the `nvmeN` name.
- **AER→ntfy monitor deployed on rig** (self-contained, because tailnet ACL blocks mini→rig SSH so the mini runner can't read rig's journal): `/opt/pcie-aer-monitor/pcie-aer-monitor.sh` + systemd timer (every 20 min, root). Counts AER on `74:00.0` this boot; POSTs to ntfy `verification` topic (same iOS push you already get) only if correctable climbs ≥25/interval, any fatal/uncorrectable, or SMART critical!=0x00. Silent when healthy. Token: vault `ntfy.rig_aer_token` (label `rig-aer`). Repo: `foss-setup/configs/host/rig/pcie-aer-monitor/`. One `[TEST]` ntfy sent + delivered (200); no more test pings.
- **Still open (physical/durable, user's call)**: reseat the SN570 M.2 / try a CPU-direct slot; consider dropping `nowatchdog` for auto-recovery; if AER ever returns, migrate OS to the Corsair MP600 PRO or replace the SN570. The software fix treats the trigger, not the marginal link itself.

### Kobo sync live + rig back + regressions cleared (2026-07-09 afternoon)

- **Rig is BACK as of 08:59 EDT** — it came up within a minute of a `wakeonlan 50:eb:f6:b5:82:c6` fired from mini at ~08:58 (vault MAC, same as wake-rig.sh — verified identical, so the earlier failed WoL was state-dependent, not a wrong MAC; a user power-cycle at that moment is the alternative explanation). All services healthy post-boot: ollama/litellm/open-webui all 200, Apollo user-unit active, restic ran. NVMe RCA below explains the crash; fixes still await the 4-7AM window.
- **Sweep regressions cleared: 54/61 (2 crit) at session start → 59/61 on re-run → remaining 2 self-clear**: stale restic snapshots on mini (its 01:41 UTC run died in the DHCP outage) and rig (was off) — both kicked manually, both completed + pinged Healthchecks ("All done" / "Finished"). Healthchecks now 0 down (ansible-pull mini/rig + immich-dump-nas in *grace*, self-clear on next scheduled run). Mini DHCP mitigations re-verified this boot: net-selfheal.timer active, KeepConfiguration drop-in present, netplan still bare-DHCP — **static IP still staged, not applied** (window tomorrow 4-7AM ET, lease expiry ~11:55 UTC).
- **CWA Kobo sync ENABLED end-to-end (server half of todo-guide TASK 08)**: `config_kobo_sync=1` + `config_kobo_proxy=1` (store passthrough) in app.db, container restarted, `https://books.tabaska.us/kobo/<token>/v1/initialization` verified **200** with the real token (401 with a bogus one = auth active). Sync token minted for the admin user (remote_auth_token, token_type=1, no expiry) → vault `cwa.kobo_sync_token_admin` + full URL at `cwa.kobo_api_endpoint_admin`. todo-guide TASK 08 rewritten to the device-side steps (edit `Kobo eReader.conf` `[OneStoreServices] api_endpoint`). Add a second CWA user + token if the user wants per-Kobo progress separation.
- **iPod toolchain preinstalled on rig (read-10 done)**: rhythmbox 3.4.9 + libgpod 0.8.3 (repo script) + gpodder 3.11.5 (read-12 install half). Human half remaining: plug in the iPod and follow `scripts/media/ipod-sync-cachyos.md` (FirewireGuid/SysInfoExtended gotchas documented there). Note: rig has **no NAS music mount** — mount `/volume1/music` (SMB) or sync from a local copy before read-11.
- **Hygiene**: the ntfy read-only `phone` user's password is visible in `ps` output on mini (curl `-u` on the wake-rig-listener cmdline). Low risk, but rotate when convenient and switch the listener to `--config`/netrc so it stays out of the process list.

### RCA: rig freeze (2026-07-08 20:02 EDT) = NVMe PCIe link instability on the OS drive (2026-07-09)

- **Event**: rig froze **2026-07-08 20:02:39 EDT**, stayed dead ~13h until user hard-rebooted 07-09 08:59. Boot -1 log ends abruptly mid-operation — **no shutdown sequence, no kernel panic, no pstore dump**. Boot -2 ended cleanly (deliberate reboot 08:46), so the freeze is a single event, but the underlying fault is chronic.
- **PRIMARY CAUSE (strongly supported)**: NVMe **nvme1 = WD Blue SN570 2TB** at PCI **0000:74:00.0** throws continuous **PCIe correctable AER errors** (`RxErr`, Physical Layer, Receiver ID): **764 (boot -2), 724 (boot -1), 8-16 within 2 min of the new boot** — ~2/min at idle, happening right now. ALL AER is on this one device (362 "PCIe Bus Error" headers in boot -1, 0 on other slots).
- **It's a LINK/signal problem, not a dying drive**: SMART clean — Critical Warning 0x00, **0 Media/Data Integrity Errors, 0 error-log entries**, 1% used, 34°C, 5647 POH. Link trains full Gen3 x4. So NAND/controller are fine; the PCIe **physical layer** is marginal.
- **Why it froze the whole box**: per `/etc/fstab`, the root btrfs `UUID=e4b84b06` (subvols `/`, `/home`, `/root`, `/srv`, `/var/cache`, `/var/tmp`, `/var/log`) **AND `/boot`** all live on this same SN570. A transient link wedge blocks ALL OS I/O → journald can't write (hence abrupt stop, no panic) → hard hang. Kernel cmdline has **`nowatchdog`** so nothing auto-recovers → frozen till manual power-cycle. **Unsafe Shutdowns = 523** (high) ⇒ this freeze/hard-reboot cycle has likely recurred.
- **Aggravator = power management**: **PCIe ASPM L1 Enabled** on the link + **NVMe APST enabled** (`nvme_core.default_ps_max_latency_us=100000`). Power-state transitions on a marginal link are the classic trigger for RxErr storms + occasional drops.
- **Ruled out**: thermal (28°C, no throttle/critical-temp), OOM (none), MCE/hardware-error (none), GPU (no Xid/NVRM errors — NVIDIA 610.43.02 clean).
- **FIXES — #1 APPLIED & VERIFIED 2026-07-09 (user waived window); see the newest top entry. #2-4 still open.** (bootloader = limine)**:**
  1. Kernel params via `/etc/default/limine` `KERNEL_CMDLINE[default]`: add **`nvme_core.default_ps_max_latency_us=0`** (kill NVMe APST) + **`pcie_aspm=off`** (or gentler `pcie_aspm.policy=performance`). Regenerate limine + reboot. Most common cure for RxErr AER storms + associated hangs.
  2. Physical (user): power down, **reseat the SN570 M.2** (clean contacts); try a CPU-direct M.2 slot if free.
  3. Resilience: consider dropping `nowatchdog` / enabling a watchdog so a future hang auto-reboots (this box is meant to be 24/7 — 13h dead is the cost of no watchdog).
  4. If AER persists after 1+2: slot/controller marginal → migrate OS to the healthier Corsair MP600 PRO (nvme0) or replace the SN570. It hosts the whole OS, so this is the durable fix.
- **Monitoring gap**: nothing alerted on the AER storm. TODO: add a verification check = count `PCIe Bus Error` in `dmesg`/journal, warn if > threshold.

### Follow-ups after queue fix — RIG DOWN, Radarr/Lidarr fixed, Hacks E01 desync (2026-07-09)

- **RIG IS FULLY OFFLINE (needs physical power-on)**: no LAN ping (192.168.10.12), SSH "host down", Tailscale "offline, last seen ~12h ago". Supposed to be 24/7 (suspend masked) so this is a crash or power event, not a sleep. **WoL recovery FAILED** — fired `wake-rig.sh` from mini (MAC 50:eb:f6:b5:82:c6), no response after 90s (WoL from full S5/crash isn't waking it). Impact: AI stack (ollama/litellm/open-webui), Apollo, AMP panel all down. **Action needed: user power-cycles rig physically**, then recheck. (User said they separately fixed the *mini* reboot in another window — mini not investigated here.)
- **Radarr + Lidarr got the same Post-Import Category fix** (they had the identical empty-category gap): Radarr `movieImportedCategory=radarr-imported` (v3), Lidarr `musicImportedCategory=lidarr-imported` (v1); Deluge labels created; removeCompletedDownloads stays False. All three *arr now auto-declog while seeding.
- **Hacks S01E01 — STILL UNRESOLVED (Sonarr DB quirk)**: deleted the ghost `-scene` file (user OK'd) and re-imported the pack's `-glhf` E01 via ManualImport (Copy). The file physically lands correctly (`Season 01/...S01E01...-scene.mkv`, 1.87GB, valid), episode is monitored, no conflicting episodefile record — **but `hasFile` stays False** after ManualImport ×2 + RescanSeries ×3. Content IS on disk and Plex-playable; only Sonarr's tracking is stuck (46/47 S01... i.e. still shows E01 missing). Next lever = **Sonarr container restart** to clear its internal cache (not done — mild downtime, user's call). Risk if left: Sonarr may keep trying to re-grab a "missing" E01 → lands on existing file → could re-stick the queue.

### Sonarr queue declogged 57→0 + seed-preserving architecture (2026-07-09)

- **Symptom**: Sonarr queue stuck at 57 items "for a while." Diagnosis: only **9 distinct torrents** behind 57 rows (one 48-episode season pack = 48 rows). All Deluge/torrent on the seedbox.
- **ROOT CAUSE**: Sonarr's Deluge download client had **no Post-Import Category** (`tvImportedCategory` empty) and `removeCompletedDownloads=False`. So every imported torrent stayed in the `sonarr` label, kept getting re-scanned, got pinned with an "already imported" *warning*, and never left the queue. (Deluge carried **266** `sonarr`-labeled torrents; only the warning-pinned ones showed in the queue.)
- **FIX (live, reversible — user wanted seeding preserved for ratio, NOT deletion)**:
  1. Created Deluge label `sonarr-imported` (RPC via `~/venvs/deluge/bin/python`, Label plugin).
  2. Set Sonarr Deluge **`tvImportedCategory = sonarr-imported`** → future imports auto-relabel out of the tracked `sonarr` label the moment they import → they leave the queue while Deluge keeps seeding. `removeCompletedDownloads` left **False** so nothing is auto-deleted.
  3. Relabeled the existing done torrents `sonarr`→`sonarr-imported` (Phineas&Ferb pack, South Park, both HotD, hacks, INSECURE). All 6 verified **still Seeding**.
- **Stragglers handled**: 3 dead `Sex.Life S02` downloads (0%, ratio -1, 3 days) → removed + blocklisted + re-searched. `INSECURE THE END` = an S00 special the user doesn't collect (0/42) → relabeled/kept seeding.
- **DISCOVERED pre-existing desync (NOT fixed — needs user OK, unrelated to queue)**: **Hacks S01E01** shows missing in Sonarr (9/10 S01) but a valid 1.87GB MKV (`...S01E01 - There Is No Line...-scene.mkv`, correct EBML magic) sits on disk at the library path — **Plex can play it now**. Sonarr's disk scan silently refuses to enumerate/register that specific file (RescanSeries completes, hasFile stays False; ManualImport hits "Destination already exists" because the ghost is there; folder scan lists E02–E10 but not E01). Likely fix = delete the ghost `-scene` file and re-import the pack's `-glhf` E01 (still seeding, importable) — held pending user OK since it's a deletion.
- **Reaper (user chose age-only 14d, remove+data)**: `deluge-reaper.py` on betty (`~/scripts/`), cron `0 5 * * *` CEST, `--live`. Removes `sonarr`/`sonarr-imported` torrents (+seedbox data only; NAS library is a separate copy) once age ≥14d. Dry-run now = **0 eligible** (oldest torrent 6.7d — seedbox populated ~1 wk ago); first reaps ~next week. Repo: `foss-setup/configs/host/seedbox/` (script + README).
- **Latent same-gap**: Radarr/Lidarr Deluge clients also have no Post-Import Category — apply the same fix if they clog.
- **Side observations (not acted on)**: rig SSH timed out at session start (supposed to be 24/7 — recheck); all mini containers showed "Up ~4 min" (mini rebooted recently, consistent with the DHCP-lease RCA below).

### RCA: recurring mini "freeze" = 24h DHCP lease expiry (2026-07-09)

- **Symptom**: every ~1-2 days mini stops answering everything (no ARP/ping/SSH/DNS); it's still powered ("frozen"); hard reboot fixes it. Took out `home.tabaska.us` (Homepage → mini) and, worse, mini's own AdGuard DNS.
- **NOT a freeze**: journald is persistent and logged continuously right up to each manual reboot — CPU/OS were alive the whole time. **Ruled out**: kernel panic/lockup (none in pstore or `-k`), thermal (`intel_powerclamp` fired *after* the outage; pkg ~75°C is high but not the trigger), OOM (`sbom-nightly`/`syft` OOM'd Jul-08 04:14 and the box survived — separate issue, see below).
- **ROOT CAUSE**: `enp3s0f0` is bare-DHCP netplan (`/etc/netplan/00-installer-config.yaml`: `dhcp4: true`, no static/`critical`). UniFi hands a **24h lease** (`LIFETIME=86400`, T1 12h, T2 21h). The **in-lease RENEW/REBIND path fails silently** (UniFi not honoring renewals for the existing lease; a *fresh DISCOVER* on reboot always succeeds — that's why reboot fixes it). At the 24h hard expiry, systemd-networkd **withdraws the IP and flushes every route** (`RTM_DELROUTE` burst) → box alive but off-network until power-cycle.
- **Proof / exact-24h pattern**: boot -1 acquired `Jul07 20:21:12` → routes flushed `Jul08 20:21:13` (24h to the second). boot -3 acquired `Jul02 19:40:21` → "network unreachable" storm began `Jul03 19:40:21` (again 24h). Log rate jumps ~1.3k→~13k lines/hr at the death moment (retry spam) and stays pinned until reboot. No `tg3`/carrier-down logged (link stayed up; only L3 config was pulled).
- **FIXES DEPLOYED (both reversible, verified)**:
  1. **`net-selfheal.timer`** (every 60s) → `/usr/local/sbin/net-selfheal.sh`: if default route/gateway `192.168.10.1` unreachable, escalates `networkctl renew` → link bounce → `systemctl restart systemd-networkd`, logging every step (journal tag `net-selfheal`). Guaranteed recovery in ≤60s + full capture next time. No-op verified when healthy. Repo copies: `foss-setup/configs/host/mini/net-selfheal/`.
  2. **`KeepConfiguration=dhcp`** drop-in at `/etc/systemd/network/10-netplan-enp3s0f0.network.d/10-keepconfiguration.conf` → networkd keeps the address instead of flushing it when a lease can't be renewed. Load + parse **confirmed** via invalid-value test.
- **STATIC IP — user chose to apply in the 4-7AM ET window (STAGED, not yet applied)**: proposed netplan + apply runbook committed at `foss-setup/configs/host/mini/static-ip/` (`00-installer-config.static.yaml` + `README-apply.md`). Sets `192.168.10.2/24` static, gw .1, nameservers [.2,.4,.1]. Prereq: user adds UniFi **Fixed IP** reservation for `98:5a:eb:ca:b2:ef`→.2. Apply via `netplan try` (auto-reverts). Do it before the next expiry (~Jul-10 11:55 UTC — the window lands just before). Removes the lease dependency entirely; watchdog + KeepConfiguration stay as backstop. Secondary open q: why UniFi ignores in-lease RENEW/REBIND for this client (static makes it moot).
- **Secondary (separate) issue — user chose "investigate first" (NO change made yet)**: `sbom-nightly.service`/`syft` OOMs **every night** — 7 kills total, one per run (Jul-04 04:51, 05 04:55, 06 05:24, 07 05:12, 08 04:14…), each grabbing ~6-6.5GB RSS. On this 2014 dual-core/**8GB** Mac mini (+4GB swap) running ~40 containers (~3.5GB resident at idle, Committed_AS ~16GB = 2× overcommit), syft's nightly ~6GB balloon blows past RAM+swap → global OOM. The OOM killer has (so far) correctly picked syft, but it's fragile — during the event the box thrashes into swap and networkd route ops can time out (saw `Could not set route: Connection timed out` 3 min before the Jul-08 OOM), so this may *aggravate* DHCP renewal too. **Proposed fix (awaiting go-ahead): `MemoryMax=`/`MemoryHigh=` on `sbom-nightly.service`** so syft is contained to its own cgroup and can't drag the whole box down; alternatively reduce syft scope/parallelism. Timer: `sbom-nightly.timer`, ~03:40 UTC nightly, ExecStart `/opt/scripts/inventory/sbom-nightly.sh`.
- **Ansible note**: the two fixes live only on-disk + in repo `configs/host/mini/net-selfheal/`; fold into the ansible mini role so a reprovision keeps them.

### Tracker repair + state sync (2026-07-08 night)

- **The Plan v3 guide (docs/index.html) had been rendering BLANK (0/223 tasks)** — the retro-01..07 stubs (added earlier without `host`/`type`/`estimate`, and with `detail` as an HTML string instead of the sectioned array) crashed `esc()`/`renderDetail()` before the first paint. Fixed: `esc` is now null-safe (one malformed task can no longer blank the whole tracker) and the retro tasks were filled to schema (async, hosts, verify lines, markdown-lite sectioned detail). **If you add tasks to taskData: title/host/type/estimate are required, and `detail` must be an array of `{h, body, sub, cmds}` sections — validate by loading the page.**
- **State synced to reality**: game-11 marked done (verified live on rig: `display-policy.service` active, dummy plug HDMI-A-1, Apollo dd_* per-client resolution config present). game-02 rescoped Pelican→AMP (deployed at amp.tabaska.us, licensed; remaining = human creates first Minecraft instance via web UI, then agent finishes crossplay). Stale "Pelican on the Mac mini" prose fixed. progress.json meta corrected to **124/223 (56%)**; run bars: R0 87 · R1 80 · R2 88 · R3 36 · R4 65 · R5 6 · R6 17 · R7 0.
- **Sweep at session start: 61/61 pass, 0 crit, 1 skipped** (61st = new sys-docker-subnet-squat guard). No regressions.
- Tracker has no served vhost — view via `file://` + Import progress, or any HTTP serve of docs/ (auto-merges progress.json). `.claude/launch.json` config `foss-docs` serves it on :8899 for sessions.

### Apollo resolutions + AMP Minecraft (2026-07-08 evening)

- **Apollo per-client resolution**: dd_configuration_option=ensure_active, dd_resolution_option=automatic, dd_refresh_rate_option=automatic, dd_config_revert_on_disconnect=enabled (rig ~/.config/sunshine/sunshine.conf). Follows each Moonlight client's requested res/fps, reverts after. User sets Deck=1280x800@90, TV=4K@30 client-side. Caveat: 1280x800@90 not in dummy EDID → may negotiate to 60 until the 4K120 dummy arrives.
- **Dummy plug**: HDMI-A-1, supports up to 3840x2160@30 (+4096x2160@24). Single-display policy service live (see below).
- **AMP Minecraft**: could NOT create the instance autonomously — this minimal AMP container breaks two ways: (1) API CreateInstance needs the deployment-defaults licence key which is only settable via the AMP UI (node not in settings spec); (2) ampinstmgr CLI CreateInstance hits BusyBox `su -f` incompatibility ("su: unrecognized option: f"). Both mean the FIRST instance must be born via the AMP web UI. Prepared everything else: firewall 25565/tcp + 19132/udp open (LAN+tailnet), instance admin pw at rig:/opt/stacks/amp/.mc-admin-password, runbook `configs/gaming/minecraft-crossplay-finish.md`. USER STEPS: set deployment licence in UI → create Minecraft Java instance (Paper) → install Geyser+Floodgate from plugin browser → then I verify + configure crossplay + Switch 2 (BedrockConnect DNS for the console). AMP panel healthy, no partial instance left.

### Run 5 kickoff — smart home context + plan (2026-07-08, day session)

- **Full house/device context captured** → `docs/research/11-ha-home-context.md` (71 Culver Rd profile, canonical rooms↔HA-areas table, 18-device integration map, IoT firewall policy, ~$550 Zigbee shopping list, 12 pitched opportunities, fut-01..06 future projects). Read it before touching Run 5.
- **Live HA audit** (192.168.10.50, core 2026.6.4): Hue (73 lights/21 scenes) + 2× Elgato + Matter/Thread + companion app already integrated — tracker was behind reality. ha-01/ha-02 closed with verification. 16 lights `unavailable` = wall-switch power cuts.
- **HA registry work (AI, reversible, verified)**: 4 floors created; areas renamed to canonical rooms (6 renames); Laundry/Gym/Storage areas added; all areas floor-assigned; misassigned bathtub light Kitchen→Bathroom. 4 room-name ambiguities await human answer (see context doc §open questions).
- **Long-lived HA token minted** (client "homelab-agent", 10 y) → vault `hosts.ha.api_token`; also on mini in `/etc/verification/env` as `HA_TOKEN`. Hue bridge located at **192.168.20.100 (already on IoT VLAN 20, 0 B WAN)** → vault `hue.bridge_ip`. Hue app shows stale 192.168.1.115 (pre-VLAN cache; harmless).
- **Tracker (Plan v3 → 222 tasks)**: ha-06 RESCOPED — new-in-box **ecobee Premium replaces Nest 3rd gen**, integrated locally via homekit_controller; Google SDM cloud path dropped. New tasks ha-18..ha-32 (rooms, IoT migration ledger, Level locks stay Apple-native, Roborock, Roomba, LG TVs, ThinQ, Apple TV/HomePods, VeSync, Emporia, Withings, non-integratables, sensor wave 1, automations pack, ops glue) + fut-01..06 (irrigation, plug-in solar, weather station, Meshtastic, sump, grow tent) in run 7. ha-01 stale IP fixed (.13→.50).
- **Verification**: new `checks.d/ha.yaml` (3 checks, HA_TOKEN-authed) deployed; sweep **60/60 pass, 0 crit** after committing /opt/stacks drift (AMP vhost + homepage tile — another session's work, committed+pushed+mirrored to repo).
- **Findings**: (1) Trusted→IoT is REJECTED for mini while HA (10.50) gets through — narrower than plan §1 assumes; reconcile in UniFi (ha-19). (2) Concurrent session did the TLS/Apollo work above mid-session — watch for races when two agents run at once.
- **⚠ Cloudflare token hygiene**: the token value has now appeared in TWO chat transcripts (user paste + this session's masking slip during a vault inspection). Rotation recommended: Cloudflare dash → API Tokens → Roll, update vault + Caddy env on mini, restart caddy, verify a cert renewal.

### TLS cutover + Apollo (2026-07-08 late)

- **REAL TLS LIVE**: NS delegated to Cloudflare (courtney/ryan.ns.cloudflare.com), zone active, email verified safe (MX/SPF/verification intact + Cloudflare added Proton DKIM ×3 + DMARC the old zone lacked). Flipped Caddy `local_tls` snippet from `tls internal` → Cloudflare DNS-01; **42 vhosts obtained Lets Encrypt certs** (valid→Oct 6, auto-renew). Unblocks ntfy iOS push, Kobo sync, Bitwarden repoint. Token in vault cloudflare.api_token (came via chat — user may rotate).
- **Sunshine → Apollo**: sunshine pkg removed; apollo 0.4.8 (AUR, NVENC) installed, creds vault apollo.*, KMS capture, autostart enabled, all ports listening, web UI auths, caddy apollo.tabaska.us (sunshine alias kept) w/ real cert. Docs migrated (19 files). **Display note**: rig is NOT headless — it's the user's daily workstation with a real monitor, just off when they're away. Apollo captures fine when monitor is on. For monitor-off remote streaming → HDMI/DP dummy plug (~$8, recommended) or leave monitor on. Finish test: `~/apollo-enable.sh` on rig + Moonlight pairing (needs monitor on / dummy plug).
- **AMP purchased** — license in vault cubecoders_amp.license_key. INSTALL METHOD PENDING USER DECISION: rig is their daily-driver workstation + Arch (AMP bare-metal officially supports Debian/Ubuntu/CentOS only). Options: Docker (least invasive, fits fleet) / Debian VM-LXC (official support, isolated) / bare-metal (intrusive on daily driver, unofficial distro). Recommend Docker. Not installed yet — don't install a big service on their personal machine without the method call.
- Sweep: 57/57 green.

### Interactive session (2026-07-08 daytime — rig→24/7 + big batch)

- **DECISION: rig runs 24/7** (~130W idle accepted for availability). Repo-wide contradiction sweep applied across 63 files (plans, tracker, wiki, verification, ansible, gaming docs). sleep.target/suspend.target MASKED on rig (it kept entering s2idle despite logind — KDE/PowerDevil); WoL kept only as recovery. Rig verification checks re-enabled → sweep now **57/57 green**.
- **Rig maintenance done**: pacman -Syu (441 pending → 0; corrupt proton-cachyos-native pkg + stale keyring fixed), kernel 7.1.3, reboot, containers recreated (log caps now apply), GPU 300W verified + resume hook, dead CIFS mounts (pointed at old //192.168.1.3 shares that no longer exist) cleaned.
- **Plex updated** 1.41.5 → 1.43.3 (DSM package).
- **Dependency-Track unblocked end-to-end**: admin pw reset via DB (v5 uses sha512+bcrypt-14; vault dtrack.admin_*), granted Automation team PROJECT_CREATION_UPLOAD, SBOM uploads now 200. Three root-cause bugs fixed (OOM excludes, bogus multipart Content-Type→415, PUT→POST).
- **AdGuard**: HaGeZi Multi Normal + OISD Big added to both instances (verified).
- **Mini Immich fully removed** (real compose was at ~/server/compose/immich-app, not /opt/stacks — that's why it kept resurrecting; data preserved). Maintainerr removed (no auto-deletion wanted). tdarr removed from plan (re-encode conflicts with TRaSH).
- **YouTube pipeline now actually works**: root-caused the 403s — stale/blind yt-dlp failing YouTube's JS n-signature challenge. Fix = nightly yt-dlp + bgutil PO-token provider container baked into custom metube & pinchflat images. MeTube verified end-to-end (download → /volume1/music/YouTube). beets deployed (youtube-ingest config: tag strong matches in place, quarantine weak by skip; daily DSM task id=10). bgutil-pot container on edge net.
- **litellm secrets rotated** (was CHANGE-ME pg pw + salt==webui secret): unique pg pw (role ALTERd live), salt, webui secret — all vaulted (litellm.*, open_webui.*). Sunshine web creds set + streaming ports opened (vault sunshine.*); switched to KMS capture; **awaiting your Moonlight PIN pairing**. Rig UFW scoped to LAN+tailnet (dropped Anywhere rules for 11434/3000, stale 3030); tailnet AI access re-verified.
- **wake-rig recovery**: ntfy topic `wake-rig` + host listener service on mini + homepage tile (publish → WoL). Verified.
- **Vaultwarden signups closed** (you registered). Vault additions: dtrack.*, litellm.*, open_webui.*, sunshine.*, uptime_kuma.*, beszel.* (you added the last two).
- **Handed back (creds ready, method fiddly — NOT done)**: Uptime Kuma monitors (socket.io API needs uptime-kuma-api client) and Beszel agent registration (mini agent is socket-mode; API-created rows show down; needs UI Add-System or agent→TCP + NAS/rig agent deploy).
- **Docs delivered**: docs/cloudflare-cutover.html (+ .md) and docs/game-hosting-design.html (incl. panel comparison: AMP vs Pterodactyl/Pelican/Crafty — AMP is the only one with in-game player-state tracking).

### Deep-audit second pass (2026-07-08, later the same night)

- **5 read-only agents audited the ~20 services the first sweep missed** → `docs/research/10-deep-audit.md` + report §3b. Report converted to light theme + proper HTML skeleton (was white-on-white in some viewers).
- **Fixed (all verified)**: musicseerr Lidarr key (was 401-dead) · paperless default admin password rotated (vault: paperless.*) · wallabag data-dir perms (65534) · navidrome nightly DB backup on + telemetry off · mealie+vaultwarden sqlite added to pre-backup dumps · vaultwarden ADMIN_TOKEN → argon2 PHC (login verified; compose .env needs single-quoted single-$) · mini sbom stale script → SCAN_EXCLUDES deployed (run passed old OOM point; one HTTP 415 on metube:latest image upload — watch) · seedbox 6 secret files chmod 600 · NAS rclone watchdog (flock, empty-ls=stall, find timeout, deduped container restart) fixed in repo + deployed · recyclarr restart=no + cron log off /tmp · 9 new verification checks (alerting.yaml; sweep now 52; scoped sudoers /etc/sudoers.d/verification-diun on NAS).
- **Top new decisions** (see report §3b): Stash NO AUTH · rig partial-upgrade (441 pending) · Sunshine firewall/pairing · litellm CHANGE-ME password + shared salt key · rig UFW Anywhere rules · Plex update + transcoder core dump · tdarr never-deployed / maintainerr inert · AdGuard-NAS .3 interface dead.

### Overnight remediation run (2026-07-08, post-audit)

- **Verification sweep**: 41/43 pass, 0 crit (2 fails = intentional git drift, cleared by this session's commits); rig checks 5/5.
- **restic mystery solved**: mini timer deployed 01:29 UTC, first backup succeeded 01:30:50 UTC (B2); rig backup ran 21:32 EDT; next fires Jul 9 01:30 UTC / 01:33 EDT. Dead-man pings now wired (see below).
- **Fixed on mini**: etckeeper stale index.lock (0 failed units now); healthchecks+mealie healthchecks (images dropped curl → python3 urllib); unbound root.key gitignored; zombie Immich stopped + restart=no (125 restarts; teardown still needs approval); generated inventory manifests folded into repo.
- **ntfy**: NTFY_BASE_URL=https://ntfy.tabaska.us, NTFY_UPSTREAM_BASE_URL=https://ntfy.sh (iOS push ready); read-only `phone` user created (vault: ntfy.phone_password, admin_password also vaulted). Verified publish/read/403.
- **Diun**: mini instance now publishes via http://ntfy:80 on edge network (was https vhost Go would reject; test notif verified); second Diun deployed on NAS watching 21 containers (test verified; vault: ntfy.diun_nas_token).
- **Healthchecks LIVE**: superuser bootstrapped (creds = HC_SUPERUSER_* in mini:/opt/stacks/healthchecks/.env), HC_SITE_ROOT=https://health.tabaska.us, ntfy integration + 6 dead-man checks (restic mini/rig, immich-dump-nas, ansible-pull mini/rig, verification); pings wired via systemd drop-ins on mini+rig and NAS dump script; all seeded green. Ping URLs in vault (healthchecks.*).
- **NAS DSM scheduler**: root-cause of "every 15 min" tasks only running 00:00-00:45 = `last work hour=0` in .task files; fixed tasks 4+5 + crond restart (crontab regenerated, verified). **DSM had wiped the immich-dump crontab line** — replaced with proper DSM task id=9 (02:30 daily) + new /volume1/scripts/nas/immich-db-dump.sh (pg_dumpall, size guard, 14-day retention, healthchecks ping; test run OK 16.7MB). health.env created (ntfy token). Installer script bug fixed on NAS + repo.
- **YouTube pipeline**: Plex "YouTube" library created (section 4, /volume1/youtube, Personal Media agent, scan verified); MeTube → /mnt/nas-youtube/metube + AUDIO_DOWNLOAD_DIR → /volume1/music/YouTube (end-to-end test download verified, then removed); Pinchflat → NAS confirmed + "YouTube (Plex)" media profile seeded (visible in UI). Human still adds sources/channels.
- **Security**: HSTS + access logs on all vhosts (local_tls snippet); vaultwarden /admin gated to LAN+tailnet at Caddy; fstab plaintext passwords scrubbed (all CIFS mounts → /etc/samba/cred-nas; new rw music mount /mnt/nas-music-rw). Vaultwarden signups left OPEN — 0 users, human must register first. Forgejo offsite backup confirmed already working (restic B2: repos as files + nightly pg_dump).
- **Reopened**: media-02 (Kometa) — was marked done but config was untouched template; plex url/token fixed from vault, runs still blocked on human TMDb key.
- **Blocked on creds** (not in vault, nowhere on disk): Uptime Kuma admin (0 notification channels, 34/45 services unmonitored) and Beszel hub admin (only MacBook monitored) — need creds dropped in vault or approval to reset.

### Run 0 results (2026-07-07 evening)

- **ansible-pull converges GREEN on mini** (first success ever): ok=34 failed=0, apply mode. Fixes: SOPS gates on backup+sbom roles, un-ignored break-glass pubkey, removed conflicting docker apt source on mini, chezmoi via installer on Debian.
- Repo topology fixed: forgejo `home/homelab` = foss-setup/ subtree, published via `scripts/docs/publish-deploy.sh` (fast-forwards).
- mini: /opt/stacks drift committed+pushed; etckeeper repaired; 3 dead CIFS mounts disabled (systemctl --failed = 0); maintainerr healthy; duplicate mini Immich stopped (Caddy->NAS verified).
- Secrets: leaked ntfy diun token REVOKED + rotated (vault: ntfy.diun_token); wallabag admin rotated (vault: wallabag.*). NAS AdGuard password rotation still blocked on container being up.
- migration-snapshot archived to nas:/volume1/backups/migration-snapshot-2026-07-07 (92,128/92,128 files verified).
- gpu-power-tune awk/read bug fixed in repo (deployed copy on rig pending sudo).
- Rig BLOCKED on two gates: btabaska sudo needs password (vault sudo slots empty; NOPASSWD or password needed) and rig forgejo deploy key unregistered (rig pubkey staged; register in Forgejo web or provide forgejo admin creds). Units staged at rig:~/staging/.
- HA discovered live at 192.168.10.50:8123 (creds in vault); not on tailnet yet.

### Runs 1-2 autonomous results (2026-07-07 night)

- **Verification framework LIVE** (verify-01..05): 41 checks across 7 domains; daily timer 07:15 on mini; ntfy topic `verification` (dedicated token); LLM triage on rig via ollama qwen3-coder:30b — first cycle: 35 pass, 6 fail (all expected: dns-02 x2, nas-08 dump, 3 git-drift), 6/6 valid triage verdicts; reopen-suggestions.json feeds session starts.
- **home.tabaska.us rebuilt** (home-01..04): 40-service catalog (service-catalog.yaml), 39 verified Caddy vhosts incl. ha + wiki + NAS/rig services; categorized Homepage with live widgets (vault keys, values only on mini).
- **wiki.tabaska.us LIVE** (wiki-01..04): 51 pages — hosts, 7 runbooks, operations, network + 32 generated service pages (gen-wiki-services.py); build via build-wiki.sh (pinned mkdocs-material 9.5).
- Notes: mini->rig SSH denied by tailnet ACL (rig checks are HTTP); mini->nas SSH key added; Sunshine down on rig (502 expected at the time — superseded 2026-07-08: rig is 24/7 now, a 502 is an incident); all *.tabaska.us certs are Caddy-internal CA by design (Cloudflare token would enable real certs).

### Gates cleared wave (2026-07-07 late)

- **dns-02 CLOSED (verified)**: NAS AdGuard up; missing *.tabaska.us rewrite added + enabled; admin password rotated (vault: adguard_nas). Verification cycle: ALL crit checks green fleet-wide (exit 0).
- **nas-08 CLOSED**: immich pg_dump in root crontab (02:30) + run once, fresh 16.7MB dump verified. Caveat: DSM Task Scheduler edits may rewrite /etc/crontab; freshness check is backstop.
- **game-10 CLOSED**: fixed gpu-power-tune deployed, GPU capped 300W.
- **fix-13 CLOSED**: rig ansible-pull green (ok=21 changed=9 failed=0), timer enabled; sbom-nightly timer live; NOPASSWD sudoers on rig; rig deploy key (read-only) in Forgejo.
- mini->rig SSH via LAN enabled (sshd + key). Sunshine 502 fixed (ufw allow 47990 from LAN); Moonlight stream ports 47984-48010 still closed (open when game streaming starts).
- Discovery: Dependency-Track runs on the NAS (healthy) — docs said mini; corrected. Overseerr on NAS Exited(1) 2mo ago (retire candidate, fix-18/D-list).
- Human leftovers: delete two Forgejo API tokens (Settings -> Applications: rig-setup-1783471946, token-cleanup-1783471996); tag seedbox tag:server in Tailscale; optional Cloudflare NS move for real TLS.

## Session 4 — 2026-07-07 (Plan v3)

- **Full repo + fleet audit** performed (every host inspected against the guide and configs).
- **Guide refactored into 8 staged runs** (Plan v3 in `docs/index.html`) — **194 tasks** total.
- **Regressions found and reopened:** `dns-02`, `game-10`, `nas-08` — previously marked done but no longer true on the fleet.
- **Run 0 execution started** (docs/repo reorganization, hygiene, tracker groundwork).
- Docs reorganized: validation report archived, wiki/home-hub designs moved under `docs/`, NAS schema and game-server guide moved next to their configs, root `README.md` added.

# Rollout handoff state — 2026-07-05 (session 3)

Import this into the tracker (`docs/index.html`) so checkmarks match reality for the next agent.

## Quick import (browser)

1. Open `foss-setup/docs/index.html` in your browser (file:// or served).
2. Click **Import progress** and choose `docs/progress-backup-2026-07-05.json`.

**Or** paste in DevTools console:

```javascript
fetch('../docs/progress-backup-2026-07-05.json')
  .then(r => r.json())
  .then(obj => {
    const done = obj.done || obj;
    const key = 'foss-analogue-progress-v1';
    const merged = { ...(JSON.parse(localStorage.getItem(key) || '{}')), ...done };
    localStorage.setItem(key, JSON.stringify(merged));
    location.reload();
  });
```

## Progress snapshot

| Metric | Value |
|--------|-------|
| Completed | **79 / 162** (49%) |
| Previous backup | `progress-backup-2026-07-03.json` (67 done) |
| This session | +12 tasks |

## Completed this session (2026-07-05)

| Wave | Tasks |
|------|-------|
| **DNS resilience** | dns-02 NAS secondary AdGuard (API configured, `*.tabaska.us → 192.168.10.2`) |
| **Life apps** | read-07 Wallabag, doc-01 Paperless-ngx (mini), read-14 Pinchflat |
| **Reading** | nas-09 CWA verified running, ebook-04 Libreseerr |
| **Ops** | docker-12 Diun (ntfy topic `diun`) |
| **Plex polish** | media-01 Tautulli, media-02 Kometa, media-03 Maintainerr |
| **Gaming** | game-08 WoL on rig, game-05 Sunshine installed + active |

## Ansible / glue-08 fixes pushed to Forgejo (`home/homelab`)

- `configs/ansible/files/id_ed25519.pub` (break-glass key)
- `admin_user: btabaska` in group_vars
- base role: missing pkglist manifest + check_mode fixes
- tailscale role: skip `tailscale up` when already connected

**Still partial:** ansible-pull timer runs but playbook may still fail on later roles; rig ansible-pull not deployed.

## Partial / deferred (do NOT mark done without verifying)

| Task | State |
|------|-------|
| **dns-02** | Deployed — **change NAS AdGuard admin password** (temp: set via API install; login at http://192.168.10.4:3000) |
| **dns-03** | UniFi DHCP fail-open chain — **you** (UniFi GUI) |
| **dns-04** | Outage drill — run `scripts/network/dns-resilience-verify.sh` after dns-03 |
| **dns-05** | NAT :53 + DoH blocking — **you** (UniFi GUI); only after dns-04 |
| **glue-01** | No UPS — nut-client on mini ready |
| **glue-08** | mini timer active; playbook still exits non-zero on some roles |
| **sbom-02** | mini + NAS scheduled; rig not done |
| **nas-08** | Immich healthy; pg_dump backup exists (2026-07-02); **schedule cron in DSM**; admin/Quick Sync pending |
| **read-07** | Change default Wallabag password; create API client for KOReader |
| **doc-01** | Paperless on **mini** (not NAS); complete first-visit admin wizard |
| **media-02** | Kometa needs `config/config.yml` Plex + TMDb keys |
| **read-14** | Pinchflat downloads to local `./downloads` — point at NAS YouTube library |
| **ebook-04** | Libreseerr needs Readarr API wiring in UI |
| **game-05** | Sunshine web UI pairing at https://192.168.10.12:47990 |
| **game-10** | gpu-power-tune script fixed in repo; verify service on rig |
| **B2 / sec-03 / handoff-05** | User skip until B2 ready |

## Key URLs

| Service | URL |
|---------|-----|
| Miniflux | https://rss.tabaska.us |
| Navidrome | https://music.tabaska.us |
| Mealie | https://recipes.tabaska.us |
| Wallabag | https://wallabag.tabaska.us |
| Paperless | https://paperless.tabaska.us |
| Pinchflat | https://pinchflat.tabaska.us |
| Homepage | https://home.tabaska.us |
| AdGuard (mini) | https://dns.tabaska.us |
| AdGuard (NAS) | http://192.168.10.4:3000 |
| Uptime Kuma | https://uptime.tabaska.us |
| DepTrack | https://deptrack.tabaska.us |
| Immich | https://immich.tabaska.us (LAN :2283) |
| CWA | http://192.168.10.4:8083 |
| Forgejo | http://macmini.tailb31641.ts.net:3030 |
| Libreseerr | http://192.168.10.2:8789 |

DNS: **Still gateway-only DHCP** until dns-03. Target chain: `#1` mini `192.168.10.2`, `#2` NAS `192.168.10.4`, `#3` gateway `192.168.10.1`.

## Suggested next_up

1. **dns-03** UniFi fail-open DHCP chain (~15 min in UniFi UI)
2. **dns-04** Run outage drill script
3. **read-03 / ebook-02** CWA ingest + Readarr hook
4. **ha-01** Home Assistant onboarding
5. **nas-08b** SD card import (after Immich admin)

## Secrets / hygiene

- NAS AdGuard temp admin password set during API install — **rotate immediately**
- ntfy Diun token: (rotated — see vault: `ntfy.diun_token` in `.handoff-secrets.yaml`; never store literal tokens in this doc)
- Wallabag/Paperless secrets generated on mini `.env` files — not in vault yet
- Seedbox SSH blocked by Tailscale ACL — add SSH policy for operator MacBook → betty
