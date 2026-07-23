# 6. Backup, beyond the NAS

RAID is not a backup — it survives a dead drive, not a deletion, ransomware hit, fire, or theft. Target: **3-2-1 — three copies, two media types, one off-site.**

> **NAS storage layout that implements this tiering:** the drive/pool/shared-folder/network-drive schema lives in `reference/nas/volume-schema.md`. It **retains three Basic volumes** (~42 TB usable, no parity): Volume 1 = Music/Books/Tier 1/Docker, Volume 2 = Movies, Volume 3 = TV — read it before reorganizing shares.

## Tier your data first (the key move)

Don't back up 40 TB to the cloud (~$278/month at B2's ~$6.95/TB). Split it:

- **Tier 1 — irreplaceable (cloud + local).** Immich photos, documents, Obsidian vault, **HA config**, **game-server worlds/saves**, the **CachyOS home directory** (dotfiles, app configs, local projects), all compose files/configs. Realistically 1-2 TB. **Goes off-site to the cloud** (~$7-14/month at B2 — trivial insurance).
- **Tier 2 — replaceable media (local redundancy only).** Ripped movies/shows/music you could re-acquire. NAS RAID + one cold copy; **don't pay to cloud-store it.**
  - **⚠️ Corrected:** the plan suggests a **rotated external HDD** at an office/relative's house for off-site Tier 2. That (`nas-03`) is **retired** — Tier-2 media is re-acquirable, so the rotated-HDD local backup is skipped.

## Tools

- **Synology native (turnkey, start here):** **Hyper Backup** (to B2 / C2 / another Synology / external), **Snapshot Replication** (Btrfs point-in-time — great vs. accidental deletion/ransomware), **Active Backup for Business** (pull backups of your computers, including the Ubuntu box, onto the NAS).
- **Ubuntu/CachyOS → cloud:** **Restic** (single Go binary, native B2/S3, simple password encryption) or **Kopia** (similar + web UI/scheduler).
- **SSH/local targets:** **BorgBackup + Borgmatic** (best compression, fastest restores, YAML scheduling, DB-dump hooks, healthcheck pings) with a cheap SSH storage box.

## Backing up the CachyOS rig (the daily-driver home directory)

`/home/you` holds what a reinstall can't recreate: dotfiles/app configs (`~/.config`), shell/theme, SSH/GPG keys, browser profiles, local game saves, documents/projects not in Git/Proton. Now that the rig runs 24/7, it backs up on plain timers like every other host:

- **What:** target `~` and exclude the firehoses — `~/.cache`, Steam's re-downloadable game files, build/`node_modules`, VM images. A short exclude list turns "hundreds of GB" into the few GB that matter.
- **How:** a **Restic** (or Kopia) job from CachyOS straight to **Backblaze B2** — encrypted, deduplicated, on a plain `systemd` timer (no wake-gating).
- **Also keep a local copy:** point a second Restic repo — or **Synology Active Backup for Business** (Linux agent) — at the **NAS**, so the rig backs up over LAN when up (fast restores), and the NAS sweeps it off-site with the rest of Tier 1.
- **Dotfiles bonus:** keep the dotfiles in the same **Git** repo as compose files (or `chezmoi`). A rig rebuild is `git clone` + restore `~` from Restic.

> **Live status:** restic dead-man checks for **mini + rig** are live and FRESH. The rig's restic job currently covers only `/etc` + `/home` — **`/opt` is not backed up** (the AMP game world lives there); Palworld saves were added explicitly. This gap is tracked in memory `rig-restic-opt-gap`.

## Off-site targets (current pricing)

**Decision: Backblaze B2 is the off-site cloud copy** — the hot Tier-1 target for both the NAS (Hyper Backup over the S3 API) and the Linux hosts (native Restic/Kopia), with **Object Lock** enabled for the immutable copy.

- **⚠️ Corrected:** Hetzner/rsync.net were listed as the optional *second* off-site for bulky Tier 2. That second off-site (`nas-06`) is **retired** — one off-site (B2 with Object Lock) is enough. Reversible if priorities change.

| Target | ~Price | Protocol | Best for |
|---|---|---|---|
| **Backblaze B2 — chosen** | ~$6.95/TB/month, free-ish egress | S3 API | Hot cloud copy of Tier 1; native Restic/Kopia |
| Hetzner Storage Box *(retired 2nd off-site)* | ~$2-3.20/TB | SSH/SFTP/Borg | Cheapest Borg/rsync target (EU) |
| rsync.net *(retired 2nd off-site)* | pricier | SSH/SFTP/Borg | Reliable SSH target, US |
| Rotated external HDD *(retired — `nas-03`)* | one-time drive cost | physical | Off-site copy of bulky Tier 2 |

> Synology units don't qualify for Backblaze's flat $99/year personal plan (that's for direct-attached drives). For the NAS use **B2** (per-TB) or **Synology C2**.

## Immutable / ransomware-proof copy (3-2-1-1-0)

Off-site copies don't help if stolen credentials can *delete or re-encrypt* every backup. Add one **immutable** copy:

- **Backblaze B2 Object Lock** on the Restic/Kopia bucket — a retention window so even your own keys can't delete objects until it expires. **Status:** the security-hardening scope was narrowed to **only B2 Object Lock** (`sec-03`).
- **Local retention runs normally; the immutable tier is B2.** Borg/restic do GFS pruning on the client so local/SSH repos don't grow unbounded — fine, because the ransomware-proof copy is the B2 Object Lock bucket. *(Optional future: server-side append-only Borg — belt-and-suspenders, not required.)*
- **Synology immutable snapshots** (DSM 7.2+) on the NAS shares — a locked read-only point-in-time even an admin can't remove early.

This is the "1" and the "0" in **3-2-1-1-0**: three copies, two media, one off-site, **one immutable**, zero restore errors (verified).

## Live status — NAS Tier-1 → B2 (validated 2026-07-13)

The NAS Tier-1 Hyper Backup → B2 task is **alive, encrypted, and succeeding** (`nas-02`/`#14` closed):

- Task **"S3 Backup enc"** → `TabaskaNAS_2.hbk`, **client-side encryption ON** (`enable_data_encrypt=true`) + TLS in transit; target `s3.us-east-005.backblazeb2.com` / `bucket-hyper-backup`.
- Selects `/backups /docker /docs /homes /photo` = **all shares that hold real data** (`vault` + `appdata` are empty shells superseded by `/docker`). Smart-recycle rotation, notify on.
- The old **unencrypted** `S3 Backup 1` / `TabaskaNAS_1.hbk` was **deleted 2026-07-13** — only the encrypted task remains.
- Encryption key in vault `hosts.nas.hyperbackup_password` (+ Proton Pass).
- A negative-tested dead-man check `nas-hyperbackup-b2-fresh` (crit, 50 h) tracks the encrypted task's completion.

## Database dumps (so a "backup" isn't a corrupt file)

File-copying a *live* DB directory can capture a half-written, unrestorable DB. Dump first, then back up the dump:

- **Postgres** (Immich's VectorChord, Miniflux, Paperless): nightly `pg_dump`/`pg_dumpall` to a `backups/` folder the file job ships off. **Borgmatic** has built-in DB-dump hooks + Healthcheck pings. *(The plan lists Dependency-Track's Postgres here — DT is retired, so drop that line.)*
- **SQLite** (Uptime Kuma, etc.): use the SQLite `.backup` command (or stop-copy-start), not a raw file copy.

## Don't forget

- **Test a restore** at least once. An untested backup is a hope.
- **Store encryption keys/passphrases off the machine** (Proton Pass + a printed copy).
- **Back up Docker volumes** and HA's backup archive, not just visible files.
- **Monitor that backups actually ran** — a dead-man's-switch (self-hosted **Healthchecks.io**, pinged by each job, alerting via ntfy when a ping *doesn't* arrive) catches the silent "the timer's been off for a month" failure. **Live** on the mini.

---
[← index](index.md)
