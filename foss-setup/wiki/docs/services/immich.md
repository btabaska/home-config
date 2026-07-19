# immich

Immich on Synology DS920+ (Container Manager / Docker Compose)

| | |
|---|---|
| **Host** | [nas](../hosts/nas.md) |
| **URL** | https://immich.tabaska.us |
| **Source** | `foss-setup/configs/nas/immich/docker-compose.yml` |
| **Notes** | Photo library + mobile backup. Vhost verified 2026-07-07. |
| **Upstream docs** | <https://github.com/immich-app/immich/releases/latest/download/docker-compose.yml> · <https://docs.immich.app/install/docker-compose> · <https://docs.immich.app/features/hardware-transcoding> |

## About

Immich is a self-hosted photo/video library and mobile-backup app running on the NAS (Synology DS920+, `192.168.10.4`) via DSM Container Manager / Docker Compose, project `immich`, reachable at https://immich.tabaska.us (LAN `http://192.168.10.4:2283`). The stack is four containers — `immich_server` (`2283:2283`), `immich_machine_learning` (OpenVINO variant for face/CLIP inference), a Valkey `redis`, and a VectorChord `postgres` database — pinned to Immich `v3.0.3` via `IMMICH_VERSION` in `.env` (compose uses `${IMMICH_VERSION:?...}` with no floating `release` fallback, so it refuses to start unpinned), with the Valkey and Postgres images digest-pinned to match that exact release (upgraded v2.7.5 → v3.0.3 on 2026-07-18 while the library was still empty, fix-35). Originals live at `UPLOAD_LOCATION=/volume1/photo` (Tier-1 irreplaceable data, backed up via Hyper Backup) and the DB at `DB_DATA_LOCATION=/volume1/docker/immich/postgres` (with `DB_STORAGE_TYPE=HDD` since it sits on spinning Btrfs disks); `/dev/dri` is passed into both the server and ML containers to use the J4125's Intel Quick Sync iGPU for transcoding and inference. Mirrorless-camera SD cards are ingested from a workstation with `immich-go` rather than the mobile app. Content (not liveness) is watched by two verification checks — `nas-immich-backup-freshness` and `nas-immich-mobile-paired` — using a `verification-monitor` API key scoped to `server.statistics` only (vault `immich.verify_api_key`); both alert until a phone is actually paired and uploading (see the [photos runbook](../runbooks/photos.md)). Both accounts (brandon, kaelyn92) are full admins by explicit decision 2026-07-18 (quality-gate M58, accepted).

## Containers

| Service | Image (pinned) | Ports |
|---|---|---|
| `immich-server` | `ghcr.io/immich-app/immich-server:${IMMICH_VERSION:?set IMMICH_VERSION in .env}` | `2283:2283` |
| `immich-machine-learning` | `ghcr.io/immich-app/immich-machine-learning:${IMMICH_VERSION:?set IMMICH_VERSION in .env}-openvino` | — |
| `redis` | `docker.io/valkey/valkey:9@sha256:4963247afc4cd33c7d3b2d2816b9f7f8eeebab148d29056c2ca4d7cbc966f2d9` | — |
| `database` | `ghcr.io/immich-app/postgres:14-vectorchord0.4.3-pgvectors0.2.0@sha256:bcf63357191b76a916ae5eb93464d65c07511da41e3bf7a8416db519b40b1c23` | — |

## Volumes

| Service | Volume |
|---|---|
| `immich-server` | `${UPLOAD_LOCATION}:/data` |
| `immich-server` | `/etc/localtime:/etc/localtime:ro` |
| `immich-machine-learning` | `model-cache:/cache` |
| `database` | `${DB_DATA_LOCATION}:/var/lib/postgresql/data` |

## Environment (`.env`)

Variable names from `.env.example` — real values live in `.env` on the host, sourced from the vault (never committed):

- `IMMICH_VERSION`
- `UPLOAD_LOCATION`
- `DB_DATA_LOCATION`
- `TZ`
- `DB_PASSWORD`
- `DB_USERNAME`
- `DB_DATABASE_NAME`

## Troubleshooting

- **immich-server or immich-machine-learning fails to start after a reboot or DSM update, complaining about /dev/dri** — Confirm the iGPU device still exists on the host: ssh nas then `ls -l /dev/dri` (expect card0 + renderD128). If /dev/dri is missing, remove the `devices: [/dev/dri:/dev/dri]` blocks from docker-compose.yml (both server and ML services) and redeploy; hardware transcoding/OpenVINO will fall back to software.
- **Compose refuses to start with an error about IMMICH_VERSION being unset** — This is intentional (`${IMMICH_VERSION:?set IMMICH_VERSION in .env}` — no floating fallback). Ensure `.env` next to docker-compose.yml at /volume1/docker/immich sets `IMMICH_VERSION=v3.0.3` (or the intended release).
- **Version bump breaks the DB or the pinned Valkey/Postgres digests no longer match the release** — When bumping IMMICH_VERSION, re-read the release notes and re-verify the redis (valkey) and database (VectorChord postgres) image digests against that release's official docker-compose.yml (https://github.com/immich-app/immich/releases/latest/download/docker-compose.yml) — Postgres major upgrades are NOT automatic. Then `cd /volume1/docker/immich && sudo docker compose pull && sudo docker compose up -d`.
- **Hardware transcoding not actually being used after deploy** — The Quick Sync device is passed in but must also be enabled in-app: Admin > Settings > Video Transcoding > Hardware Acceleration = Quick Sync (OpenVINO ML acceleration works automatically via the `-openvino` image).
- **ntfy `verification` alerts `backup=STALE` (nas-immich-backup-freshness) or `paired=NO` (nas-immich-mobile-paired)** — These probe CONTENT, not liveness — the 2026-07-16 audit found every liveness probe green around a zero-asset library because no phone was ever paired (findings H17/H28). `paired=NO` means no iOS/Android session exists: install the Immich mobile app, point it at https://immich.tabaska.us, log in, and enable background backup (steps in the photos runbook). `backup=STALE` with a paired device means uploads stopped flowing — check the app's backup screen for stalled uploads, then the server job queue at Admin > Jobs.

## Operations

```bash
# NAS stack — manage via DSM Container Manager (project: immich)
# or over SSH (sudo required): cd /volume1/docker/immich && sudo docker compose ps
```

Update procedure: [Runbooks → Update images](../runbooks/update-images.md). Full add/change loop: [Runbooks → Add a service](../runbooks/add-a-service.md).

*Generated by `scripts/docs/gen-wiki-services.py` — do not edit by hand; edit the compose file and regenerate.*
