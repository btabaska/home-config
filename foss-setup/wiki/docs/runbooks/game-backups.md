# Runbook — game backups & tunnels (silent AMP backup freeze / restic bloat / playit UDP)

**Task:** `fix-34` · **Findings:** H10, M29, M30 · **Host:** rig (AMP/MinecraftCross01 + playit)

## The failure class

Three ways the game stack rots while every liveness check stays green:

1. **Silent backup refusal (H10).** AMP's `LocalFileBackupPlugin` combined
   `Limits.MaxBackupCount=28` with `Limits.ReplacePolicy=DoNothing`. Once 28
   zips existed, every hourly scheduled backup logged
   `Backup not taken: Backup count limit reached.` and did nothing — ~115
   consecutive refusals over 5 days. Nothing consumed that log line; local
   restore points froze at 2026-07-10 22:00.
2. **Dedup-hostile bloat shipped off-site (M29).** The frozen `Backups/` dir
   (28 × ~458 MB zips = 12 G of a 445 M world) sat inside restic's
   `BACKUP_PATHS`, inflating the B2 repo by ~12 G for restore points restic
   already had in better form (the live world dir, snapshotted nightly).
3. **UDP tunnels die while TCP lives (M30).** The playit agent's UDP claim
   registration wedges (~daily historically:
   `got unexpected response from register request ...UdpChannelDetails`).
   Java/TCP keeps serving, so port checks stay green while every Bedrock and
   Palworld player is locked out until the agent restarts.

## Fixed state (2026-07-18)

- **Policy:** `ReplacePolicy=ReplaceOldest` ("Delete Single Oldest") +
  `MaxBackupCount=24` on MinecraftCross01 — a rolling 24 h of hourly local
  restore points (~7 G). Set live via the AMP API (`Core/SetConfig`, no
  instance restart needed). The 28 frozen zips were deleted through
  `LocalFileBackupPlugin/DeleteLocalBackup` (manifest stays consistent —
  never `rm` zips behind AMP's back).
- **Restic:** `scripts/backup/excludes-rig.txt` (deployed to rig
  `/etc/restic/excludes.txt`) now excludes
  `/opt/stacks/amp/config/.ampdata/instances/*/Backups`. The B2 bloat ages out
  via the nightly `forget` + Sunday prune — no manual repo surgery.
- **playit:** `playit-udp-guard.timer` (rig, every 10 min, from
  `configs/host/rig/playit-udp-guard/`) RakNet-pings the local Geyser origin
  (127.0.0.1:19132) and the public tunnel (`bedrock.tabaska.us:1111`). Only
  the combination *local healthy + public dead* indicts playit → one
  `docker restart playit` (skipped if the container is <10 min old, so a
  broken upstream can't cause flapping). Success pings the healthchecks
  dead-man `playit-udp-rig` (20-min period / 15-min grace, ntfy-routed).

## Checks that guard this (verification/checks.d/gaming.yaml)

| check | what it proves | fires when |
|-------|----------------|------------|
| `game-amp-backup-fresh` | newest local zip <4 h old and last backup event wasn't a refusal | backups silently stop again (exact H10 regression) |
| `game-amp-backup-policy` | no instance carries `ReplacePolicy=DoNothing` | the root-cause config returns on ANY instance (crit) |
| `restic-bloat-rig` | latest AMP-bearing snapshot ships no `Backups/*.zip` | the exclusion is removed/bypassed (M29 class; scan lives in `restic-snapshot-hygiene`) |
| `game-playit-bedrock-udp` | RakNet pong from mini through the public UDP tunnel | the consumer Bedrock path is dead (crit) |
| `game-playit-udp-register-errors` | no register-error signatures in 24 h of agent logs | the UDP-claim class recurred at all, even if self-healed |

## If a check fires

- **BACKUP-REFUSED / POLICY-DONOTHING:** someone or something reset the
  backup limits. Fix live via API (no restart):
  `Core/SetConfig` node `LocalFileBackupPlugin.Limits.ReplacePolicy` value `1`
  through `ADSModule/Servers/<id>/API/` (creds: vault `cubecoders_amp.*`).
  Verify with `grep ReplacePolicy .../MinecraftCross01/LocalFileBackupPlugin.kvp`
  → must not be `DoNothing`.
- **BACKUP-STALE with a sane policy:** check the instance is actually up and
  the scheduler ran: `grep -aE 'Creating Backup|Backup not taken'` in the
  newest `AMP_Logs/AMPLOG_*.log`.
- **BLOAT:** `sudo grep Backups /etc/restic/excludes.txt` on rig — restore the
  `instances/*/Backups` line from `scripts/backup/excludes-rig.txt` and
  redeploy (root 0644).
- **NO-PONG (public) but guard logs say local is dead too:** it's Geyser/AMP,
  not playit — check the MinecraftCross01 instance; do NOT restart playit.
- **NO-PONG with healthy local:** the guard should have already restarted the
  agent (see `journalctl -u playit-udp-guard.service`). If it's throttled or
  still dead: `ssh rig 'sudo docker restart playit'`; if a tunnel was newly
  claimed, `docker compose up -d --force-recreate` in `/opt/stacks/playit`.
- **REGISTER-ERRORS with everything else green:** the class recurred and
  self-healed — no action, but note the date; if it becomes much more frequent
  than ~daily, take it to playit.gg support with the log excerpts.

Source checks: `verification/checks.d/gaming.yaml` + BLOAT scan in
`scripts/backup/restic-snapshot-hygiene.sh` · Dead-man: healthchecks
`playit-udp-rig` · Findings closed: H10, M29, M30
(`docs/quality-gate-2026-07-16.md`).
