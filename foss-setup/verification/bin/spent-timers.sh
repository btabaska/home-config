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
# service is STILL RUNNING/STARTING, systemd reports that timer's NEXT as n/a (the
# next elapse is not scheduled until the unit settles). This check runs INSIDE the
# verification units, so it saw its OWN verification.timer / verification-fast.timer
# (NEXT=n/a, LAST set) as "spent" — a chronic false positive that filed fix-39 to
# the reopen ledger and burned an LLM triage slot. A timer whose activated unit
# ($NF, the ACTIVATES column) is in ANY in-flight state is NOT spent — skip it.
#
# fix-61 followup (2026-08-03): the exclusion originally matched only `active`, but
# a oneshot service mid-run reports `activating` (not `active`) — verification-fast
# is `activating` for its whole run window — so it still false-flagged. Treat every
# in-flight state (active/activating/reloading/deactivating) as "in flight". Only a
# settled service (inactive/failed) means its timer is genuinely spent.
set -u
bad=""
while read -r line; do
  unit=$(awk '{print $(NF-1)}' <<<"$line")   # UNIT column (the timer)
  svc=$(awk '{print $NF}' <<<"$line")         # ACTIVATES column (its service)
  case "$(systemctl is-active "$svc" 2>/dev/null || true)" in
    active|activating|reloading|deactivating) continue ;;  # in flight → NEXT=n/a is transient
  esac
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
