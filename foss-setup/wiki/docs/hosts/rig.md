# rig — CachyOS workstation (on-demand)

The powerful box that **sleeps by default**. Waking it costs ~30 seconds;
idling it 24/7 would cost more per year than the rest of the fleet combined.

| | |
|---|---|
| **Hardware** | i7-12700K · RTX 3090 Ti · 64 GB RAM |
| **OS** | CachyOS (Arch-based) |
| **IP / aliases** | `192.168.10.12` · SSH alias `rig` · Tailscale `cachyos.*.ts.net` |
| **Power** | **On-demand** — Wake-on-LAN + auto-suspend; 400–600 W under load |
| **Access** | Wake first, then `ssh rig` — see [Wake the rig](../runbooks/wake-the-rig.md) |

## What runs here (when awake)

- **Local LLM stack**: Ollama + Open WebUI + mcpo, fronted fleet-wide by
  LiteLLM on the mini (stable URL; falls back to a small always-on model when
  the rig sleeps)
- **Sunshine** game-streaming host (Moonlight clients; pairing UI
  `https://192.168.10.12:47990`)
- **Heavy game servers** on-demand (LinuxGSM); the mini hosts at most one
  light always-on server
- Daily driver desktop / gaming

**GPU contention policy**: one GPU, three jobs — run Ollama with
`keep_alive=0` or don't infer during a stream/game session.

## Power notes & wake procedure

WoL is enabled and verified (wakes in ~30 s). Canonical procedure, timings,
and auto-suspend behavior: [runbooks/wake-the-rig.md](../runbooks/wake-the-rig.md).

`gpu-power-tune.service` caps the 3090 Ti at 300 W and fixes the
stuck-at-idle high-power state. The repo copy of the script is fixed; the
deployed copy on the rig is stale and the service fails at boot
(pending: game-10 — redeploy + `systemctl restart gpu-power-tune`).

## Maintenance channel

**ansible-pull — not yet deployed here** (pending: glue-08 rig half, blocked
on two gates: the `btabaska` sudo password is not in the vault, and the rig's
Forgejo deploy key is unregistered; units are staged at `rig:~/staging/`).
Until then the rig is hand-managed: `pacman` on your own cadence, dotfiles
via chezmoi. Once deployed, the ansible-pull timer here is **wake-gated**
(`OnBootSec` + `Persistent=true`, no wall-clock schedule — a sleeping box
misses every window).

## Failure blast radius

Rig down/asleep is the **normal state** — nothing critical depends on it.
LiteLLM transparently falls back; game streaming and heavy servers simply
require a wake first.
