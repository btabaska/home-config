# Roadmap — ops

33 task(s). Status mirrors `docs/progress.json` (the source of truth).

| Task | Title | Status | Effort |
|---|---|---|---|
| `dns-01` | DNS core on mini (Unbound + AdGuard upstream + tabaska.us rewrites) | ✅ done | 45-60 min |
| `dns-02` | Deploy NAS secondary AdGuard + mirror rewrites (DHCP DNS #2) | ✅ done | 30-45 min |
| `dns-03` | UniFi DHCP fail-open DNS chain (mini → NAS → gateway) | ✅ done | 15 min |
| `dns-04` | DNS outage runbook + automated verify script | ✅ done | 15 min |
| `dns-05` | NAT :53 redirect + DoH blocking (only after fail-open chain) | 🗑️ retired | 20-30 min |
| `dns-06` | NAS AdGuard: external resolution failing (dns-nas-external crit) | ⬜ open | 20-40 min |
| `docker-06` | Deploy Caddy reverse proxy with automatic HTTPS | ✅ done | 45 min |
| `docker-07` | Deploy AdGuard Home network DNS filtering (chosen over Pi-hole) | ✅ done | 30 min |
| `docker-08` | Deploy Dockge container manager (chosen default; Dockhand is optional upgrade) | ✅ done | 15 min |
| `docker-09` | Deploy ntfy push-notification backbone | ✅ done | 25 min |
| `docker-10` | Deploy Beszel monitoring hub + agent | ✅ done | 25 min |
| `docker-11` | Deploy Uptime Kuma uptime monitoring | ✅ done | 30 min |
| `docker-12` | Deploy Diun image-update notifier (notify-only) | ✅ done | 20 min |
| `docker-13` | Commit the whole Docker stack to Git (rebuildable in an hour) | ✅ done | 20 min |
| `docker-14` | Serve your own apps on the LAN — Caddy-fronted Compose stacks (optional Coolify behind Caddy) | ✅ done | 30-60 min |
| `docker-15` | Deploy Homepage — one dashboard (your observability + the household front door) | ✅ done | 45-60 min |
| `fix-32` | Fix Caddy reverse-proxy routes (ha.tabaska.us 400, llamaswap not reloaded, stray placeholders/vhosts) | ✅ done | 1-3 hrs |
| `fix-41` | Repo-vs-live drift codification (forgejo stack, manifests, .env keys, ansible units) | ✅ done | 1-3 hrs |
| `glue-05` | Self-host Forgejo (config-as-code forge) on the Ubuntu box | ✅ done | 30-45 min |
| `glue-06` | Push ALL configs to Git + run the rebuild drill (capstone) | ⏸️ deferred | 1-2 hr |
| `glue-07` | Fleet maintenance with Ansible (run one command across every box) | ✅ done | 1-1.5 hr |
| `glue-08` | Self-converging fleet with ansible-pull + roles (the set-and-forget layer) | ✅ done | 2-3 hr |
| `glue-10` | Deploy Scrutiny (disk SMART health) across the fleet + Homepage widget | ✅ done | 1.5 hr |
| `glue-11` | Capture the rig fstab NAS mounts + Docker service drop-in in the repo (anti-drift) | ✅ done | 20-30 min |
| `glue-12` | Reconcile the uncommitted /opt/stacks drift on the mini + protect backup blobs from git (docker-stacks hygiene) | ✅ done | 30-45 min |
| `glue-13` | Audit + codify (or document external ownership of) the remaining live-only rig host units | ⬜ open | 30-45 min |
| `nas-31` | Immich: backup freshness + mobile pairing checks failing (fix-35 regression) | ⬜ open | 30-60 min |
| `net-16` | homepage container DNS: EAI_AGAIN on tabaska.us names (159 errors/2h) | ⬜ open | 20-40 min |
| `sbom-01` | Deploy OWASP Dependency-Track v5 (the SBOM / vulnerability dashboard) | 🗑️ retired | 45-60 min |
| `sbom-02` | Nightly SBOMs with Syft + Grype, uploaded to Dependency-Track | 🗑️ retired | 45-60 min/host |
| `sbom-03` | Track /etc in Git with etckeeper (auto-commit on every package op) | ✅ done | 30-45 min/host |
| `sbom-04` | Export package manifests, cron jobs & timers to the control repo | 🗑️ retired | 30 min/host |
| `sbom-05` | Write per-host restore runbooks and run a whole-host rebuild drill | ⏸️ deferred | 2-3 hr |

[← Roadmap overview](index.md)
