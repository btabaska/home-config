# rig — CachyOS workstation

The powerful box, now **on 24/7** (decision 2026-07-08): ~130 W idle
(≈ $23/mo) accepted as the price of availability. Idle-power tuning is an
open task; Wake-on-LAN is kept purely as recovery tooling.

| | |
|---|---|
| **Hardware** | i7-12700K · RTX 3090 Ti · 64 GB RAM |
| **OS** | CachyOS (Arch-based) |
| **IP / aliases** | `192.168.10.12` · SSH alias `rig` · Tailscale `cachyos.*.ts.net` |
| **Power** | **24/7** — ~130 W idle (accepted 2026-07-08; idle-power-tuning open), 400–600 W under load |
| **Access** | `ssh rig` any time. Unreachable = incident — see [Recover the rig](../runbooks/wake-the-rig.md) |

## What runs here

- **Local LLM stack** — all ON THIS HOST (compose in the separate
  `local-ai-tooling` repo, `~/Documents/GitHub/local-ai-tooling/docker`):
  native Ollama (`:11434`) + **LiteLLM** gateway (`:4000`,
  [llm.tabaska.us](https://llm.tabaska.us), with its postgres sidecar) +
  Open WebUI ([ai.tabaska.us](https://ai.tabaska.us)) + mcpo.
  *There is no LiteLLM on the mini* — a mini-hosted front-door/fallback was
  planned but never deployed (stack dir exists; decision pending 2026-07-09).
- **Apollo** game-streaming host — a maintained Sunshine fork (AUR `apollo`),
  chosen over stock Sunshine for headless/virtual-display support and
  per-client permissions on this 24/7 headless box. Drop-in for Moonlight
  clients on the same ports; pairing UI `https://192.168.10.12:47990`
- **Game servers** (compose stacks in `/opt/stacks`): [AMP](../services/amp.md)
  panel (`amp.tabaska.us`, MinecraftCross Java+Bedrock),
  [Palworld](../services/palworld.md) ("Robits Farm"), and the
  [playit](../services/playit.md) tunnel agent for the public game paths
  (dedicated IP 69.9.181.17). Not LinuxGSM — that stayed a research note.
- **Agents & timers**: beszel-agent (metrics), `ai-stack-watchdog.timer`
  (10-min container→host-ollama probe → Healthchecks `ai-stack-rig`),
  `pcie-aer-monitor.timer`, `ansible-pull.timer`, `restic-backup.timer`
- Daily driver desktop / gaming

**GPU contention policy**: one GPU, three jobs — run Ollama with
`keep_alive=0` or don't infer during a stream/game session.

## Power & recovery

The rig runs 24/7 with **no auto-suspend**. WoL remains enabled and verified
(wakes in ~30 s) as **recovery tooling only** — power outage, accidental
shutdown — not part of any workflow:
[runbooks/wake-the-rig.md](../runbooks/wake-the-rig.md).

`gpu-power-tune.service` caps the 3090 Ti at 300 W and fixes the
stuck-at-idle high-power state — deployed and working (verified 2026-07-09:
active, exit 0, 300 W + persistence mode; the hardened script from the repo
is what's on disk).

**Known hardware issue**: the OS NVMe (WD SN570 @ `74:00.0`) has a marginal
PCIe link that froze the box on 2026-07-08. APST/ASPM kernel workaround is
applied and `pcie-aer-monitor.timer` (20-min) watches for AER errors → ntfy.
A physical reseat/replacement is still open — if the box hard-freezes with
nothing in monitoring, suspect this first.

## Firewall (UFW)

UFW is active with default-deny incoming, rules scoped to LAN
(`192.168.10.0/24`) + tailnet (`100.64.0.0/10`). Tailscale traffic arrives via
`tailscaled`'s own iptables chains and **bypasses UFW entirely** — a service
can be tailnet-reachable while LAN-blocked (this hid the Apollo outage below).

Live rule inventory (2026-07-19; rules are hand-applied — update this table
when you touch them):

| ports | proto | from | purpose |
|---|---|---|---|
| SSH, KDE Connect | tcp/udp | anywhere | remote admin / device pairing |
| 8765 | tcp | LAN, 172.16/12, 10.201/16 | beszel agent |
| 11434 | tcp | LAN, tailnet, 172.16/12 | ollama shim (see gotcha below) |
| 47984,47989,47990,48010 | tcp | LAN | Apollo/Moonlight web+pairing+RTSP |
| 47998:48002 | udp | LAN | Apollo/Moonlight video/control/audio/mic |

**History:** the 2026-07-16 lockdown omitted the Apollo ports — LAN game
streaming (and the caddy `apollo.tabaska.us` vhost) was dead for 3 days while
tailnet checks stayed green; re-allowed 2026-07-19 (operator decision, fix-45
close-out). **Gotcha (bit us
2026-07-09)**: docker containers reaching services on the *host* (e.g.
open-webui/litellm → native Ollama via `host.docker.internal:11434`) arrive
from `172.x` and hit the INPUT chain — LAN/tailnet-scoped rules do NOT cover
them. Symptom: ai.tabaska.us "no models available" while every external port
probe stays green. Fix in place: `ufw allow from 172.16.0.0/12 to any port
11434 proto tcp`. If a new host-native service needs container access, it
needs its own `172.16.0.0/12` rule. Caught by verification check
`rig-ai-e2e` (real completion through litellm).

## Maintenance channel

**ansible-pull is deployed and running here** (verified 2026-07-09:
`ansible-pull.timer` active, daily ~04:40 ET, dead-manned via Healthchecks
`ansible-pull-rig`). Packages remain `pacman` on your own cadence (Arch —
ansible does not do OS upgrades here), dotfiles via chezmoi.

## Failure blast radius

Rig down is an **incident** (since 2026-07-08 this is a 24/7 host). Blast
radius: the whole AI surface (ai/llm/ollama/mcpo.tabaska.us — there is **no
fallback**; the planned mini fallback was never deployed), all game servers
and their public playit paths, and game streaming. Nothing else in the
fleet depends on it. Detection: Kuma rig monitors + `ai-stack-rig`
dead-man + `rig-ai-e2e` in the sweep.
