# Roadmap — backups-offsite

7 task(s). Status mirrors `docs/progress.json` (the source of truth).

| Task | Title | Status | Effort |
|---|---|---|---|
| `fix-42` | Make off-site DR reproducible (ansible backup role is a no-op diverged from live) | ⬜ open | 1-3 hrs |
| `nas-02` | Hyper Backup of NAS Tier 1 shares → Backblaze B2 (client-side encrypted) | ✅ done | 1 hr |
| `nas-03` | Set up Tier 2 media backup to a rotated external HDD | 🗑️ retired | 30 min |
| `nas-04` | Deploy restic → Backblaze B2 on the Ubuntu host | ✅ done | 45 min |
| `nas-05` | Deploy restic → Backblaze B2 on the CachyOS host | ✅ done | 30 min |
| `nas-06` | Deploy BorgBackup + borgmatic → Hetzner Storage Box (optional 2nd off-site) | 🗑️ retired | 1 hr |
| `nas-07` | Store all encryption keys and run a full restore test | ✅ done | 45 min |

[← Roadmap overview](index.md)
