# Runbook — Backup & restore

Target model: **3-2-1-1-0** — three copies, two media, one off-site (B2), one
immutable (B2 Object Lock GOVERNANCE 30d on `bucket-restic` — live since
2026-07-17, see [Immutability](#immutability-b2-object-lock-fix-22-2026-07-17)),
zero restore errors (tested). Tier 1
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
    The old unencrypted `S3 Backup 1` / `TabaskaNAS_1.hbk` was deleted 2026-07-13.
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
| NAS Tier 1 → B2 | Hyper Backup task "S3 Backup enc" → S3-compat `s3.us-east-005.backblazeb2.com` / `bucket-hyper-backup` / `TabaskaNAS_2.hbk`; selects `/backups /docker /docs /homes /photo` (covers all shares with real data — `vault`/`appdata` are empty 28K shells superseded by `/docker`); smart-recycle rotation; notify on | **Live + client-side ENCRYPTED** (nas-02; re-created encrypted 2026-07-13, first full backup 13:45; `enable_data_encrypt=true` + TLS in transit; key in vault `hosts.nas.hyperbackup_password` + Bitwarden), dead-manned (`nas-hyperbackup-b2-fresh`, crit, 50h). Old unencrypted `TabaskaNAS_1.hbk` deleted 2026-07-13 — only the encrypted task remains. |
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

## Rebuild the restic deployment from ansible (fix-42, 2026-07-19)

`configs/ansible/roles/backup` is the **deployer of record** for restic on
mini + rig: it installs the live-mirrored `scripts/backup/*` files *verbatim*
(pinned restic 0.19.1 to `/usr/local/bin` on Ubuntu — apt's 0.12 is removed;
pacman on Arch), the backup/alert scripts, the service + timer +
`ntfy-notify@` units, the healthchecks dead-man drop-in, the per-host
excludes, and the verification wrappers + sudoers. The nightly `ansible-pull`
(mini 04:35, rig 04:44) re-converges all of it — a hand-edit on a host is
overwritten within a day.

Until 2026-07-19 the role was a **silent no-op** (gated on a never-seeded SOPS
file, M52), and the fix-20 rig rebuild showed the cost: restic was restored by
hand but `ntfy-notify@` and the dead-man drop-in were lost — `restic-backup-rig`
in healthchecks sat "down" with nobody pinging it.

**The only hand-seeded piece** is `/etc/restic/env` (root 0600) on each host —
the role installs everything else and only arms the timer once this file
exists. Seed it from `scripts/backup/restic-backup.env.example` with, per host:

- `RESTIC_REPOSITORY` (`b2:bucket-restic:<host>`), `RESTIC_PASSWORD`
  (vault `backblaze_b2.restic_password_mini` / `_rig`)
- `B2_ACCOUNT_ID`/`B2_ACCOUNT_KEY` = the **append-only** key
  (`backblaze_b2.restic_append_only_key_id` / `_key`)
- `BACKUP_PATHS` (per-host sets documented in the env example),
  `RESTIC_EXCLUDE_FILE=/etc/restic/excludes.txt`,
  mini only: `PRE_BACKUP_SCRIPT=/opt/scripts/pre-backup-db-dumps.sh`
- `RESTIC_HC_URL` (vault `healthchecks.restic_mini_ping_url` / `restic_rig_ping_url`)
  — the dead-man drop-in *sources* the env with `sh`, so either `KEY=VALUE` or
  `export KEY=VALUE` works. **Never point a systemd `EnvironmentFile=` at this
  file**: systemd logs rejected lines verbatim to the journal (leaked the restic
  password + B2 keys on 2026-07-19 before the drop-in was redesigned)
- rig only: `NTFY_URL` + `NTFY_TOKEN` for `ntfy-notify.sh` failure alerts
  (mini reads them from `/etc/verification/env`)

Guards (daily, `verification/checks.d/backups.yaml`, task `fix-42`):
`restic-role-matches-source-{mini,rig}` (every role-owned file byte-matches the
host's ansible-pull checkout, timer enabled, restic ≥ pin, mini: apt restic
absent), `ansible-site-converged-mini` (full `site.yml --check` reports
`changed=0 failed=0` — the class check for *any* role drifting from live),
`ansible-pull-ok-rig` (the convergence loop itself is alive; mini equivalent is
`sys-ansible-pull`).

## Immutability: B2 Object Lock (fix-22, 2026-07-17)

The quality-gate audit (H20) found the documented "GOVERNANCE 30d" immutability
was **not in effect** — `bucket-restic` had File Lock *enabled* but no default
retention and no per-file retention, so the only guard was the append-only key.
Resolved 2026-07-17:

- **`bucket-restic`**: default retention **GOVERNANCE 30 days** + a one-time
  backfill locked all 1174 pre-existing pack versions. New uploads are locked
  automatically at upload — the append-only keys on mini/rig need no extra
  capabilities. restic `forget`/`prune` still work: restic ≥0.19 deletes by
  *hiding*, and the lifecycle rule (`daysFromHidingToDeleting: 30`) hard-deletes
  only after both the hide window and retention have passed.
- **`bucket-hyper-backup`**: **deliberately NOT locked** (M37, accepted).
  Hyper Backup's Smart Recycle rotation must delete old versions; retention
  would break it. Compensating controls: the delete-capable master key is out
  of the vault (below), and the backup content is client-side encrypted.
- **Master key retired from the vault**: it carries `deleteFiles` +
  `bypassGovernance`, so a laptop/vault compromise could hard-delete
  everything despite GOVERNANCE. Day-to-day access is now the scoped read-only
  `b2-ops` key (vault `backblaze_b2.ops_key_id`/`ops_key` — list/read only).
  Bucket admin uses the offline master key via
  `scripts/backup/b2-apply-bucket-policy.py` (idempotent re-apply + backfill).
- **Junk cleanup**: orphan empty `bucket-rustic` (typo bucket) deleted (L58);
  the three 8-byte `ao-verify` test snapshots forgotten (L57) — their synthetic
  hostnames put them in their own forget group, retained forever.

Daily checks (all in `verification/checks.d/backups.yaml`, task `fix-22`):
`b2-restic-immutable` (crit — asserts retention config **and live-attempts a
delete with the vault key, expecting HTTP 401**), `b2-bucket-policy` (bucket-set
manifest — catches unknown/typo buckets and policy drift),
`restic-snapshot-hygiene-{mini,rig}` (no synthetic-host/test snapshots).

## Verify (any backup work)

- New dump file appeared and is >0 bytes; `gunzip -t` passes.
- Healthchecks ping received — silence is a failure (`restic-backup-mini`,
  `restic-backup-rig`, `immich-dump-nas`).
- Monthly: `restore-test.sh`; quarterly: a real restore drill, logged in the
  tracker (glue-06 / sbom-05 — both still open).
