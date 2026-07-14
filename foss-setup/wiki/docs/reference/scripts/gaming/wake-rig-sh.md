# `wake-rig.sh`

> Rig is 24/7 since 2026-07 — this is RECOVERY tooling (power outage / accidental shutdown), not workflow.

**Path:** `foss-setup/scripts/gaming/wake-rig.sh` · **Category:** [Gaming & streaming](index.md) · **Type:** Bash

## Synopsis

```
(from repo, any LAN device with wakeonlan installed):
```

## What it does

```text
 Rig is 24/7 since 2026-07 — this is RECOVERY tooling (power outage / accidental shutdown), not workflow.

 wake-rig.sh
 Send a Wake-on-LAN magic packet to the CachyOS rig on the Trusted VLAN.

 Config (no shell exports needed):
   configs/gaming/rig-wol.env  — RIG_MAC (committed fleet constant)
   RIG_BCAST is auto-detected from this machine's default-route subnet.

 Usage (from repo, any LAN device with wakeonlan installed):
   ./scripts/gaming/wake-rig.sh

 From anywhere on the tailnet (mini is always on the same L2 segment as the rig):
   ./scripts/gaming/wake-rig-via-mini.sh
   ssh mini 'bash ~/wake-rig.sh'

 Overrides (optional):
   RIG_MAC=aa:bb:... RIG_BCAST=192.168.10.255 ./wake-rig.sh
   WOL_CONFIG=/path/to/rig-wol.env ./wake-rig.sh

 Docs:
   - Arch Wiki Wake-on-LAN:      https://wiki.archlinux.org/title/Wake-on-LAN
   - Ubuntu WakeOnLan community: https://help.ubuntu.com/community/WakeOnLan

 Idempotent + safe: set -euo pipefail.
```

## Environment / variables referenced

`IFACE`, `RIG_BCAST`, `RIG_MAC`, `SCRIPT_DIR`, `WOL_CONFIG`

## See also

- [`apollo-enable.sh`](apollo-enable-sh.md)
- [`display-policy.sh`](display-policy-sh.md)
- [`enable-wol-cachyos.sh`](enable-wol-cachyos-sh.md)
- [`gpu-power-tune.sh`](gpu-power-tune-sh.md)
- [`mc-bedrock-ping.py`](mc-bedrock-ping-py.md)
- [`mc-status-ping.py`](mc-status-ping-py.md)
- [`wake-rig-listener.sh`](wake-rig-listener-sh.md)
- [`wake-rig-recovery.sh`](wake-rig-recovery-sh.md)
- [`wake-rig-via-mini.sh`](wake-rig-via-mini-sh.md)
- [Gaming & streaming scripts](index.md) · [All scripts](../index.md)
