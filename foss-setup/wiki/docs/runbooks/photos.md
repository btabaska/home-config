# Runbook — photos (Immich empty-library / backup freshness)

**Task:** `fix-35` · **Findings:** H17, H28, M58, I109 · **Host:** nas (Immich)

## The failure class

Immich ran green for two weeks with **zero assets**. Every probe watched the *process* —
API ping, version endpoint, container health, the nightly pg_dump dead-man — and all of
them stayed green around a library that had never received a single photo. The service's
entire purpose (phone photo backup) was not happening, and nothing could tell.

Root cause (H28): **the mobile app was never paired.** Server-side setup stopped at web
onboarding — the only session ever created was a Safari/macOS web login. No iOS/Android
session was ever registered, `asset` count was 0, both users' `quotaUsageInBytes` were 0,
and 14 nightly DB dumps differed by <300 bytes (a static database).

This is the flagship instance of the audit's monitoring-vs-reality class: see
[Monitoring coverage (liveness vs reality)](monitoring-coverage.md).

## Current state (2026-07-18, fix-35)

- **Server upgraded v2.7.5 → v3.0.3** while the library was empty (cheapest possible time
  for a major hop; the v3 breaking changes are API-surface only, and the VectorChord
  Postgres digest is unchanged from the v2.7.5 release compose). Pin lives in
  `/volume1/docker/immich/.env`, mirrored at `foss-setup/configs/nas/immich/`.
- **Pairing is deliberately pending** — operator decision 2026-07-18: infrastructure
  ready now, phones pair later. The two content checks below **alert until that happens;
  the alert is the reminder.** Do not "fix" the alert by disabling the checks.
- **Both accounts are full admins on purpose** (brandon.tabaska@protonmail.com,
  kaelyn92@icloud.com) — M58 reviewed and accepted 2026-07-18. Both still carry
  `shouldChangePassword=true`; Immich forces a password change at each account's next
  login, which is the intended path.
- **Monitoring API key**: `verification-monitor`, scoped to `server.statistics` **+
  `asset.read`** (the latter added 2026-07-24/glue-14 so the `immich-smart-search-consumer`
  check can POST `/api/search/smart`), owned by the brandon account. Secret at vault
  `immich.verify_api_key`, deployed as `IMMICH_API_KEY` (+ `IMMICH_URL`) in
  `/etc/verification/env` on mini. Rotate by deleting the `api_key` row named
  `verification-monitor` and re-inserting `sha256(new_secret)` (the `key` column is the
  raw 32-byte digest, bytea).
- **ML window key**: `rig-ml-window (glue-14)`, scoped to `job.create` + `job.read` only
  (NOT admin), owned by the brandon account. Secret at vault
  `immich.rig_ml_window_api_key`, deployed as `IMMICH_API_KEY` in
  `/etc/immich-ml-window.env` on the **rig** — used only to pause/resume the ML job
  queues around the night window (below).

## Pairing a phone (the missing step)

1. Install the **Immich** app (iOS App Store / Google Play).
2. Server URL: `https://immich.tabaska.us` (works on LAN and away; LAN-only fallback
   `http://192.168.10.4:2283`).
3. Log in with the account's email. Both accounts are flagged to force a password change
   at first login — pick the permanent password there.
4. Enable **backup**: select albums (at minimum Camera Roll/Recents), turn on background
   backup, and let the first sync finish while on home Wi-Fi + power.
5. Confirm end-to-end: the two verification checks flip green on the next daily sweep,
   or run ad-hoc from mini:
   `/opt/verification/bin/run-checks.sh --host mini` (look for the two `nas-immich-*` ids).

## The checks (verification/checks.d/nas-services.yaml)

| id | probes | green means |
|----|--------|-------------|
| `nas-immich-backup-freshness` | admin statistics API (photos+videos) **and** newest original file on disk under `/volume1/photo` | at least one asset exists AND a file landed within 7 days — backup is actually flowing |
| `nas-immich-mobile-paired` | *(retired nas-31)* `session` table via psql — ≥1 iOS/Android session | *(disabled)* was a proxy for "a consumer is connected"; superseded by backup-freshness |

`nas-immich-backup-freshness` is `severity: warn`, daily sweep tier, ntfy topic
`verification`. It is both the **regression** guard (exact H17 bug: empty/stale library
behind green liveness) **and** the **class** guard (server green but no consumer ever
connected): it asserts the real OUTCOME — fresh assets landing within 7 days — regardless
of which client uploaded them.

### nas-31 (2026-07-28): why `nas-immich-mobile-paired` was retired

The 2026-07-20 audit flagged both fix-35 checks failing. Reality on 2026-07-28:

- **backup-freshness RECOVERED and is genuinely healthy** — `backup=fresh`, DB dump
  `immich-2026-07-28.sql.gz`, organic daily uploads continuing (162 assets created
  2026-07-27, newest original on disk `IMG_2114.jpg` @ 2026-07-27 22:53). Photos are
  really being backed up.
- **mobile-paired was accurate but is the wrong proxy.** The `session` table has *never*
  held an iOS/Android row — only Safari/Firefox on macOS/Linux. Yet fresh phone photos
  keep landing, because this fleet backs up via the **web uploader**, not the native app.
  The check tests an implementation detail (a native-app login session) that is not the
  actual goal, and it can only be made green by a **physical device** pairing the app — no
  server-side action clears it. Left it as a permanent false alarm.

**Resolution:** retired (set `enabled: false`, kept for provenance) because its intent —
catch "server green but nothing is actually being backed up" — is fully and more strongly
covered by `nas-immich-backup-freshness`, which measures the outcome rather than a
session-row proxy. Re-pairing the native Immich app (see "Pairing a phone" above) remains a
user choice / **needs-human** action, not an automated monitor.

## fix-60 (2026-08-02 fleet sweep): four Immich data-hygiene fixes

The sweep found four independent Immich issues (findings SM1, SM36, SL5, SL22, SL29). All
resolved 2026-08-03; five new checks in `verification/checks.d/nas-services.yaml`:

| id | severity | probes | green means |
|----|----------|--------|-------------|
| `immich-user-zero-assets` | warn | `/api/server/statistics` `usageByUser` | **every** user has >0 assets — per-user backup is flowing |
| `nas-immich-corrupt-mov-quarantined` | warn | `asset_file` preview row for asset `8a5d0a66…` | the crash-looping .mov is still quarantined from transcode |
| `nas-immich-ffmpeg-nocrash` | warn | `@ffmpeg*core.gz` at `/volume1` root | no Immich ffmpeg transcode crash recurred |
| `nas-immich-no-future-dates` | warn | assets with `fileCreatedAt > now()+1y` | no bogus future date is hijacking the timeline |
| `nas-immich-dump-rotation` | warn | count of `immich-*.sql.gz` (≤10) | the keep-N pg-dump rotation is still pruning |

### SM1 — nightly ffmpeg SIGSEGV core dump on one corrupt .mov

`immich_server`'s bundled `jellyfin-ffmpeg` **segfaulted every midnight** decoding one 2021
iPhone video, dumping a fresh ~23 MB `@ffmpeg…core.gz` to the `/volume1` root (5 consecutive
nights). Root cause: the asset — `8a5d0a66-9ee4-47d3-a058-c80eea7d53ba`
(`/data/library/admin/2021/2021-06-28/IMG_3674.mov`, HEVC with a **Frame-Cropping** side
data block) — crashes the HEVC decoder on Immich's preview command (`-skip_frame nointra …`).
It never produced a thumbnail, so Immich's nightly `QUEUE_GENERATE_THUMBNAILS(force=false)`,
which re-queues any asset **missing a preview**, retried it forever. (`ffprobe` reads the file
fine; a `-c copy` remux would not change the crashing bitstream. The NAS `core_pattern` is a
pipe to `syno-dump-core.sh`, so `ulimit -c 0` can't reliably suppress the dump — do **not**
deliberately re-run the crashing command.)

**Quarantine (preserve the asset, stop the loop):** the operator authorization was *stop the
retry, don't delete*. Rather than move the original aside (which risks Immich auto-trashing a
now-missing internal asset), the asset was **marked already-thumbnailed** so it drops out of
the regen queue:

1. Generate a synthetic placeholder preview + thumbnail **inside the container** with ffmpeg's
   `lavfi color` source (never touches the corrupt file):
   - `.../thumbs/936853a2…/8a/5d/8a5d0a66…_preview.jpeg` (mjpeg 1440×1080)
   - `.../thumbs/936853a2…/8a/5d/8a5d0a66…_thumbnail.webp` (webp 250×188)
2. `INSERT INTO asset_file ("assetId", type, path) VALUES (…,'preview',…),(…,'thumbnail',…)`
   — the row's existence is what makes the nightly job skip it. Verified the API now serves
   both (`GET /api/assets/{id}/thumbnail` → 200 image/jpeg + image/webp).
3. Delete the stale core: `rm /volume1/@ffmpeg…core.gz`.

The original `.mov` is untouched — playback and the asset are intact; only the thumbnail is a
grey placeholder. **Do NOT run "Regenerate thumbnails" (force) on this asset** until the source
is repaired/re-encoded — a forced regen deletes the injected preview and re-arms the nightly
crash. `nas-immich-corrupt-mov-quarantined` guards the preview row; `nas-immich-ffmpeg-nocrash`
(and `nas-core-dumps` in `nas-host.yaml`) guard for any recurrence. A second, *hidden* video
(`IMG_2067.MOV`) also lacks a preview but is `visibility=hidden` so it is never re-queued and
never crashes — left as-is.

### SM36 — a second household user with 0 assets ever (needs-human)

Kaelyn Tabaska (`b6be5585-152e-4330-86d2-f52a397ed706`) has **0 photos / 0 videos** since her
account was created 2026-07-14 — her phone backup has never flowed, and the global
`nas-immich-backup-freshness` check structurally can't see it (Brandon's uploads keep it green
forever). New check `immich-user-zero-assets` asserts **every** user has >0 assets — the
mandate-1 per-user signal. It also catches a new family member who never backs up, or an
existing library being wiped. **It is RED today, on purpose** — it is Kaelyn's standing
onboarding reminder (see "Pairing a phone"). Clearing it requires **her device**: open the
Immich app, sign in as `kaelyn92@icloud.com`, enable backup. No server-side action can make it
green — do not disable the check to silence it.

### SL5 — a bogus 4501-01-01 capture date topping the timeline

Asset `a2641009-65a4-4148-b2ee-0d95670b67b5` (`Pic 127.jpg`, from a 2026-07-24 bulk import)
carried `fileCreatedAt = 4501-01-01` (corrupt EXIF), so it permanently sat at the top of every
date-descending view. Corrected via the admin-key API (`PUT /api/assets/{id}` with
`dateTimeOriginal`) to **2025-08-30T16:31:46Z** — the file's `fileModifiedAt`/EXIF `modifyDate`,
a sane proxy since the true capture date is unrecoverable. Verified: newest-by-date is now a
real recent asset (`IMG_2121.WEBP`, 2026-07-29) and the future-dated count is 0. Guarded by
`nas-immich-no-future-dates`.

### SL22 — newest asset 3+ days old (freshness trend)

A trend record, not an incident: uploads paused for a few days (a normal usage lull). Already
bounded by `nas-immich-backup-freshness` (7-day file-mtime window, unaffected by the SL5 date
bug) and now sharpened per-user by `immich-user-zero-assets`. A tighter 3-day freshness alert
was deliberately **not** added — it would false-positive on ordinary gaps and add to alert
fatigue (fix-61).

### SL29 — pg-dumps accumulating without observed rotation

The nightly `immich-db-dump.sh` (DSM Task Scheduler task 9, 02:30) already had a `find -delete`
keep-N rotation, but the sweep observed 16 dumps (~254 MB each) piling up in
`/volume1/docker/immich/backups` and shipping offsite via Hyper Backup. Tightened
`KEEP_DAYS` **14 → 7** (a week of point-in-time logical dumps is ample — HB's own Smart-Recycle
versioning in B2 covers deeper history; halves the redundant-full offsite bloat) and pruned to
8 files. Codified in `foss-setup/scripts/nas/immich-db-dump.sh` (deployed byte-identical to
`/volume1/scripts/nas/immich-db-dump.sh`). `nas-immich-dump-rotation` alerts if the dir grows
past 10 files (rotation stopped).

## If `backup=STALE` fires *after* pairing worked

1. Check the app: Backup screen → stalled uploads, battery-optimization kills
   (Android), or a stale server URL after a cert/domain change.
2. Check the server: `https://immich.tabaska.us` → Admin → Jobs (stuck queues),
   then `sudo docker logs immich_server --since 24h` on the NAS.
3. Check disk truth: `find /volume1/photo/upload -type f -mtime -7 | head` — if files
   land but the API count doesn't move, the DB and disk disagree → treat as an Immich
   bug, check the job queue and the postgres container health.

## Machine-learning GPU contention — night-only rig window (glue-14)

Immich ML (CLIP smart search, `buffalo_l` faces, PP-OCRv5 OCR) is offloaded to the rig's
RTX 3090 Ti (`immich_machine_learning` `-cuda`, `192.168.10.12:3003`). **Problem:** a 24B
chat/coding model needs ~22 GB of the 24 GB card and Immich ML needs ~13 GB, so they
**cannot coexist** — whichever loads second OOMs (`llama-swap: upstream command exited
prematurely` → LiteLLM 500 in OpenWebUI, or Immich `ONNXRuntimeError … Failed to allocate`).
The Immich job queue can read **0 active / 0 waiting while ~13 GB is still pinned**: models
stay resident for the model TTL after the last job, and interactive searches hit ML
directly without ever becoming queue jobs. So "empty queue but GPU busy" is expected, not a
bug.

**Policy (2026-07-24): photos are the lowest-priority GPU tenant.** The rig ML container is
time-gated to a **night window, 01:00–07:00 EDT**, by two systemd timers on the rig
(`immich-ml-window-on/off.timer` → `immich-ml-window.sh`, source
`configs/host/rig/immich-ml/`):

| Time | Action | Effect |
|---|---|---|
| **07:00** off | pause `smartSearch`/`faceDetection`/`ocr`, **stop** the rig container | GPU 100 % free for chat/coding/ComfyUI; Immich falls back to the **NAS iGPU** (OpenVINO) |
| **01:00** on | **start** the container, wait for `/ping`, resume the queues | new-photo backlog crunches fast on the 3090 Ti while nobody's using it |

**Daytime search experience (NAS iGPU):** identical results (same SigLIP2 model/embeddings),
~225 ms warm text-encode vs ~3 ms on the GPU — imperceptible, since a smart search is
already 0.7–2.5 s (DB vector search + network dominated). The NAS `.env` preloads the CLIP
**text** tower (`MACHINE_LEARNING_PRELOAD__CLIP__TEXTUAL`) + `MODEL_TTL=86400` so search
stays warm and never hits the ~27 s cold-load. New-photo **indexing** is much slower on the
iGPU, so its queues are paused by day — new photos become searchable after that night's rig
run. Interactive text search is a live call (not a queue job), so it keeps working by day.

**Monitoring** (`checks.d/rig-immich-ml.yaml`, window-aware):

- `immich-smart-search-consumer` (crit) — smart search returns results end-to-end via
  **whichever** backend is active. The real user-facing signal.
- `rig-immich-ml-window` (warn) — rig ML **up + encoding** at night, **down** by day. A
  `DAY_UNEXPECTED_UP` means the 07:00 off-timer failed and VRAM contention with chat is back.

`docker-fleet.yaml`'s `containers-manifest-rig` **excludes** `immich_machine_learning` (it's
intentionally absent by day) — so it is removed from `verification/coverage/rig.containers`.

### Operating it

- **Force the GPU free now** (e.g. mid-day, need the whole card):
  `sudo systemctl start immich-ml-window@off.service` on the rig.
- **Bring ML back early**: `sudo systemctl start immich-ml-window@on.service`.
- **Change the window**: edit the two timers under `configs/host/rig/immich-ml/`, redeploy,
  `systemctl daemon-reload`. Keep the `rig-immich-ml-window` check's `01`/`07` hour test and
  the runbook table in sync.
- **`DAY_UNEXPECTED_UP` alert**: the off-timer didn't stop the container. Check
  `journalctl -u immich-ml-window@off.service` and `systemctl list-timers immich-ml-window-*`.
- **Known edge case**: if you are actively running a 24B model at **01:00** when the on-timer
  starts Immich ML, that one request can OOM (num_retries then surface a 500). Rare (photos
  run "when offline"); if it bites, escalate to event-driven preemption (Immich yields to any
  LLM/ComfyUI load, not just a fixed clock).

## Version bumps

Re-read release notes, re-verify the Valkey/Postgres digests against that release's
compose, bump `IMMICH_VERSION` in `.env` (live + repo mirror), `docker compose pull &&
up -d`, then confirm `/api/server/version`. Postgres major upgrades are **not**
automatic — never float the DB image. Take a pre-upgrade dump:
`sudo bash /volume1/scripts/nas/immich-db-dump.sh` (the canonical dump script DSM task 9
runs; `immich-pg-dump.sh` is deprecated).
