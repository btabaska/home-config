# `mc-bedrock-ping.py`

> RakNet unconnected ping — what a Bedrock client sends to list a server.

**Path:** `foss-setup/scripts/gaming/mc-bedrock-ping.py` · **Category:** [Gaming & streaming](index.md) · **Type:** Python

## Synopsis

```
mc-bedrock-ping.py <host> <port>
```

## What it does

```text
RakNet unconnected ping — what a Bedrock client sends to list a server.

Covers the playit UDP path (bedrock.tabaska.us:1111), which shares the
wedged-claim failure mode found on TCP 2026-07-09: agent says "connected,
tunnels loaded" while no data flows. Only a real protocol ping sees it.

Usage: mc-bedrock-ping.py <host> <port>
Prints the pong MOTD fields on success, exits 1 on failure.
Deployed to mini:/opt/verification/bin/ for the verification sweep
(check playit-bedrock-public in checks.d/rig.yaml).
```

## See also

- [`apollo-enable.sh`](apollo-enable-sh.md)
- [`display-policy.sh`](display-policy-sh.md)
- [`enable-wol-cachyos.sh`](enable-wol-cachyos-sh.md)
- [`gpu-power-tune.sh`](gpu-power-tune-sh.md)
- [`mc-status-ping.py`](mc-status-ping-py.md)
- [`wake-rig-listener.sh`](wake-rig-listener-sh.md)
- [`wake-rig-recovery.sh`](wake-rig-recovery-sh.md)
- [`wake-rig-via-mini.sh`](wake-rig-via-mini-sh.md)
- [`wake-rig.sh`](wake-rig-sh.md)
- [Gaming & streaming scripts](index.md) · [All scripts](../index.md)
