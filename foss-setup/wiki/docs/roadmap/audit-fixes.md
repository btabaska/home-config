# Roadmap — audit-fixes

20 task(s). Status mirrors `docs/progress.json` (the source of truth).

| Task | Title | Status | Effort |
|---|---|---|---|
| `fix-01` | Fix set -e in self-healing scripts (failures silently ignored) | ✅ done | 20 min |
| `fix-02` | Fix $COMPOSE word-splitting (convert to bash array) | ✅ done | 15 min |
| `fix-03` | Fix install-slskd-native.sh default path ($HOME/$HOME bug) | ✅ done | 15 min |
| `fix-04` | Idempotency guard for /etc/fuse.conf append in rclone mount script | ✅ done | 10 min |
| `fix-05` | Version-pin reconciliation (README table vs compose reality) | ✅ done | 45 min |
| `fix-06` | Repair ansible-pull convergence (12/12 runs failing on mini) | ✅ done | 1-1.5 hr |
| `fix-07` | Repo topology: publish foss-setup as git subtree to Forgejo (deploy repo) | ✅ done | 1 hr |
| `fix-08` | Commit /opt/stacks drift on mini + add dirty-repo check to monitoring | ✅ done | 30 min |
| `fix-09` | Repair etckeeper on mini (HEAD ref lock — /etc autocommits dead) | ✅ done | 20 min |
| `fix-10` | Clean stale CIFS fstab mounts on mini (fail at every boot) | ✅ done | 20 min |
| `fix-11` | Fix Maintainerr crash loop (181 restarts — data-dir perms) | ✅ done | 20 min |
| `fix-12` | Decommission duplicate mini Immich (crash-looping ×109) — canonical is NAS | ✅ done | 30 min |
| `fix-13` | Rig convergence — GPU cap redeploy + ansible-pull + SBOM timer | ✅ done | 45 min |
| `fix-14` | Secrets hygiene — strip leaked ntfy token from git + rotate exposed creds | ✅ done | 45 min |
| `fix-15` | Docs reorg — root README index, archive stale docs, surgical plan fixes | ✅ done | 1.5 hr |
| `fix-16` | Progress-as-code — canonical docs/progress.json in git | ✅ done | 30 min |
| `fix-17` | Archive migration-snapshot (15 GB, zero backup, contains Plex tokens) to NAS | ✅ done | 30 min + transfer |
| `fix-18` | Ratify placement decisions & purge legacy leftovers (D2–D5) | ✅ done | 30 min + your answers |
| `fix-19` | Docker default-address-pools on mini (stop 192.168.x squatting) — maintenance window | ✅ done | 20 min (4-7AM window) |
| `fix-20` | Recover rig root btrfs read-only incident + durable OS-NVMe fix | ⬜ open | 1-3 hrs |

[← Roadmap overview](index.md)
