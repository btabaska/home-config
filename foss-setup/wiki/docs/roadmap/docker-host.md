# Roadmap — docker-host

8 task(s). Status mirrors `docs/progress.json` (the source of truth).

| Task | Title | Status | Effort |
|---|---|---|---|
| `docker-01` | Install Docker Engine + Compose plugin on Ubuntu (Mac mini) | ✅ done | 10 min |
| `docker-02` | Create the shared edge network and /opt/stacks layout | ✅ done | 10 min |
| `fix-39` | mini host cleanup: dead Pterodactyl LEMP + root cron, broken crons, dead stack dirs, reclaimable docker | ✅ done | 1-3 hrs |
| `fix-45` | Fleet hygiene batch: host junk, core dumps, stale caches, log/backup bloat (mini/rig/seedbox) | ✅ done | 1-3 hrs |
| `fix-69` | Fleet hygiene batch: meme-review check-vs-policy contradiction, log floods (synologand 7k, deluged 1.1/s, ufw), stale units/kernel, /tmp session litter incl. cookies, dead experiments | ✅ done | 1-3 hrs |
| `fix-72` | Reconcile the etckeeper /etc repo so git-etckeeper-clean greens | ⬜ open | <1 hr |
| `fix-74` | Perform the pending mini kernel reboot in a maintenance window | ⬜ open | 1-3 hrs |
| `fix-80` | Commit the regenerated /opt/foss-setup manifests + clear clone drift | ⬜ open | <1 hr |

[← Roadmap overview](index.md)
