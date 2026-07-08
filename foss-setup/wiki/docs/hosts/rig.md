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

- **Local LLM stack**: Ollama + Open WebUI + mcpo, fronted fleet-wide by
  LiteLLM on the mini (stable URL; its small always-on fallback model is
  pure resilience now — if you're on the fallback, the rig is down and
  that's an incident)
- **Sunshine** game-streaming host (Moonlight clients; pairing UI
  `https://192.168.10.12:47990`)
- **Heavy game servers** (LinuxGSM); the mini hosts at most one light
  always-on server
- Daily driver desktop / gaming

**GPU contention policy**: one GPU, three jobs — run Ollama with
`keep_alive=0` or don't infer during a stream/game session.

## Power & recovery

The rig runs 24/7 with **no auto-suspend**. WoL remains enabled and verified
(wakes in ~30 s) as **recovery tooling only** — power outage, accidental
shutdown — not part of any workflow:
[runbooks/wake-the-rig.md](../runbooks/wake-the-rig.md).

`gpu-power-tune.service` caps the 3090 Ti at 300 W and fixes the
stuck-at-idle high-power state. The repo copy of the script is fixed; the
deployed copy on the rig is stale and the service fails at boot
(pending: game-10 — redeploy + `systemctl restart gpu-power-tune`).

## Maintenance channel

**ansible-pull — not yet deployed here** (pending: glue-08 rig half, blocked
on two gates: the `btabaska` sudo password is not in the vault, and the rig's
Forgejo deploy key is unregistered; units are staged at `rig:~/staging/`).
Until then the rig is hand-managed: `pacman` on your own cadence, dotfiles
via chezmoi. Once deployed, the ansible-pull timer here runs the standard
wall-clock schedule (`OnCalendar`) like every other host — `Persistent=true`
is just the generic catch-up for any missed window.

## Failure blast radius

Rig down is an **incident** (since 2026-07-08 this is a 24/7 host), though a
soft one: LiteLLM falls back to the mini's small model, and game streaming /
heavy servers are simply unavailable until it's recovered. Nothing else in
the fleet depends on it.
