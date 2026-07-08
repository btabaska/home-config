# Runbook — Recover the rig (Wake-on-LAN)

The rig ([hosts/rig](../hosts/rig.md)) runs **24/7** (decision 2026-07-08).
If it's unreachable, that's an **incident** — most likely a power outage or
an accidental shutdown — and this runbook brings it back. WoL is retained as
recovery tooling only (verified 2026-07-07: woke in ~30 s from a magic
packet); it is not part of any routine workflow, and there is no
auto-suspend to fight.

## Bring it back

```bash
# From the MacBook / any LAN host (wakeonlan: brew install wakeonlan)
wakeonlan <rig-MAC>            # or: wol <rig-MAC> / etherwake <rig-MAC>

# Then wait and connect (~30 s typical)
until ssh -o ConnectTimeout=3 rig true 2>/dev/null; do sleep 3; done
ssh rig
```

The rig's MAC is in the inventory (`configs/inventory/inventory.md`) — WoL is
enabled in BIOS (game-08). Other recovery paths:

- **Moonlight/Sunshine**: opening a stream to the rig sends WoL itself once
  paired.
- **Home Assistant**: a WoL switch entity (pending: ha track) — recover the
  rig from a dashboard.
- **Off-LAN**: WoL is broadcast-only; trigger it via another LAN host over
  Tailscale: `ssh mini 'wakeonlan <rig-MAC>'`.

If the magic packet doesn't bring it up, it's a physical problem (breaker,
PSU, hung board) — go press the button.

## After recovery — what to expect

- Tailscale reconnects on its own; `ssh rig` works via alias.
- Ollama serves once up; LiteLLM on the mini resumes routing big-model
  requests to the rig automatically (it will have been on the small
  mini-fallback model while the rig was down).
- `gpu-power-tune.service` should cap the GPU at 300 W — currently failing at
  boot (pending: game-10); check `nvidia-smi` if the room gets warm.
- Once rig ansible-pull lands (pending: glue-08), `Persistent=true` catches
  up any converge window missed while the box was down.

## Verify

```bash
ping -c1 192.168.10.12 && ssh rig 'uptime && nvidia-smi --query-gpu=power.limit --format=csv'
```

Host answers, SSH works, power limit reads 300 W (or you've found game-10
still open). Then ask *why* it was down — a 24/7 host going dark deserves a
root cause, not just a wake.
