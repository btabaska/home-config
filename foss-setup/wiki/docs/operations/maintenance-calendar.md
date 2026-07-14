# Maintenance calendar

> What runs when — the recurring maintenance surface of the fleet. Most of it is
> automated by systemd timers and container schedules; the manual rows are the ones that
> need a human. Times are the unit's own `OnCalendar` (mixed TZ — see notes).

_Compiled 2026-07-14 from the live systemd timers (`reference/hosts/systemd-units.md`), container schedules, and the NAS backup architecture. If you change a timer, update this page._

## Automated — sub-hourly

| Cadence | Job | Host | What |
|---|---|---|---|
| every 60 s | `net-selfheal.timer` | mini | Network watchdog — renew→link-bounce→networkd-restart if off-net |
| every 10 min | `ai-stack-watchdog.timer` | rig | Restarts the local-AI stack if unhealthy |
| every 20 min | `pcie-aer-monitor.timer` | rig | Scans PCIe AER errors on the NVMe → ntfy on new errors |
| hourly `:40` | `verification-quick.timer` | mini | Quick verification checks |
| hourly | Navidrome scanner (`ND_SCANNER_SCHEDULE=@every 1h`) | mini | Picks up new music from the NAS |
| hourly | Btrfs Snapshot Replication | NAS | CoW snapshots, GFS retention, immutable 7–14 days |

## Automated — daily

| Time | Job | Host | What |
|---|---|---|---|
| 01:30 | `restic-backup.timer` | mini + rig | Tier-1 restic → Backblaze B2, dead-man monitored |
| 03:10 | `borgmatic.timer` | (mini) | Borg → Hetzner — **not deployed** (template only) |
| 04:20 | `ansible-pull.timer` | each host | Converge against `forgejo:home/homelab` |
| 05:00 | `nas-music-mirror.timer` | rig | **Sole** `~/Music` mirror: FLAC → ALAC (.m4a) transcode + mp3/aac verbatim; owns the `music-mirror-rig` dead-man (media-06 — the 05:30 rsync mirror was retired) |
| 05:00 | Kometa (`KOMETA_TIME=05:00`) | mini | Rebuild Plex collections / overlays |
| 06:00 | Diun (`DIUN_WATCH_SCHEDULE=0 6 * * *`) | mini | Check for new image tags → notify (no auto-update) |
| 07:15 (PT) | `verification.timer` | mini | Full verification sweep |
| nightly | Synology Hyper Backup "S3 Backup enc" | NAS | Tier-1 shares → B2, **client-side encrypted**, Smart Recycle |

## Automated — weekly

| Cadence | Job | Host | What |
|---|---|---|---|
| Mon 04:00 | `export-manifests.timer` | mini | Export inventory / SBOM manifests |

## Manual — periodic

| Cadence | Task | What |
|---|---|---|
| Weekly | Review Diun notifications → pull & roll updates | [Runbooks → Update images](../runbooks/update-images.md) |
| Weekly | Swap the rotated external HDD (Tier-2 media) | **Planned** (drive-in-a-drawer offsite) |
| Monthly | `scripts/backup/restore-test.sh restic` | Scripted proof that a restore actually works |
| Quarterly | Full restore drill in a throwaway VM, logged | [Restore runbook template](restore-runbook-template.md) — a procedure you've never run is a wish, not a backup |

## Continuous / event-driven (no schedule)

- **Caddy TLS** — auto-renews Let's Encrypt certs via the Cloudflare DNS-01 issuer (~60-day, no action).
- **Healthchecks** — dead-man pings; a missed ping alerts via ntfy. Timers/agents inside the LAN must ping the **private-IP** URL.
- **ntfy** — the alert bus (AER monitor, backup results, watchdogs).

!!! note "Timezone caveats"
    Timers run in mixed zones: mini is UTC (`04:20` = `00:20` EDT for `ansible-pull`),
    `music-mirror` uses `America/New_York`, `verification` uses `America/Los_Angeles`.
    Read each unit's `OnCalendar` in `reference/hosts/systemd-units.md` rather than assuming.

!!! warning "Maintenance window"
    Disruptive work (reboots, migrations, network changes) goes in the **04:00–07:00 EST**
    window. `apply-static-ip` was a one-shot (2026-07-10, done); `sbom-nightly` is retired.

---

See also: [Troubleshooting index](../runbooks/troubleshooting.md) · [Fleet systemd units](../reference/hosts/systemd-units.md) · [NAS backup architecture](../reference/nas/backup-architecture.md)
