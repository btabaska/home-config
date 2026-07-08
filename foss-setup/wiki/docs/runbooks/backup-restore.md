# Runbook — Backup & restore

Target model: **3-2-1-1-0** — three copies, two media, one off-site (B2), one
immutable (B2 Object Lock), zero restore errors (tested). Tier 1
(irreplaceable: photos, documents, configs, HA, saves) goes off-site;
Tier 2 (re-acquirable media) gets local redundancy only.

!!! warning "Where this stands today"
    **B2 does not exist yet** — no bucket, no keys (pending: nas-02…07,
    sec-03; blocked on the human creating the B2 account + app key into the
    vault). Restic/borgmatic jobs are likewise pending. What exists now:
    the Immich pg_dump on the NAS, DSM snapshots, and config-as-code in git.
    Until B2 lands, the pg_dump is the only Immich safety net.

## What is backed up where (current + planned)

| Data | Mechanism | Status |
|---|---|---|
| Immich Postgres | `/volume1/docker/immich/immich-pg-dump.sh` → `/volume1/docker/immich/backups/` | Script works; **DSM Task Scheduler entry pending** (nas-08): root, daily 02:30 |
| All configs / compose / scripts | git — GitHub `home-config` + Forgejo mirrors | Live |
| `/etc` on mini | etckeeper (auto-commit on apt ops) | Live |
| Dotfiles | chezmoi | Live |
| NAS Tier 1 → B2 | Hyper Backup (S3 API) + Object Lock | pending: nas-02…07 |
| mini/rig → B2 | restic (systemd timers; rig on the same schedule — it runs 24/7) | pending: sec-03 |
| HA full backups → NAS | HA Settings → Backups (key in Bitwarden) | pending: ha track |
| NAS snapshots | Btrfs Snapshot Replication on Tier 1 shares | DSM |
| Tier 2 media | NAS volumes + rotated external HDD | manual |

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
   (pending: sec-03) or the NAS copy.

Full-host rebuilds: [Rebuild a host](rebuild-a-host.md).

## Restore: restic from B2 — pending

Once sec-03/nas-07 land, this section gets the exact
`restic -r b2:<bucket> restore` commands and the quarterly restore-test
procedure. Keys: B2 app key + restic password live in the vault / Bitwarden
(+ printed copy) — **a backup you can't decrypt is not a backup**.

## Verify (any backup work)

- New dump file appeared and is >0 bytes; `gunzip -t` passes.
- Healthchecks ping received (once wired) — silence is a failure.
- Quarterly: one real restore drill, logged in the tracker (glue-06 / sbom-05).
