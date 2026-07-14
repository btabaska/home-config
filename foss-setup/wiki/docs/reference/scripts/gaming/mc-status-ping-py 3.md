# `mc-status-ping.py`

> Real Minecraft Java status ping (handshake + status, protocol 1.7+).

**Path:** `foss-setup/scripts/gaming/mc-status-ping.py` · **Category:** [Gaming & streaming](index.md) · **Type:** Python

## Synopsis

```
mc-status-ping.py <host> <port> [handshake-hostname]
```

## What it does

```text
Real Minecraft Java status ping (handshake + status, protocol 1.7+).

Why not a bare TCP probe: the playit edge intermittently refuses/ignores
no-data connects (verified 2026-07-09: a Kuma TCP monitor on 69.9.181.17
flapped while real client pings succeeded every time). This speaks the actual
protocol a Java client uses, so green means friends can really reach it.

Usage: mc-status-ping.py <host> <port> [handshake-hostname]
  handshake-hostname defaults to <host>; pass minecraft.tabaska.us when
  probing the playit edge by IP so hostname-based routing still matches.
Prints the status JSON (truncated) on success, exits 1 on any failure.
Deployed to mini:/opt/verification/bin/ for the verification sweep
(check playit-java-public in checks.d/rig.yaml).
```

## See also

- [`apollo-enable.sh`](apollo-enable-sh.md)
- [`display-policy.sh`](display-policy-sh.md)
- [`enable-wol-cachyos.sh`](enable-wol-cachyos-sh.md)
- [`gpu-power-tune.sh`](gpu-power-tune-sh.md)
- [`mc-bedrock-ping.py`](mc-bedrock-ping-py.md)
- [`wake-rig-listener.sh`](wake-rig-listener-sh.md)
- [`wake-rig-recovery.sh`](wake-rig-recovery-sh.md)
- [`wake-rig-via-mini.sh`](wake-rig-via-mini-sh.md)
- [`wake-rig.sh`](wake-rig-sh.md)
- [Gaming & streaming scripts](index.md) · [All scripts](../index.md)
