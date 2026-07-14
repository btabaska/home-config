#!/usr/bin/env bash
# systemd entrypoint: run checks, then LLM triage if anything failed.
#
# EXIT 0 IF THE SWEEP RAN (observability-audit fix, 2026-07-14). It used to
# `exit ${rc}` (nonzero when a crit check failed), which had two failure modes:
# (1) it self-poisoned `systemd-failed-mini` (the unit showed FAILED just because
# the fleet was unhealthy), and (2) the dead-man ping is an ExecStartPost, which
# only runs on ExecStart *success* — so a persistent crit failure SKIPPED the ping
# and falsely marked the `verification-mini` Healthchecks dead-man DOWN for days,
# making the one signal meant to prove "the sweep is alive" a false positive.
# Fleet health is reported via ntfy + results.json + the crit-failing checks, NOT
# via this unit's exit code; the unit's only job is to prove the sweep EXECUTED.
# A real non-completion (crash/timeout) still exits nonzero and correctly downs
# the dead-man.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR="${VERIFICATION_STATE_DIR:-/var/lib/verification}"

"${SCRIPT_DIR}/run-checks.sh" || true

failed=$(python3 -c "import json;print(json.load(open('${STATE_DIR}/results.json'))['summary']['failed'])" 2>/dev/null || echo 0)
if [ "${failed}" -gt 0 ]; then
  "${SCRIPT_DIR}/llm-triage.sh" || echo "llm-triage failed (non-fatal)" >&2
fi
exit 0
