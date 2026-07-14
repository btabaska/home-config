# rig — PCIe AER monitor → ntfy

> A self-contained systemd timer on the rig that watches the OS NVMe's PCIe Advanced Error Reporting (AER) counters and SMART critical-warning flag, pinging ntfy only when errors climb, go fatal, or SMART flags a problem.

_Source: `foss-setup/configs/host/rig/pcie-aer-monitor/README.md`, `foss-setup/configs/host/rig/pcie-aer-monitor/pcie-aer-monitor.service`, `foss-setup/configs/host/rig/pcie-aer-monitor/pcie-aer-monitor.timer` · migrated + validated 2026-07-14_

## Why this exists

The rig's OS drive — a **WD Blue SN570 NVMe**, PCI address **`0000:74:00.0`**, hosting the root btrfs and `/boot` — has a marginal PCIe link that **froze the box on 2026-07-09**. An APST/ASPM kernel fix was applied after that incident. This monitor is the watchdog that alerts if the drive resumes PCIe AER errors after the fix. See the handoff RCA "rig freeze".

!!! note "Validated against live rig (2026-07-14)"
    `lspci -s 74:00.0` on the rig reports the device at `0000:74:00.0` as a "Non-Volatile memory controller: Sandisk Corp SanDisk Extreme Pro / WD Black 2018/SN750/PC SN720 NVMe SSD" (the SN570 shares WD/SanDisk controller IDs). `/sys/bus/pci/devices/0000:74:00.0` exists, confirming the sysfs path the monitor reads.

## Why rig-local (not in the mini verification runner)

AER counters and SMART data live in the rig's kernel log / sysfs and need **privileged local access** — an HTTP probe from the mini can't see them (the "which vantage sees this break?" rule). mini→rig SSH does work now, so the runner *could* shell in, but a self-contained rig-local watcher is the right vantage.

## What it does

- Runs as a systemd **timer every 20 minutes** on the rig.
- Counts AER on the current boot and **POSTs to ntfy** only when:
  - errors climb (threshold **25 new/interval**), or
  - errors go **fatal**, or
  - SMART **critical warning != `0x00`**.
- Sends to the ntfy **`verification` topic** — the same one the mini verification runner uses → same iOS push.
- **Quiet when healthy** (no alert on a clean interval).

## Files (deployed on rig)

| Path | Perms | Purpose |
| --- | --- | --- |
| `/opt/pcie-aer-monitor/pcie-aer-monitor.sh` | root, `0755` | The monitor script |
| `/etc/pcie-aer-monitor.env` | `0600` | `NTFY_URL`, `NTFY_TOKEN` (vault key `ntfy.rig_aer_token`) |
| `/etc/systemd/system/pcie-aer-monitor.service` | — | oneshot unit |
| `/etc/systemd/system/pcie-aer-monitor.timer` | — | timer, every 20 min |

!!! note "Validated against live rig (2026-07-14)"
    On the rig: `/opt/pcie-aer-monitor/pcie-aer-monitor.sh` exists (3297 bytes, `-rwxr-xr-x` root, dated 2026-07-09) and `/etc/pcie-aer-monitor.env` exists (`-rw-------` root, 90 bytes, dated 2026-07-09). Both match the documented paths and permissions.

## systemd unit definitions

`pcie-aer-monitor.service`:

```ini
[Unit]
Description=PCIe AER monitor for OS NVMe (74:00.0) -> ntfy alert
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/opt/pcie-aer-monitor/pcie-aer-monitor.sh
Nice=10
```

`pcie-aer-monitor.timer`:

```ini
[Unit]
Description=Run PCIe AER monitor every 20 min

[Timer]
OnBootSec=5min
OnUnitActiveSec=20min
Persistent=true

[Install]
WantedBy=timers.target
```

## Deploy / redeploy

```bash
scp pcie-aer-monitor.sh rig:/tmp/ && ssh rig 'sudo install -m0755 /tmp/pcie-aer-monitor.sh /opt/pcie-aer-monitor/'
# env (token from vault):
ssh rig 'sudo install -m0600 /tmp/pcie-aer-monitor.env /etc/pcie-aer-monitor.env'
ssh rig 'sudo systemctl daemon-reload && sudo systemctl enable --now pcie-aer-monitor.timer'
```

Manual run / check:

```bash
ssh rig 'sudo systemctl start pcie-aer-monitor.service; journalctl -u pcie-aer-monitor -n5 -o cat'
```

!!! note "Validated against live rig (2026-07-14)"
    `systemctl is-enabled pcie-aer-monitor.timer` → **`enabled`**. The timer is **active (waiting)** since 2026-07-09 (boot after the fix), triggering `pcie-aer-monitor.service` with ~10 min to next run at the time of check. The last service run exited `0/SUCCESS` (`Mem peak: 4.4M`, `CPU: 119ms`) and logged: `ok: corr=0 fatal=0 crit=0x00 (no alert)` — confirming the healthy/quiet path is working end to end. Note the journal was rotated since the unit started, so full boot history may be incomplete.

---

[← Host internals reference](index.md)
