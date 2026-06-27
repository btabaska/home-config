# Homelab Backup Architecture (3-2-1)

Reference for the FOSS homelab migration. Implements the **3-2-1 rule**: at least
**3** copies of data, on **2** different media, with **1** copy off-site.

- **3 copies** — live data + local backup copy + off-site cloud/SSH copy
- **2 media** — Synology Btrfs volume (NAS) + external HDD + cloud object storage
- **1 off-site** — Backblaze B2 (per-TB) for irreplaceable data; Hetzner Storage Box for SSH/Borg hosts

> **Cost note:** A Synology NAS does **not** qualify for Backblaze's flat $99/yr
> "Computer Backup" plan. The NAS uses **per-TB B2 Cloud Storage ($6.95/TB-month, effective May 1 2026)**
> via Hyper Backup, or **Synology C2** as an alternative. The flat plan is desktop-only.

---

## Data tiers

| Tier | Data | ~Size | Irreplaceable? |
|------|------|-------|----------------|
| **Tier 1** | Immich photos/videos, Postgres dump, documents, Obsidian vault, Home Assistant config, game saves, all compose files + `.env` / configs | ~1–2 TB | **Yes** → must go off-site |
| **Tier 2** | Replaceable media on vol3 `tv`, vol2 `movies`, vol1 `music` + `books` | large | No → daily snapshots + rotated external HDD only |

---

## Mapping: data → tool → target → schedule

| # | Data | Tool | Target | Schedule | Encryption |
|---|------|------|--------|----------|------------|
| 1 | NAS Tier 1 shares (photos, docs, Obsidian, HA config, configs) | **Synology Hyper Backup** | **Backblaze B2** (per-TB, S3-compatible API) | Daily 03:00, Smart Recycle versioning | Client-side encryption ON |
| 2 | All NAS Btrfs shares (fast local rollback / ransomware) | **Snapshot Replication** (Btrfs CoW) | Same NAS volume (+ optional 2nd NAS) | Hourly, GFS retention, immutable snapshots 7–14 days | n/a (local) |
| 3 | Tier 2 media (`/volume3/tv`, `/volume2/movies`, `/volume1/music`, `/volume1/books`) | **Hyper Backup** (or rsync/USB Copy) | **Rotated external HDD** | Weekly, swap drives offsite-in-a-drawer | Optional |
| 4 | Ubuntu / CachyOS host Tier 1 (`/home`, `/etc`, `/opt`, docker volumes) | **restic** (`restic-backup.sh`) | **Backblaze B2** (per-TB) | Daily 02:30 via cron/systemd timer | restic native (AES) |
| 5 | SSH-reachable host Tier 1 (alt off-site path) | **BorgBackup + borgmatic** | **Hetzner Storage Box** (SSH port 23) | Daily, GFS retention, append-only repo | Borg repokey-blake2 |
| 6 | Windows PCs / laptops (optional) | **Synology Active Backup for Business** | NAS volume (then folded into #1) | Daily | n/a → covered by #1 off-site |

**Off-site coverage:** Tier 1 data reaches off-site by **two independent paths** —
NAS shares via Hyper Backup → B2 (#1), and Linux hosts via restic → B2 (#4) and/or
Borg → Hetzner (#5). Tier 2 stays on-NAS + external HDD (#2, #3); it is re-downloadable
so it intentionally does **not** consume cloud spend.

---

## Immich-specific backup

Immich photos live under `UPLOAD_LOCATION` (`/volume1/photo`) on Volume 1 and are
captured by Hyper Backup (#1). The Postgres database needs a **logical dump**, not
a raw file copy, for a clean restore:

- Dump on a schedule (DSM Task Scheduler), then let Hyper Backup ship the dump file:
  ```bash
  docker exec -t immich_postgres pg_dumpall --clean --if-exists -U postgres \
    | gzip > /volume1/docker/immich/backups/immich-$(date +%F).sql.gz
  ```
- Keep the `.env` (it holds `DB_PASSWORD`) and `docker-compose.yml` in Tier 1.
- Restore order: restore files → restore DB dump into a fresh VectorChord Postgres
  container of the **same pinned tag** → `docker compose up -d`.
- Immich's own backup guidance: <https://docs.immich.app/administration/backup-and-restore>

---

## Encryption key handling (do this before relying on backups)

- **restic** repository password → password manager **and** printed on paper.
- **Borg** passphrase → password manager **and** printed.
- **Hyper Backup** client-side encryption key → export the `.pem`, store in password
  manager + printed. Losing it makes the B2 copy unrecoverable.
- Never commit real `.env` / `b2.env` / passphrase files to git.

---

## Restore testing (mandatory, monthly)

A backup that has never been restored is not a backup. Use `scripts/backup/restore-test.sh`:

```bash
ENV_FILE=/etc/restic/b2.env ./restore-test.sh restic
./restore-test.sh borgmatic /etc/borgmatic/config.yaml
```

For Hyper Backup, periodically use **Restore → Backup Explorer** in DSM to pull a
sample folder back and confirm it opens. borgmatic also self-tests via the `extract`
check (`frequency: 1 month`) in `borgmatic-config.yaml`.

---

## Phase summary

- **Phase 1 — Backups first.** Stand up Snapshot Replication, Hyper Backup → B2,
  restic → B2, Borg → Hetzner, store keys, run a restore test. Everything else is
  built on top of working backups.
- **Phase 2 — Immich** (with DB dump job feeding Hyper Backup).
- **Phase 3 — Calibre-Web-Automated.**
- **Plex stays** (lifetime pass) — verify only.

## Authoritative docs

- Hyper Backup → B2: <https://www.backblaze.com/docs/cloud-storage-integrate-synology-hyper-backup-with-backblaze-b2>
- Snapshot Replication: <https://kb.synology.com/en-us/DSM/help/SnapshotReplication/snapshotreplication>
- restic + B2: <https://www.backblaze.com/docs/cloud-storage-integrate-restic-with-backblaze-b2>
- borgmatic + Hetzner: <https://community.hetzner.com/tutorials/install-and-configure-borgmatic/>
- Immich backup/restore: <https://docs.immich.app/administration/backup-and-restore>
- Synology C2 (B2 alternative): <https://c2.synology.com/en-us/backup>
