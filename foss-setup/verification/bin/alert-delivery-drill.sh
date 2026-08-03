#!/usr/bin/env bash
# alert-delivery-drill.sh — synthetic "did a page actually reach a device?" drill
# (fix-63 / SM39, mandate 2).
#
# WHY: every alerting check proves publishes SUCCEED server-side, but nothing
# proves the last mile — a silently logged-out phone app or a broken iOS upstream
# relay looks identical to a healthy one. This drill exercises the SAME path real
# alerts use: publish to the self-hosted ntfy, which relays to the iOS device via
# ntfy.sh. It goes to a DEDICATED low-priority topic (alert-drill) so drills never
# masquerade as real alerts and can be routed/muted separately on the phone.
#
# The SEND is automated and freshness-checked (alert-delivery-drill-fresh). The
# RECEIPT is an operator human-confirm: the phone is subscribed to `alert-drill`
# (phone user already has read-* on the self-hosted server); the operator sees the
# timestamped drill and confirms once. A future closed-loop upgrade: an iOS
# Shortcut automation that, on receiving the drill, pings a Healthchecks dead-man
# so receipt becomes machine-verifiable (documented in the alerting runbook).
set -uo pipefail

ENV_FILE="${VERIFICATION_ENV_FILE:-/etc/verification/env}"
[ -r "$ENV_FILE" ] && set -a && . "$ENV_FILE" && set +a

STATE_DIR="${VERIFICATION_STATE_DIR:-/var/lib/verification}"
NTFY_BASE="${NTFY_URL:-http://127.0.0.1:8080/verification}"
NTFY_SERVER="${NTFY_BASE%/*}"                       # strip the topic path
DRILL_TOPIC="${ALERT_DRILL_TOPIC:-alert-drill}"
NTFY_TOKEN="${NTFY_TOKEN:-}"
STATE_FILE="${STATE_DIR}/alert-drill-last"

mkdir -p "$STATE_DIR"
stamp=$(date -Is)
nonce=$(date +%s)

if [ -z "$NTFY_TOKEN" ]; then
  echo "alert-delivery-drill: NTFY_TOKEN unset (vault ntfy.* admin token in /etc/verification/env)" >&2
  exit 2
fi

msg="ALERT DELIVERY DRILL ${stamp} (nonce ${nonce}). If you can read this on your phone, the ntfy->iOS-relay->device path is alive. This is a synthetic test (fix-63/SM39); no action needed. Confirm receipt per the alerting runbook."

if curl -fsS -m 12 --retry 2 \
     -H "Authorization: Bearer ${NTFY_TOKEN}" \
     -H "Title: Alert delivery drill" \
     -H "Priority: low" \
     -H "Tags: test_tube,bell" \
     -d "$msg" "${NTFY_SERVER}/${DRILL_TOPIC}" -o /dev/null; then
  printf 'sent_at=%s\nnonce=%s\n' "$stamp" "$nonce" > "$STATE_FILE"
  echo "alert-delivery-drill: sent to ${NTFY_SERVER}/${DRILL_TOPIC} at ${stamp}" >&2
  exit 0
else
  echo "alert-delivery-drill: publish FAILED — server-side send did not succeed" >&2
  exit 1
fi
