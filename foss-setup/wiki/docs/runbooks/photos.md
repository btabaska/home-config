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
- **Monitoring API key**: `verification-monitor`, scoped to `server.statistics` only,
  owned by the brandon account. Secret at vault `immich.verify_api_key`, deployed as
  `IMMICH_API_KEY` (+ `IMMICH_URL`) in `/etc/verification/env` on mini. Rotate by
  deleting the `api_key` row named `verification-monitor` and re-inserting
  `sha256(new_secret)` (the `key` column is the raw 32-byte digest, bytea).

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

## Version bumps

Re-read release notes, re-verify the Valkey/Postgres digests against that release's
compose, bump `IMMICH_VERSION` in `.env` (live + repo mirror), `docker compose pull &&
up -d`, then confirm `/api/server/version`. Postgres major upgrades are **not**
automatic — never float the DB image. Take a pre-upgrade dump:
`sudo /volume1/docker/immich/immich-pg-dump.sh`.
