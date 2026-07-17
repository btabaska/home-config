# Roadmap — security

11 task(s). Status mirrors `docs/progress.json` (the source of truth).

| Task | Title | Status | Effort |
|---|---|---|---|
| `fix-21` | Close public exposure of seedbox torrent clients (Deluge RPC/web, qBittorrent, slskd) | ✅ done | 1-3 hrs |
| `fix-22` | Make restic B2 backups actually immutable (default retention) + lock hyper-backup bucket | ✅ done | 1-3 hrs |
| `fix-23` | Secrets & filesystem-permission hygiene (world-readable env, stale local secret dumps) | ⬜ open | 1-3 hrs |
| `foss-01` | Bitwarden → Vaultwarden data cutover (point clients at vault.tabaska.us) | ⬜ open | 1-2 hrs |
| `foss-04` | Ente Auth adoption + YubiKey enrollment (Authy migration) | ⬜ open | 1-2 hrs |
| `sec-01` | Turn on MFA/2FA everywhere (hardware key on the crown jewels) | ⬜ open | 1-2 hrs |
| `sec-02` | Cap Docker logs globally (prevent silent disk-fill) | ✅ done | 15 min |
| `sec-03` | Immutable backups (B2 Object Lock + Borg append-only) + Healthchecks dead-man's-switch | ✅ done | 1-1.5 hrs |
| `sec-04` | Harden exposed surfaces (CrowdSec + forward-auth on the seedbox/public ports) | ⬜ open | 1 hr |
| `sec-05` | OS security patches (unattended-upgrades on Ubuntu; manual cadence on CachyOS) | ✅ done | 20 min |
| `sec-06` | B2 master key custody: regenerate in console, store offline (Bitwarden/paper); optionally scope HB's key | ⬜ open | 15-30 min |

[← Roadmap overview](index.md)
