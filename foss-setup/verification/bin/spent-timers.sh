#!/usr/bin/env bash
# spent-timers.sh — flag systemd timers that will NEVER fire again (NEXT=n/a)
# but HAVE fired before (LAST set) and are still enabled or active.
#
# M3 class (fix-39): media-window-maint.timer was a one-shot with a past
# OnCalendar and Persistent=false — it ran once, FAILED, and sat enabled with
# NEXT=n/a forever, so the failed maintenance silently never rescheduled.
# Dormant stock timers (apport-autoreport, snapd.snap-repair: LAST=n/a, armed
# by events, never scheduled) are NOT spent — LAST!=n/a is the discriminator.
#
# Self-observation guard (SM22, fix-61, 2026-08-02): while a timer's activated
# oneshot service is STILL RUNNING, systemd reports that timer's NEXT as n/a (the
# next elapse is not scheduled until the unit deactivates). This check runs INSIDE
# verification.service, so every daily sweep it saw its OWN verification.timer
# (NEXT=n/a, LAST set) as "spent" — a chronic false positive that filed fix-39 to
# the reopen ledger daily and burned an LLM triage slot. A timer whose activated
# unit ($NF, the ACTIVATES column) is currently active is NOT spent — skip it.
set -u
bad=""
while read -r line; do
  unit=$(awk '{print $(NF-1)}' <<<"$line")   # UNIT column (the timer)
  svc=$(awk '{print $NF}' <<<"$line")         # ACTIVATES column (its service)
  if [[ "$(systemctl is-active "$svc" 2>/dev/null || true)" == "active" ]]; then
    continue   # timer's own run is in flight → NEXT=n/a is transient, not spent
  fi
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
