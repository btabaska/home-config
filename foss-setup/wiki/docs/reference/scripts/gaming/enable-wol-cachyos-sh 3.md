# `enable-wol-cachyos.sh`

> Rig is 24/7 since 2026-07 — this is RECOVERY tooling (power outage / accidental shutdown), not workflow.

**Path:** `foss-setup/scripts/gaming/enable-wol-cachyos.sh` · **Category:** [Gaming & streaming](index.md) · **Type:** Bash

## What it does

```text
 Rig is 24/7 since 2026-07 — this is RECOVERY tooling (power outage / accidental shutdown), not workflow.

 enable-wol-cachyos.sh
 Persistently enable Wake-on-LAN (magic packet) on the CachyOS rig's wired NIC,
 so the rig can be remotely powered back on after an unexpected power-off.

 WoL has two halves: (1) BIOS/UEFI must allow "Wake on PCIe/LAN" / "Power On By
 PCI-E" AND disable deep ErP/EuP power-off that cuts power to the NIC; (2) the OS
 must arm the NIC with `ethtool -s <nic> wol g` on every boot. `ethtool` settings
 do NOT survive a reboot on most systems, so we install a templated systemd unit
 that re-arms the NIC at boot.

 Docs:
   - Arch Wiki Wake-on-LAN:        https://wiki.archlinux.org/title/Wake-on-LAN
   - Ubuntu WakeOnLan community:   https://help.ubuntu.com/community/WakeOnLan

 Idempotent: safe to re-run. set -euo pipefail for strict error handling.
```

## Environment / variables referenced

`EUID`, `UNIT_PATH`, `WOL_NIC`

## See also

- [`apollo-enable.sh`](apollo-enable-sh.md)
- [`display-policy.sh`](display-policy-sh.md)
- [`gpu-power-tune.sh`](gpu-power-tune-sh.md)
- [`mc-bedrock-ping.py`](mc-bedrock-ping-py.md)
- [`mc-status-ping.py`](mc-status-ping-py.md)
- [`wake-rig-listener.sh`](wake-rig-listener-sh.md)
- [`wake-rig-recovery.sh`](wake-rig-recovery-sh.md)
- [`wake-rig-via-mini.sh`](wake-rig-via-mini-sh.md)
- [`wake-rig.sh`](wake-rig-sh.md)
- [Gaming & streaming scripts](index.md) · [All scripts](../index.md)
