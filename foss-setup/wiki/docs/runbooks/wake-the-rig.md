# Runbook — Wake the rig

The rig ([hosts/rig](../hosts/rig.md)) sleeps by default. Waking it is
routine, verified working (2026-07-07: woke in ~30 s from a magic packet).

## Wake it

```bash
# From the MacBook / any LAN host (wakeonlan: brew install wakeonlan)
wakeonlan <rig-MAC>            # or: wol <rig-MAC> / etherwake <rig-MAC>

# Then wait and connect (~30 s typical)
until ssh -o ConnectTimeout=3 rig true 2>/dev/null; do sleep 3; done
ssh rig
```

The rig's MAC is in the inventory (`configs/inventory/inventory.md`) — WoL is
enabled in BIOS (game-08). Other wake paths:

- **Moonlight/Sunshine**: opening a stream to the rig sends WoL itself once
  paired.
- **Home Assistant**: a WoL switch entity (pending: ha track) — "wake the
  rig" from a dashboard or a heavy-LLM automation.
- **Off-LAN**: WoL is broadcast-only; wake via another LAN host over
  Tailscale: `ssh mini 'wakeonlan <rig-MAC>'`.

## After wake — what to expect

- Tailscale reconnects on its own; `ssh rig` works via alias.
- Ollama serves once up; LiteLLM on the mini starts routing big-model
  requests to the rig automatically (falls back again when it sleeps).
- `gpu-power-tune.service` should cap the GPU at 300 W — currently failing at
  boot (pending: game-10); check `nvidia-smi` if the room gets warm.
- Once rig ansible-pull lands (pending: glue-08), a converge fires ~3 min
  after each wake (`OnBootSec` + `Persistent=true`).

## Auto-suspend

The rig suspends itself after idle — **that is the design, don't fight it**.
For a long unattended job, use a systemd inhibitor so it stays awake exactly
as long as the job runs:

```bash
systemd-inhibit --what=sleep --why="long job" <command>
```

## Verify

```bash
ping -c1 192.168.10.12 && ssh rig 'uptime && nvidia-smi --query-gpu=power.limit --format=csv'
```

Host answers, SSH works, power limit reads 300 W (or you've found game-10
still open).
