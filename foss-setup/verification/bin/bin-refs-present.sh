#!/usr/bin/env bash
# bin-refs-present.sh — CLASS guard for the deploy-drift bug (M38/M53).
#
# Every /opt/verification/bin/<x> that a check cmd references must actually exist
# on disk. The quality-gate bug: committed checks (rig.yaml playit-*-public) and
# a service called scripts that lived only on the host, so the documented
# `rsync -a --delete` deploy would have deleted them and broken the checks — a
# failure invisible until the check silently errored. This probes the LIVE
# checks.d against the LIVE bin, so ANY future "check references a script the
# deploy didn't stage" is caught the next sweep. Prints BIN_REFS_OK / a list of
# MISSING_BIN_REF:<path> lines then BIN_REFS_INCOMPLETE.
set -uo pipefail
CHECKS_DIR="${1:-/opt/verification/checks.d}"
miss=0
refs="$(grep -rhoE '/opt/verification/bin/[A-Za-z0-9._-]+' "$CHECKS_DIR" 2>/dev/null | sort -u || true)"
for r in $refs; do
  if [ ! -e "$r" ]; then echo "MISSING_BIN_REF:$r"; miss=1; fi
done
if [ "$miss" = 0 ]; then
  echo "BIN_REFS_OK ($(printf '%s\n' "$refs" | grep -c . ) referenced scripts present)"
else
  echo "BIN_REFS_INCOMPLETE"
fi
