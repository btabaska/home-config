# Fleet systemd units — index

> Master index of every systemd `.service`/`.timer` unit tracked in the control repo — what it does, which host runs it, when it fires, and where the source lives.

_Source: `foss-setup/configs/ansible/ansible-pull.service`, `foss-setup/configs/ansible/ansible-pull.timer`, `foss-setup/configs/systemd/display-policy.service`, `foss-setup/configs/systemd/wake-rig-listener.service`, `foss-setup/scripts/backup/borgmatic.service`, `foss-setup/scripts/backup/borgmatic.timer`, `foss-setup/scripts/backup/restic-backup.service`, `foss-setup/scripts/backup/restic-backup.timer`, `foss-setup/scripts/backup/ntfy-notify@.service`, `foss-setup/scripts/gaming/gpu-power-tune.service`, `foss-setup/scripts/inventory/export-manifests.service`, `foss-setup/scripts/inventory/export-manifests.timer`, `foss-setup/verification/systemd/verification.service`, `foss-setup/verification/systemd/verification.timer`, `foss-setup/verification/systemd/verification-quick.service`, `foss-setup/verification/systemd/verification-quick.timer`, plus the host-specific units under `foss-setup/configs/host/mini` and `foss-setup/configs/host/rig`_ · migrated + validated 2026-07-14

This page is the single index for **every** systemd unit file checked into the repo, found via:

```
find foss-setup/configs foss-setup/scripts foss-setup/verification -type f \( -name '*.service' -o -name '*.timer' \)
```

Hosts referenced below: `mini` = 192.168.10.2, `nas` = 192.168.10.4 (Synology; runs Docker, no systemd fleet units), `rig` = 192.168.10.12, `HA` = 192.168.10.50. The seedbox `betty` is Ansible-managed and also carries `ansible-pull` + `restic-backup`.

## Master table

| Unit | Host(s) | Purpose | Schedule (timers) | Source path |
|------|---------|---------|-------------------|-------------|
| `ansible-pull.service` | mini, rig, betty (all Ansible hosts) | oneshot: clone control repo, `ansible-pull` `site.yml` against `$(hostname -s)` with `--connection local --diff` — self-converging fleet (glue-08). `--check` removed 2026-07-07 so it APPLIES, not dry-runs | (via timer) | `foss-setup/configs/ansible/ansible-pull.service` |
| `ansible-pull.timer` | mini, rig, betty | fire fleet convergence | `*-*-* 04:20:00`, `RandomizedDelaySec=30m`, `Persistent=true` | `foss-setup/configs/ansible/ansible-pull.timer` |
| `restic-backup.service` | mini, rig, betty | oneshot: restic backup → Backblaze B2. `OnFailure=ntfy-notify@%n.service`; `RESTIC_CACHE_DIR=/var/cache/restic` (+ `CacheDirectory=restic`); reads `/etc/restic/env`; `Nice=10`, best-effort IO prio 7 | (via timer) | `foss-setup/scripts/backup/restic-backup.service` |
| `restic-backup.timer` | mini, rig, betty | nightly restic run | `*-*-* 01:30:00`, `RandomizedDelaySec=15m`, `Persistent=true` | `foss-setup/scripts/backup/restic-backup.timer` |
| `ntfy-notify@.service` | any host | templated `OnFailure=` notifier → high-prio ntfy `backups` topic (mini's ntfy). `ExecStart=/opt/scripts/ntfy-notify.sh %i` | on-failure only | `foss-setup/scripts/backup/ntfy-notify@.service` |
| `borgmatic.service` | (Phase 1 — NOT yet deployed) | oneshot: borgmatic/Borg backup → Hetzner Storage Box. Injects `BORG_PASSPHRASE` via `EnvironmentFile=/etc/borgmatic/passphrase.env`; `Nice=10`, best-effort IO prio 7, `LockPersonality=true` | (via timer) | `foss-setup/scripts/backup/borgmatic.service` |
| `borgmatic.timer` | (Phase 1 — NOT yet deployed) | nightly borgmatic, offset from restic | `*-*-* 03:10:00`, `RandomizedDelaySec=20m`, `Persistent=true` | `foss-setup/scripts/backup/borgmatic.timer` |
| `export-manifests.service` | mini (any host) | oneshot: snapshot package/cron/timer/image manifests into the control repo. `REPO_ROOT=/opt/foss-setup`, `STACKS_DIR=/opt/stacks`; optional `NTFY_URL` on failure; `Nice=10` | (via timer) | `foss-setup/scripts/inventory/export-manifests.service` |
| `export-manifests.timer` | mini | weekly manifest export | `Mon *-*-* 04:00:00`, `RandomizedDelaySec=20m`, `Persistent=true` | `foss-setup/scripts/inventory/export-manifests.timer` |
| `verification.service` | mini | oneshot: full homelab verification sweep + LLM triage (`/opt/verification/bin/verify-cycle.sh`). Runs as `btabaska` (needs ssh keys, docker group, passwordless sudo); `TimeoutStartSec=30min`; env `-/etc/verification/env` | (via timer) | `foss-setup/verification/systemd/verification.service` |
| `verification.timer` | mini | daily full sweep | `*-*-* 07:15:00 America/Los_Angeles` (clock is UTC → pinned to local TZ), `Persistent=true`, `RandomizedDelaySec=120` | `foss-setup/verification/systemd/verification.timer` |
| `verification-quick.service` | mini | oneshot: cheap hourly tier — 3 `run-checks.sh` passes (`--host url` incl. rig-ai-e2e, `--host docker-fleet`, `--host media`), all `--notify`; dead-man `ExecStartPost` curl to healthchecks `verification-quick-mini`; `TimeoutStartSec=15min` | (via timer) | `foss-setup/verification/systemd/verification-quick.service` |
| `verification-quick.timer` | mini | hourly quick tier | `*-*-* *:40:00` (:40 offset, clear of 07:15 PT sweep + rig watchdog), `Persistent=true`, `RandomizedDelaySec=120` | `foss-setup/verification/systemd/verification-quick.timer` |
| `wake-rig-listener.service` | mini | long-running ntfy subscriber: wake the rig on demand (recovery topic `wake-rig`). `Restart=always`, `RestartSec=10`, `EnvironmentFile=/etc/wake-rig.env`, `ExecStart=/opt/scripts/wake-rig-listener.sh` | always-on | `foss-setup/configs/systemd/wake-rig-listener.service` |
| `gpu-power-tune.service` | rig | oneshot (`RemainAfterExit=yes`): re-apply NVIDIA power limit + persistence on boot (3090 Ti). `Environment=GPU_POWER_LIMIT=300`, optional `LOCK_CLOCKS=1`; `After=nvidia-persistenced.service` | at boot | `foss-setup/scripts/gaming/gpu-power-tune.service` |
| `display-policy.service` | rig (**user** unit) | dummy-plug when headless / real monitor when present. `Type=simple`, tails `udevadm monitor -u -s drm`, runs `%h/display-policy.sh` on `(drm)` events; `Restart=always`, `WantedBy=graphical-session.target` | always-on (user scope) | `foss-setup/configs/systemd/display-policy.service` |
| `net-selfheal.service` | mini | oneshot: recover NIC `enp3s0f0` after DHCP lease/route loss (`/usr/local/sbin/net-selfheal.sh`, `TimeoutStartSec=90`). See `reference/hosts/mini-network-resilience.md` | (via timer) | `foss-setup/configs/host/mini/net-selfheal/net-selfheal.service` |
| `net-selfheal.timer` | mini | run self-heal every minute | `OnBootSec=90`, `OnUnitActiveSec=60`, `AccuracySec=10s`. See `reference/hosts/mini-network-resilience.md` | `foss-setup/configs/host/mini/net-selfheal/net-selfheal.timer` |
| `apply-static-ip.service` | mini | oneshot: guarded static-IP apply (auto-reverts to DHCP on failure); the script self-disables its timer. See `reference/hosts/mini-network-resilience.md` | (via timer) | `foss-setup/configs/host/mini/static-ip/apply-static-ip.service` |
| `apply-static-ip.timer` | mini | one-shot armed window | `OnCalendar=2026-07-10 08:35:00 UTC` (04:35 EDT), `Persistent=false`, `AccuracySec=1min`; re-arm by editing to a future date. See `reference/hosts/mini-network-resilience.md` | `foss-setup/configs/host/mini/static-ip/apply-static-ip.timer` |
| `ai-stack-watchdog.service` | rig | oneshot: container→host ollama hop → healthchecks dead-man; `EnvironmentFile=/etc/ai-stack-watchdog.env`, `After=docker.service ollama.service`. See `reference/hosts/rig-timers.md` | (via timer) | `foss-setup/configs/host/rig/ai-stack-watchdog/ai-stack-watchdog.service` |
| `ai-stack-watchdog.timer` | rig | every 10 min | `OnCalendar=*:0/10`, `RandomizedDelaySec=30`, `Persistent=true`. See `reference/hosts/rig-timers.md` | `foss-setup/configs/host/rig/ai-stack-watchdog/ai-stack-watchdog.timer` |
| `nas-music-mirror.service` | rig | oneshot: **sole** `~/Music` mirror — FLAC→ALAC (.m4a) transcode + mp3/aac verbatim, prunes orphans (`/home/btabaska/bin/nas-music-to-alac-mirror.sh`); `Nice=10`, IO class idle; `ExecStartPost` pings the `music-mirror-rig` dead-man. See `reference/hosts/rig-timers.md` | (via timer) | `foss-setup/configs/host/rig/music-mirror/nas-music-mirror.service` |
| `nas-music-mirror.timer` | rig | daily ALAC mirror | `*-*-* 05:00:00` (host TZ), `RandomizedDelaySec=300`, `Persistent=true`. See `reference/hosts/rig-timers.md` | `foss-setup/configs/host/rig/music-mirror/nas-music-mirror.timer` |
| ~~`music-mirror.service`/`.timer`~~ | rig | **RETIRED (media-06, 2026-07-14)** — the 05:30 `rsync -rt --delete-after` verbatim mirror copied FLAC to the rig and deleted the ALAC the 05:00 job made. Removed so the rig holds ALAC-only. | — | — |
| `pcie-aer-monitor.service` | rig | oneshot: PCIe AER monitor for OS NVMe (`74:00.0`) → ntfy alert (`/opt/pcie-aer-monitor/pcie-aer-monitor.sh`, `Nice=10`). See `reference/hosts/rig-pcie-aer-monitor.md` | (via timer) | `foss-setup/configs/host/rig/pcie-aer-monitor/pcie-aer-monitor.service` |
| `pcie-aer-monitor.timer` | rig | every 20 min | `OnBootSec=5min`, `OnUnitActiveSec=20min`, `Persistent=true`. See `reference/hosts/rig-pcie-aer-monitor.md` | `foss-setup/configs/host/rig/pcie-aer-monitor/pcie-aer-monitor.timer` |

!!! note "Validated against live mini + rig (2026-07-14)"
    Checked `systemctl is-enabled`/`is-active` for the key units on both hosts.
    **mini:** `ansible-pull.timer`, `restic-backup.timer`, `verification.timer`, `verification-quick.timer`, `net-selfheal.timer`, `export-manifests.timer` all `enabled` + `active`; `wake-rig-listener.service` `enabled` + `active`. `apply-static-ip.timer` is `active` but `is-enabled=disabled` — expected: it is a one-shot armed timer whose apply script disables it on completion (`Persistent=false`). `borgmatic.timer` reported empty `is-enabled` + `inactive` = **not installed on mini** (Phase 1 borgmatic → Hetzner Storage Box not yet deployed).
    **rig:** `ansible-pull.timer`, `restic-backup.timer`, `ai-stack-watchdog.timer`, `music-mirror.timer`, `nas-music-mirror.timer`, `pcie-aer-monitor.timer` all `enabled` + `active`; `gpu-power-tune.service` `enabled` + `active` (`RemainAfterExit`). `display-policy.service` returns `not-found` at **system** scope but is `enabled` under `--user` scope — correct, since it is `WantedBy=graphical-session.target`. `borgmatic.timer` is `not-found` on rig too (**not installed**).

## Host distribution at a glance

- **mini (192.168.10.2)** — control/verification hub: `ansible-pull`, `restic-backup`, `verification`, `verification-quick`, `export-manifests`, `wake-rig-listener`, `net-selfheal`, `apply-static-ip`. `ntfy-notify@` is the shared failure notifier target.
- **rig (192.168.10.12)** — 24/7 since 2026-07-08, GPU/AI/media-mirror host: `ansible-pull`, `restic-backup`, `gpu-power-tune`, `display-policy` (user), `ai-stack-watchdog`, `music-mirror`, `nas-music-mirror`, `pcie-aer-monitor`.
- **betty (seedbox)** — Ansible-managed: `ansible-pull`, `restic-backup` (via role).
- **nas (192.168.10.4)** — Synology, Docker-based (`sonarr radarr lidarr readarr prowlarr unpackerr flaresolverr rreading-glasses soularr beets calibre-web-automated stash immich adguardhome-nas beszel-agent diun`); Plex is a Synology **package**; slskd runs on betty. No systemd fleet units in this repo.

## Deferred / not-yet-deployed

- `borgmatic.service` / `borgmatic.timer` — Phase 1 Borg → Hetzner Storage Box. Source lives in the repo (config-as-code) but confirmed **not installed** on mini or rig as of 2026-07-14. Install recipe (from the unit header): `sudo install -m 644 scripts/backup/borgmatic.{service,timer} /etc/systemd/system/` then create `/etc/borgmatic/passphrase.env` (mode 600) with `BORG_PASSPHRASE=…`, then `systemctl enable --now borgmatic.timer`.

## Dedicated detail pages

The host-specific units are summarized above but documented in full elsewhere — see `reference/hosts/mini-network-resilience.md` (net-selfheal + apply-static-ip), `reference/hosts/rig-pcie-aer-monitor.md` (pcie-aer-monitor), and `reference/hosts/rig-timers.md` (ai-stack-watchdog, music-mirror, nas-music-mirror).

---

[← Host internals reference](index.md)
