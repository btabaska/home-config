# Runbook — Backup & restore

Target model: **3-2-1-1-0** — three copies, two media, one off-site (B2), one
immutable (B2 Object Lock), zero restore errors (tested). Tier 1
(irreplaceable: photos, documents, configs, HA, saves) goes off-site;
Tier 2 (re-acquirable media) gets local redundancy only.

!!! success "Where this stands (re-verified live 2026-07-13)"
    **B2 exists and restic to it is LIVE on the mini and the rig** — daily
    systemd timers, both dead-manned in Healthchecks (`restic-backup-mini`,
    `restic-backup-rig`, green; re-probed 2026-07-13: mini snapshot 17.7h old,
    rig 13.8h — both FRESH). The nightly Immich pg_dump is live and
    dead-manned (`immich-dump-nas`).
    **NAS Tier 1 → B2 via Hyper Backup (nas-02) is DONE and now CLIENT-SIDE
    ENCRYPTED.** The 2026-07-13 re-probe found the task alive and succeeding, so
    the earlier "pending" was stale; the task was then **re-created with
    client-side encryption ON** ("S3 Backup enc" → `TabaskaNAS_2.hbk`,
    `enable_data_encrypt=true`, first full encrypted backup completed
    2026-07-13 13:45; key in vault `hosts.nas.hyperbackup_password` + Bitwarden).
    The old unencrypted `S3 Backup 1` / `TabaskaNAS_1.hbk` is being retired.
    nas-06 (optional Hetzner 2nd off-site) was **retired** in the 2026-07-13
    roadmap prune — one off-site (B2) is the accepted design.

## What is backed up where (current + planned)

| Data | Mechanism | Status |
|---|---|---|
| Immich Postgres | NAS Task Scheduler nightly → `/volume1/docker/immich/backups/` | **Live**, dead-manned (`immich-dump-nas`; 2026-07-09 fix: hardcode `/bin/curl` — DSM cron PATH has no `curl`) |
| All configs / compose / scripts | git — GitHub `home-config` + Forgejo mirrors | Live |
| `/etc` on mini | etckeeper (auto-commit on apt ops) | Live |
| Dotfiles | chezmoi | Live |
| mini → B2 | restic daily timer: `/opt/stacks /etc ~/.ssh ~/.config ~/.docker` (env `/etc/restic/env`) | **Live**, dead-manned |
| rig → B2 | restic daily timer: `/etc /home/btabaska` + Palworld saves + the AMP `MinecraftCross01` instance (gap closed — was missing until 2026-07-09) | **Live**, dead-manned |
| NAS Tier 1 → B2 | Hyper Backup task "S3 Backup enc" → S3-compat `s3.us-east-005.backblazeb2.com` / `bucket-hyper-backup` / `TabaskaNAS_2.hbk`; selects `/backups /docker /docs /homes /photo` (covers all shares with real data — `vault`/`appdata` are empty 28K shells superseded by `/docker`); smart-recycle rotation; notify on | **Live + client-side ENCRYPTED** (nas-02; re-created encrypted 2026-07-13, first full backup 13:45; `enable_data_encrypt=true` + TLS in transit; key in vault `hosts.nas.hyperbackup_password` + Bitwarden), dead-manned (`nas-hyperbackup-b2-fresh`, crit, 50h). Old unencrypted `TabaskaNAS_1.hbk` being retired. |
| 2nd off-site → Hetzner | borgmatic (optional) | pending: nas-06 |
| HA full backups → NAS | HA Settings → Backups (key in Bitwarden) | pending: ha track |
| NAS snapshots | Btrfs Snapshot Replication on Tier 1 shares | DSM |
| Tier 2 media | NAS volumes + rotated external HDD | manual |

The ansible `backup` role that would *manage* the restic units is still
SOPS-gated (sec-03) — the live timers were hand-deployed from
`scripts/backup/`; treat the repo scripts as their source.

## Restore: Immich database (the drill that matters now)

Immich data = photo files under `UPLOAD_LOCATION` (`/volume1/...`) **plus**
the Postgres DB. Files without the DB lose albums/faces/metadata.

```bash
# 1. Stop the app (keep the DB up)  — on the NAS
cd /volume1/docker/immich
sudo docker compose stop immich-server immich-machine-learning

# 2. Pick the dump
ls -lt /volume1/docker/immich/backups/   # newest .sql.gz

# 3. Restore into the running postgres container
gunzip -c backups/<dump>.sql.gz \
  | sudo docker exec -i immich_postgres psql -U <DB_USERNAME> -d <DB_DATABASE_NAME>
# (drop/recreate the DB first for a clean restore:
#  docker exec -i immich_postgres psql -U <u> -c 'DROP DATABASE <db>; CREATE DATABASE <db>;')

# 4. Restart and verify
sudo docker compose up -d
curl -fsS http://192.168.10.4:2283/api/server/ping   # {"res":"pong"}
```

Credentials come from `/volume1/docker/immich/.env` (never from a doc).
Then spot-check: log in, confirm albums and people are intact.

## Restore: a service's config/state on the mini

1. `git clone` the stack from Forgejo `home/docker-stacks` (or `configs/docker-stack/stacks/<name>`).
2. Recreate `.env` from `.env.example` + the vault.
3. `docker compose up -d`, then restore any data volume from restic
   (`/opt/stacks` is in the mini's BACKUP_PATHS) or the NAS copy.

Full-host rebuilds: [Rebuild a host](rebuild-a-host.md).

## Restore: restic from B2

The repo/env/paths live on each host at `/etc/restic/env` (600, root). All
restic credentials are in that file and in the vault
(`backblaze_b2.restic_password_mini` / `_rig`) — **a backup you can't
decrypt is not a backup**.

```bash
# List snapshots (on the host being restored)
sudo bash -c 'set -a; . /etc/restic/env; restic snapshots --compact | tail'

# Restore one path from the latest snapshot into a scratch dir (never in place)
sudo bash -c 'set -a; . /etc/restic/env; restic restore latest \
  --target /tmp/restore --include /opt/stacks/<name>'
```

Scripted monthly proof: `scripts/backup/restore-test.sh restic`
(`ENV_FILE=/etc/restic/env`) — restores the latest snapshot to a temp dir
and verifies files exist; read-only for the live system and the repo.

## Verify (any backup work)

- New dump file appeared and is >0 bytes; `gunzip -t` passes.
- Healthchecks ping received — silence is a failure (`restic-backup-mini`,
  `restic-backup-rig`, `immich-dump-nas`).
- Monthly: `restore-test.sh`; quarterly: a real restore drill, logged in the
  tracker (glue-06 / sbom-05 — both still open).
