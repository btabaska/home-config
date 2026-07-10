# mini — Ubuntu Docker host (Mac mini)

The always-on hub of the homelab. If one box matters most, it's this one:
Caddy, primary DNS, and Forgejo all live here.

| | |
|---|---|
| **Hardware** | Mac mini Late 2014 (Macmini7,1) — dual-core i5-4278U, **8 GB RAM soldered, non-upgradeable** |
| **OS** | Ubuntu Server 22.04 |
| **IP / aliases** | `192.168.10.2` · SSH alias `mini` · Tailscale `macmini.tailb31641.ts.net` |
| **Power** | 24/7, ~10–15 W under load |
| **Access** | `ssh mini` (Tailscale SSH primary, break-glass key fallback); passwordless sudo for the operator |

## What runs here

The **light always-on web/management stack** (38 containers as of
2026-07-09) under `/opt/stacks`, one directory per compose stack, managed by
Dockge:

- **Edge**: Caddy (owns 80/443, `edge` network, `*.tabaska.us` TLS), AdGuard + Unbound (primary DNS)
- **Life apps**: Miniflux, Wallabag, Navidrome, Mealie, Paperless-ngx, MeTube, Pinchflat, Seerr, MusicSeerr, Libreseerr, RomM (retro-game library)
- **Media polish**: Tautulli, Kometa, Recyclarr (weekly cron, not a resident container). *Maintainerr was removed from the plan 2026-07-08 and never runs here.*
- **Ops**: Homepage, Uptime Kuma, Beszel (+agent), ntfy, Diun, Healthchecks, Dockge
- **Infra**: Forgejo (git — HTTP :3030, `http://macmini.tailb31641.ts.net:3030`), BedrockConnect (console gateway for the Switch, UDP 19132). The mini is also the WoL relay for rig recovery. *No LLM runs here — LiteLLM lives on the [rig](rig.md); the planned mini fallback was never deployed (decision pending).*
- **This wiki**: static site at `/opt/stacks/wiki/site`, served by Caddy at <https://wiki.tabaska.us>

Full generated inventory: [Services](../services/index.md).

## Capacity rule

8 GB is a hard ceiling: **no heavy game servers, no real local LLM, no
Java-heavy or video-detection workloads** (those go to the NAS after its RAM
upgrade, or the rig). At most one light always-on game server. When adding
anything here, check `free -m` first.

## Maintenance channel

- **ansible-pull** (glue-08): systemd timer, daily ~04:20 **UTC** (~00:20 ET)
  ± jitter, pulls Forgejo `home/homelab` into `~/.ansible-pull` and applies
  `site.yml` against itself; dead-manned via Healthchecks `ansible-pull-mini`.
  See [Operations → Ansible](../operations/ansible.md).
- **Dockge** for day-to-day compose stack management; `/opt/stacks` is itself
  a git repo (Forgejo `home/docker-stacks`) — **commit drift immediately**.
- `etckeeper` tracks `/etc`.
- Manual converge / logs:

```bash
ssh mini 'systemctl status ansible-pull.timer'
ssh mini 'sudo systemctl start ansible-pull.service && journalctl -u ansible-pull -n 50'
ssh mini 'cd /opt/stacks && git status --short'   # must be clean
```

## Failure blast radius

If the mini is down: all `*.tabaska.us` names (Caddy), primary DNS (clients
fall to NAS AdGuard then gateway — see [DNS outage](../runbooks/dns-outage.md)),
Forgejo (ansible-pull fetches fail harmlessly), Homepage, and every service
listed above. NAS media serving (Plex/Immich direct ports) survives.
