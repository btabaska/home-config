# `gpu-power-tune.sh`

> -  RTX 3090 Ti idle/load power tuning on CachyOS (Linux)

**Path:** `foss-setup/scripts/gaming/gpu-power-tune.sh` · **Category:** [Gaming & streaming](index.md) · **Type:** Bash

## What it does

```text
 gpu-power-tune.sh  --  RTX 3090 Ti idle/load power tuning on CachyOS (Linux)

 WHY: A 3090 Ti can sit at a high idle clock and burn ~100-130W doing nothing,
 and pulls ~450W under load. This script:
   1. Enables persistence mode so the driver stays loaded and our settings
      don't reset when the last client exits (clocks/offsets otherwise reset).
   2. Applies a conservative POWER LIMIT (watts) to cap peak draw + heat/noise
      with minimal FPS loss.
   3. (Optional) Locks the GPU clock range. On Linux, NVIDIA exposes NO direct
      voltage control. The community "indirect undervolt" trick = lock the max
      clock + apply a positive clock OFFSET so the card hits the same clock at
      a lower voltage. The offset step needs Coolbits/pynvml and is documented
      in the runbook below rather than auto-applied (it's per-card and risky).

 SAFETY:
   - Power limit is clamped to the card's reported Min..Max range. We never set
     below Min (would be rejected) or above Max.
   - Clock locking is OFF by default (LOCK_CLOCKS=0). Enable only after testing.
   - Undervolt offsets can CRASH the GPU/driver if too aggressive. Start small
     (e.g. +100 MHz), test under load, increase gradually. See runbook.

 Docs:
   - nvidia-smi reference (-pm, -pl, -lgc): https://docs.nvidia.com/deploy/nvidia-smi/index.html
   - Power limits & undervolting on Linux:   https://hbfreed.com/2026/03/12/power-limits-undervolting.html
   - nvuv (indirect undervolt tool):         https://github.com/doums/nvuv
   - NVIDIA undervolt discussion:            https://github.com/NVIDIA/open-gpu-kernel-modules/discussions/236

 Usage:
   sudo ./gpu-power-tune.sh                 # persistence + default power limit
   sudo GPU_POWER_LIMIT=300 ./gpu-power-tune.sh
   sudo LOCK_CLOCKS=1 LOCK_GC_MIN=210 LOCK_GC_MAX=1800 ./gpu-power-tune.sh

 Idempotent: re-running just re-applies the same state. set -euo pipefail.
```

## Environment / variables referenced

`EUID`, `GPU_ID`, `GPU_POWER_LIMIT`, `LOCK_CLOCKS`, `LOCK_GC_MAX`, `LOCK_GC_MIN`, `MAX_PL`, `MIN_PL`

## See also

- [`apollo-enable.sh`](apollo-enable-sh.md)
- [`display-policy.sh`](display-policy-sh.md)
- [`enable-wol-cachyos.sh`](enable-wol-cachyos-sh.md)
- [`mc-bedrock-ping.py`](mc-bedrock-ping-py.md)
- [`mc-status-ping.py`](mc-status-ping-py.md)
- [`wake-rig-listener.sh`](wake-rig-listener-sh.md)
- [`wake-rig-recovery.sh`](wake-rig-recovery-sh.md)
- [`wake-rig-via-mini.sh`](wake-rig-via-mini-sh.md)
- [`wake-rig.sh`](wake-rig-sh.md)
- [Gaming & streaming scripts](index.md) · [All scripts](../index.md)
