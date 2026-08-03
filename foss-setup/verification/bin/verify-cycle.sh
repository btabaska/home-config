#!/usr/bin/env bash
# systemd entrypoint: run checks, fire the daily dead-man ping, then bounded LLM
# triage if anything failed.
#
# EXIT 0 IF THE SWEEP RAN (observability-audit fix, 2026-07-14). It used to
# `exit ${rc}` (nonzero when a crit check failed), which had two failure modes:
# (1) it self-poisoned `systemd-failed-mini` (the unit showed FAILED just because
# the fleet was unhealthy), and (2) the dead-man ping was an ExecStartPost, which
# only runs on ExecStart *success* — so a persistent crit failure SKIPPED the ping
# and falsely marked the `verification-mini` Healthchecks dead-man DOWN for days,
# making the one signal meant to prove "the sweep is alive" a false positive.
# Fleet health is reported via ntfy + results.json + the crit-failing checks, NOT
# via this unit's exit code; the unit's only job is to prove the sweep EXECUTED.
# A real non-completion (crash/timeout) still exits nonzero and correctly downs
# the dead-man.
#
# SH8/SH15 (fix-61, 2026-08-02): the dead-man ping now fires HERE — right after
# the sweep writes a fresh results.json and BEFORE triage — instead of as an
# ExecStartPost on verification.service. On 08-01 the LLM-triage phase overran the
# unit's TimeoutStartSec and systemd killed the unit mid-triage; ExecStartPost is
# skipped on a killed run, so the ping never fired and the dead-man falsely flipped
# DOWN for ~12h even though the sweep had fully executed and paged. Firing the ping
# from the script (gated on a successfully-parsed results.json) means a slow or
# killed triage phase can NEVER blind the dead-man, while a genuine non-execution
# (results.json missing/unparseable) still correctly skips the ping and downs it.
# Triage is then bounded (VERIFY_TRIAGE_TIMEOUT, default 20m) so it cannot run
# unbounded and cannot take the whole unit past its start-timeout.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR="${VERIFICATION_STATE_DIR:-/var/lib/verification}"
TRIAGE_TIMEOUT="${VERIFY_TRIAGE_TIMEOUT:-20m}"

"${SCRIPT_DIR}/run-checks.sh" || true

# Did the sweep EXECUTE and write a parseable results.json? Empty => it did not
# (crash before write / corrupt file) and we must NOT ping (let the dead-man down).
failed=$(python3 -c "import json;print(json.load(open('${STATE_DIR}/results.json'))['summary']['failed'])" 2>/dev/null || true)

if [ -n "${failed}" ]; then
  # Sweep executed → fire the daily dead-man ping NOW, before triage (SH8/SH15).
  # URL from the unit's EnvironmentFile (/etc/verification/env); skipped silently
  # on ad-hoc/audit runs where it is unset.
  if [ -n "${VERIFY_DAILY_PING_URL:-}" ]; then
    /usr/bin/curl -fsS -m 10 --retry 3 -o /dev/null "${VERIFY_DAILY_PING_URL}" \
      || echo "verify-cycle: dead-man ping failed (non-fatal)" >&2
  fi
  if [ "${failed}" -gt 0 ]; then
    timeout "${TRIAGE_TIMEOUT}" "${SCRIPT_DIR}/llm-triage.sh" \
      || echo "verify-cycle: llm-triage failed or timed out after ${TRIAGE_TIMEOUT} (non-fatal)" >&2
  fi
else
  echo "verify-cycle: results.json missing/unparseable — the sweep did NOT complete;" \
       "skipping the dead-man ping so verification-mini correctly flips down" >&2
fi
exit 0
