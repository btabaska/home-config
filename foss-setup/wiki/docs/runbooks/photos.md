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
| `nas-immich-mobile-paired` | `session` table via psql (nas-sudo idiom) | ≥1 iOS/Android session exists — a real phone is attached |

Both are `severity: warn`, daily sweep tier, ntfy topic `verification`. The freshness
check is the **regression** guard (exact H17 bug: empty/stale library behind green
liveness); the paired check is the **class** guard (server green but no consumer ever
connected — catches never-paired, all-devices-revoked, and a family account that never
completed setup).

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
`sudo /volume1/docker/immich/immich-pg-dump.sh`.
