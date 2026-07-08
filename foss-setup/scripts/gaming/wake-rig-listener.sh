#!/usr/bin/env bash
# Long-poll the ntfy 'wake-rig' topic; fire the recovery WoL on each message.
set -uo pipefail
: "${PHONE_PW:?}"
curl -s -u "phone:${PHONE_PW}" -N "http://localhost:8080/wake-rig/json" | \
while read -r line; do
  case "$line" in
    *'"event":"message"'*) /opt/scripts/wake-rig-recovery.sh ;;
  esac
done
