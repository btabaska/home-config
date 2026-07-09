# rig PCIe AER monitor → ntfy

Alerts if the OS NVMe (WD Blue SN570, PCI `0000:74:00.0`, hosts root btrfs + /boot)
resumes PCIe AER errors after the 2026-07-09 fix. See handoff RCA "rig freeze".

**Why rig-local (not in the mini verification runner):** tailnet ACL blocks mini→rig SSH,
so the runner can't read rig's journal. This is a self-contained systemd timer on rig that
counts AER on the current boot and POSTs to ntfy (`verification` topic, same one the runner
uses → same iOS push) only when errors climb (threshold 25 new/interval) or go fatal, or
SMART critical warning != 0x00. Quiet when healthy.

## Files (deployed on rig)
- `/opt/pcie-aer-monitor/pcie-aer-monitor.sh` (root, 0755)
- `/etc/pcie-aer-monitor.env` (0600) — `NTFY_URL`, `NTFY_TOKEN` (vault `ntfy.rig_aer_token`)
- `/etc/systemd/system/pcie-aer-monitor.{service,timer}` — timer every 20 min

## Deploy / redeploy
```
scp pcie-aer-monitor.sh rig:/tmp/ && ssh rig 'sudo install -m0755 /tmp/pcie-aer-monitor.sh /opt/pcie-aer-monitor/'
# env (token from vault):
ssh rig 'sudo install -m0600 /tmp/pcie-aer-monitor.env /etc/pcie-aer-monitor.env'
ssh rig 'sudo systemctl daemon-reload && sudo systemctl enable --now pcie-aer-monitor.timer'
```
Manual run / check: `ssh rig 'sudo systemctl start pcie-aer-monitor.service; journalctl -u pcie-aer-monitor -n5 -o cat'`
