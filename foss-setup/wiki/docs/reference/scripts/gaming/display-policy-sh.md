# `display-policy.sh`

> Single-display policy. HDMI-A-1 = dummy plug (headless fallback). If a REAL

**Path:** `foss-setup/scripts/gaming/display-policy.sh` · **Category:** [Gaming & streaming](index.md) · **Type:** Bash

## What it does

```text
 Single-display policy. HDMI-A-1 = dummy plug (headless fallback). If a REAL
 monitor is connected on any other output, switch to it and drop the dummy in
 ONE atomic kscreen-doctor call; else keep the dummy as the sole display.
```

## Environment / variables referenced

`DUMMY`, `LOG`

## See also

- [`apollo-enable.sh`](apollo-enable-sh.md)
- [`enable-wol-cachyos.sh`](enable-wol-cachyos-sh.md)
- [`gpu-power-tune.sh`](gpu-power-tune-sh.md)
- [`mc-bedrock-ping.py`](mc-bedrock-ping-py.md)
- [`mc-status-ping.py`](mc-status-ping-py.md)
- [`wake-rig-listener.sh`](wake-rig-listener-sh.md)
- [`wake-rig-recovery.sh`](wake-rig-recovery-sh.md)
- [`wake-rig-via-mini.sh`](wake-rig-via-mini-sh.md)
- [`wake-rig.sh`](wake-rig-sh.md)
- [Gaming & streaming scripts](index.md) · [All scripts](../index.md)
