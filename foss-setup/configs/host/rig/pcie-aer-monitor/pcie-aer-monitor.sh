#!/usr/bin/env bash
# pcie-aer-monitor: alert via ntfy if the OS NVMe (WD SN570 @ 0000:74:00.0) resumes
# PCIe AER errors after the 2026-07-09 APST/ASPM fix (nvme_core.default_ps_max_latency_us=0
# + pcie_aspm=off). Runs from a systemd timer on rig, as root. Quiet when healthy.
# See handoff-rollout-state.md "RCA: rig freeze ... NVMe PCIe link instability".
set -uo pipefail

PCI="0000:74:00.0"                       # stable addr of the OS drive (nvmeX name is NOT stable)
ENVF="/etc/pcie-aer-monitor.env"
STATE_DIR="/var/lib/pcie-aer-monitor"
STATE="$STATE_DIR/state"
mkdir -p "$STATE_DIR"

# shellcheck disable=SC1090
[ -r "$ENVF" ] && . "$ENVF"
NTFY_URL="${NTFY_URL:-https://ntfy.tabaska.us/verification}"
NTFY_TOKEN="${NTFY_TOKEN:-}"
THRESH="${AER_THRESHOLD:-25}"            # new correctable errors per interval before alerting

boot_id="$(cat /proc/sys/kernel/random/boot_id)"
corr=$(journalctl -b 0 -k --no-pager 2>/dev/null | grep "PCIe Bus Error" | grep -c "$PCI")
fatal=$(journalctl -b 0 -k --no-pager 2>/dev/null | grep "$PCI" | grep -Ec "severity=(Fatal|Uncorrected)")

# resolve the nvme node for this PCI addr (name reshuffles across boots)
node=""
for d in /sys/class/nvme/nvme*; do
  [ "$(cat "$d/address" 2>/dev/null)" = "$PCI" ] && node="$(basename "$d")"
done
critwarn="unknown"; model="?"
if [ -n "$node" ]; then
  model=$(tr -s ' ' < "/sys/class/nvme/$node/model" 2>/dev/null)
  cw=$(smartctl -H -A "/dev/$node" 2>/dev/null | awk -F: '/Critical Warning/{gsub(/ /,"",$2);print $2}')
  [ -n "$cw" ] && critwarn="$cw"
fi

prev_boot=""; prev_corr=0
if [ -r "$STATE" ]; then prev_boot=$(sed -n 1p "$STATE"); prev_corr=$(sed -n 2p "$STATE"); fi

alert=""; prio="default"
if [ "$boot_id" != "$prev_boot" ]; then
  # reboot → reset baseline; only alert if errors are already high right after boot
  if [ "$fatal" -gt 0 ]; then alert="Post-boot: $fatal FATAL/uncorrectable PCIe errors on $PCI."; prio="urgent";
  elif [ "$corr" -ge "$THRESH" ]; then alert="Post-boot: $corr correctable PCIe AER already on $PCI (fix may have regressed)."; prio="high"; fi
else
  delta=$(( corr - prev_corr )); [ "$delta" -lt 0 ] && delta=0
  if [ "$fatal" -gt 0 ]; then alert="UNCORRECTABLE/fatal PCIe errors ($fatal) on $PCI — link may be dropping."; prio="urgent";
  elif [ "$delta" -ge "$THRESH" ]; then alert="PCIe correctable AER climbing: +$delta since last check ($corr total this boot) on $PCI."; prio="high"; fi
fi
if [ "$critwarn" != "0x00" ] && [ "$critwarn" != "unknown" ]; then
  alert="${alert:+$alert }SMART critical warning=$critwarn on $PCI."; prio="urgent"
fi

printf '%s\n%s\n%s\n' "$boot_id" "$corr" "$(date -Is)" > "$STATE"

if [ -n "$alert" ] && [ -n "$NTFY_TOKEN" ]; then
  body="$alert
Drive: $model ($node @ $PCI) — hosts the OS/root filesystem.
Correctable(this boot)=$corr  fatal=$fatal  SMART_crit=$critwarn
The 2026-07-09 NVMe APST/ASPM fix appears to be regressing. Reseat/replace the SN570 or migrate the OS. See handoff RCA."
  curl -s -m 12 \
    -H "Authorization: Bearer $NTFY_TOKEN" \
    -H "Title: rig NVMe PCIe errors ($PCI)" \
    -H "Priority: $prio" \
    -H "Tags: warning,floppy_disk" \
    -d "$body" "$NTFY_URL" >/dev/null && echo "alerted: $alert" || echo "ntfy send failed"
else
  echo "ok: corr=$corr fatal=$fatal crit=$critwarn (no alert)"
fi
