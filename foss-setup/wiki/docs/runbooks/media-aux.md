# Media-aux services — configured but silently dead

What to do when a `media-aux` check fires (ntfy topic `verification`).

These checks close quality-gate findings **M14 / M15 / M16 / M18** (task
**fix-37**, 2026-07-18). The shared failure shape: a service that looks green —
container Up, daily run "completed", provider `/ping` 200 — while its actual
function is dead. A backup env that silently no-ops, a PO-token provider no
client ever calls, playlist builders 401ing inside a run that exits 0, a
library UI serving zero content. Every check probes the **consumer end**.

Source checks: `verification/checks.d/media-aux.yaml`. Daily via the
verify-cycle sweep (domain `media-aux`); failures notify ntfy `verification`,
and the sweep itself is dead-man-monitored on healthchecks.

---

## `navidrome-backup-fresh` failed (crit) — no recent backup file

Output `fresh_backups=0`. No `navidrome_backup_*.db` under
`/opt/stacks/navidrome/backup/` newer than 26h and >1MB. The nightly 02:00
backup didn't land — schedule broken, path unwritable, or container down.

1. `ssh mini 'docker logs navidrome 2>&1 | grep -i backup | tail'` — you want
   `Scheduling periodic backup`; if you see `Periodic backup is DISABLED`,
   `ND_BACKUP_PATH` regressed (see next check).
2. Check the dir exists and is writable by 1000:1000:
   `ls -la /opt/stacks/navidrome/backup`.
3. Force one now and confirm a >1MB file appears:
   `ssh mini 'docker exec navidrome /app/navidrome backup create'`.
4. Off-site copy rides restic's `/opt/stacks` path automatically.

## `navidrome-backup-armed` failed (warn) — backup silently disarmed

Output `disabled_msgs=1+`. The container logged `Periodic backup is DISABLED`
at startup. Root cause of the original M15: Navidrome accepts
`ND_BACKUP_SCHEDULE`/`ND_BACKUP_COUNT` **without** `ND_BACKUP_PATH` and
disarms itself with one INFO line. The compose must keep `ND_BACKUP_PATH:
/backup` + the `./backup:/backup` mount (`stacks/navidrome/compose.yaml`,
fix-37 comment block). Restore whichever went missing, `docker compose up -d`,
confirm the log shows `Scheduling periodic backup`.

## `kometa-run-clean` failed (warn) — last run buried errors

Output `kometa_run_errors=N`. Kometa's exit code is worthless (a run full of
401s still "Finished OK"), so this parses the last run in
`/opt/stacks/kometa/config/logs/meta.log`.

1. See what broke:
   `ssh mini "awk '/Starting .* Run/{n=NR} {l[NR]=\$0} END{for(i=n;i<=NR;i++) if(l[i] ~ /Error|CRITICAL/) print l[i]}' /opt/stacks/kometa/config/logs/meta.log"`.
2. Common causes and fixes:
   - `MDBList Error: 401` → `mdblist.apikey` missing/rotated in
     `config/config.yml` (vault `mdblist.api_key`).
   - `sub-attribute … is blank` → someone re-added an empty integration block;
     delete it (fix-37 removed all of them — empty blocks are latent errors).
   - `Plex Library 'X' not found` / `File does not exist` → a `libraries:`
     block names a nonexistent Plex library or collection file; fix or delete.
3. Re-run one-shot and re-check:
   `ssh mini 'docker exec -e KOMETA_RUN=True kometa python3 kometa.py'`.
   The `-e KOMETA_RUN=True` is **mandatory** — Kometa gives env vars precedence
   over CLI flags and the compose env pins `KOMETA_RUN=False`, so the
   often-documented `docker compose run --rm kometa --run` silently ignores
   `--run` and sits waiting for the 05:00 schedule with zero output.
4. Mirror any config-structure change to
   `configs/docker-stack/stacks/kometa/config/config.yml.example`.

## `pinchflat-pot-provider` failed (warn) — POT pipeline broken

No `bgutil:http-<ver> (external)` line (or it shows `, unavailable`) when
pinchflat's own yt-dlp runs. One of: the plugin zip fell out of a rebuilt
image, `/etc/yt-dlp.conf` lost the `youtubepot-bgutilhttp:base_url` line, or
the `bgutil-pot` server is down/unreachable on the `edge` network.

1. Server first: `ssh mini 'docker logs --tail 5 bgutil-pot'` and
   `docker exec pinchflat wget -qO- http://bgutil-pot:4416/ping`.
2. Plugin/conf: `docker exec pinchflat sh -c 'ls /etc/yt-dlp/plugins/; cat /etc/yt-dlp.conf'` —
   both the zip and the base_url line are baked by `stacks/pinchflat/Dockerfile`;
   if missing, someone rebuilt from a stale Dockerfile — redeploy from the repo
   and `docker compose build --pull && docker compose up -d`.
3. Version skew: the plugin zip is pinned to the bgutil-pot server version
   (1.3.1 ↔ 1.3.1). If the server image moved (it tracks `:latest`), bump the
   pinned plugin URL in the Dockerfile to match and rebuild. Bump **together**.

## `pinchflat-stuck-media` failed (warn) — a NEW video is bot-check-stranded

Output `new_botcheck_stuck=N`. A media item beyond the 7 accepted ids
(409/702/895/915/939/1008/1333, the 2026-07-14 casualties) hit `Sign in to
confirm you're not a bot` and never downloaded. The 7 are accepted because a
valid PO token was fetched and attached on 2026-07-18 and YouTube still
returned LOGIN_REQUIRED — that state is cookie-gated, and feeding account
cookies to a headless downloader is a deliberate non-goal (account-flag risk).

A new stranded item means the countermeasure pipeline regressed or YouTube
escalated:

1. Confirm the POT pipeline is green (`pinchflat-pot-provider` above).
2. Probe the video manually inside the container with
   `docker exec pinchflat yt-dlp -v --simulate --extractor-args "youtube:pot_trace=true" <url>`
   — if a POT is attached and it still LOGIN_REQUIREDs, the video joined the
   cookie-gated class: either accept it (add its id to the check's exclusion
   list in `media-aux.yaml`, live + repo) or decide to provide cookies.
3. If NO POT is fetched, work the provider chain (plugin/conf/server/versions).

## `romm-content-ingest` failed (warn) — library/DB out of sync

RomM is **accepted-empty** (M18): 0 files on the share, 0 DB rows, owner adds
ROMs manually. Empty+empty passes. The failures:

- `ROMM_CONTENT_NOT_INGESTED files=N roms=0` — files landed under
  `/mnt/share/Games/romm/` but the DB never ingested them. Scans are
  UI-triggered, not scheduled: log into https://romm.tabaska.us and run
  Library → Scan. If the scan finds nothing, files are probably not in the
  `roms/<platform-slug>/` layout RomM expects (docs.romm.app folder structure).
- `ROMM_LIBRARY_VANISHED files=0 roms=N` — DB claims ROMs the share doesn't
  have (the Immich-class bug): CIFS mount dropped mid-scan or share content
  was deleted. Fix the mount, re-scan, only then consider purging DB rows.
- `GAMES_MOUNT_DOWN` — `/mnt/share/Games` isn't mounted on the mini; the check
  fails loudly instead of passing vacuously. Remount, then re-run.
