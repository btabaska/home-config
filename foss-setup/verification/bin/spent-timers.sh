#!/usr/bin/env bash
# spent-timers.sh — flag systemd timers that will NEVER fire again (NEXT=n/a)
# but HAVE fired before (LAST set) and are still enabled or active.
#
# M3 class (fix-39): media-window-maint.timer was a one-shot with a past
# OnCalendar and Persistent=false — it ran once, FAILED, and sat enabled with
# NEXT=n/a forever, so the failed maintenance silently never rescheduled.
# Dormant stock timers (apport-autoreport, snapd.snap-repair: LAST=n/a, armed
# by events, never scheduled) are NOT spent — LAST!=n/a is the discriminator.
set -u
bad=""
while read -r line; do
  unit=$(awk '{print $(NF-1)}' <<<"$line")
  en=$(systemctl is-enabled "$unit" 2>/dev/null || true)
  act=$(systemctl is-active "$unit" 2>/dev/null || true)
  if [[ "$en" == "enabled" || "$act" == "active" ]]; then
    bad="$bad $unit"
  fi
done < <(systemctl list-timers --all --no-legend --plain 2>/dev/null | awk '$1=="n/a" && $3!="n/a"')
if [[ -z "$bad" ]]; then
  echo "SPENT_ENABLED=NONE"
else
  echo "SPENT_ENABLED=${bad# }"
fi
