#!/usr/bin/env bash
#
# ntfy-notify.sh <failed-unit> — push a failure alert to the ntfy `backups` topic.
# Wired as OnFailure=ntfy-notify@%n.service on restic-backup.service (mini + rig).
#
# Credentials: sources (in order, later wins for NTFY_* if set in both)
#   /etc/verification/env  (mini — already holds NTFY_URL + NTFY_TOKEN)
#   /etc/restic/env        (rig  — NTFY_URL/NTFY_TOKEN copied in at deploy time)
# NTFY_URL may point at any topic (e.g. .../verification); the last path segment
# is replaced with the `backups` topic.

set -euo pipefail

UNIT="${1:-unknown-unit}"
HOST="$(hostname -s)"

set -a
[[ -r /etc/verification/env ]] && . /etc/verification/env
[[ -r /etc/restic/env ]] && . /etc/restic/env
set +a

: "${NTFY_URL:?NTFY_URL not set (need /etc/verification/env or /etc/restic/env)}"
: "${NTFY_TOKEN:?NTFY_TOKEN not set (need /etc/verification/env or /etc/restic/env)}"

TOPIC_URL="${NTFY_URL%/*}/backups"

curl -fsS -m 15 \
  -H "Authorization: Bearer ${NTFY_TOKEN}" \
  -H "Title: ${UNIT} FAILED on ${HOST}" \
  -H "Priority: high" \
  -H "Tags: rotating_light,floppy_disk" \
  -d "${UNIT} failed on ${HOST} at $(date -Is). Check: journalctl -u ${UNIT} -n 50" \
  "${TOPIC_URL}" >/dev/null
