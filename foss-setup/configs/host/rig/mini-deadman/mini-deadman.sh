#!/usr/bin/env bash
# mini-deadman.sh — the fleet's OFF-MINI dead-man (fix-63 / SH19).
#
# WHY THIS EXISTS
# The entire alerting/observability plane lives ON mini: ntfy (the pager),
# Healthchecks + Uptime Kuma (both dead-man systems), all three verification
# tiers, Caddy (the sole TLS edge / 62 vhosts), AdGuard primary DNS and the
# Forgejo deploy remote. A dead-man is only meaningful if it lives OUTSIDE the
# thing it watches — so if mini loses power/disk, EVERY self-hosted pager dies
# with it and nothing can say so. This watcher runs on the rig (24/7, off-mini)
# and, on a total mini outage, pages the operator over a channel that never
# touches mini: it publishes DIRECTLY to a topic on the PUBLIC ntfy.sh server —
# the same relay the self-hosted ntfy already uses for iOS push. The phone
# subscribes to that ntfy.sh topic (see README — human follow-up).
#
# no-cloud tradeoff (foss-03): this fleet leans no-cloud. For this ONE
# safety-critical last resort we accept a single public relay, because the
# self-hosted delivery path to an iOS device fundamentally routes through
# ntfy.sh anyway and a whole-house-independent external account would need
# operator signup. The payload is a bare alert (no secrets); the topic name is
# the read secret (vault alerting.mini_deadman_ntfy_topic).
#
# Config: /etc/mini-deadman.env (0600, deployed by hand — see README).
# State:  /var/lib/mini-deadman/{state,heartbeat}
# Detect: TCP connect to mini's Caddy TLS edge (:443). N consecutive failures
#         (default 3 × 5-min timer = ~15 min) => mini is DOWN. Re-page hourly
#         while still down; RECOVERY notice when the edge answers again.
set -uo pipefail

ENV_FILE="${MINI_DEADMAN_ENV:-/etc/mini-deadman.env}"
[ -r "$ENV_FILE" ] && set -a && . "$ENV_FILE" && set +a

MINI_HOST="${MINI_HOST:-192.168.10.2}"
MINI_PORT="${MINI_PORT:-443}"          # Caddy TLS edge — "no https" is the SH19 symptom
PROBE_TIMEOUT="${PROBE_TIMEOUT:-4}"
FAIL_THRESHOLD="${FAIL_THRESHOLD:-3}"  # consecutive fails before paging (blip tolerance)
REPAGE_SECS="${REPAGE_SECS:-3600}"     # re-page interval while still down
NTFY_URL="${MINI_DEADMAN_NTFY_URL:-https://ntfy.sh}"
NTFY_TOPIC="${MINI_DEADMAN_NTFY_TOPIC:-}"
STATE_DIR="${MINI_DEADMAN_STATE_DIR:-/var/lib/mini-deadman}"
FALLBACK_RESOLVERS="${FALLBACK_RESOLVERS:-1.1.1.1 9.9.9.9}"

STATE_FILE="${STATE_DIR}/state"
HEARTBEAT_FILE="${STATE_DIR}/heartbeat"
mkdir -p "$STATE_DIR"
now=$(date +%s)
# Heartbeat every run — the armed/fresh check reads this to prove the watcher runs.
echo "$now" > "$HEARTBEAT_FILE"

if [ -z "$NTFY_TOPIC" ]; then
  echo "mini-deadman: MINI_DEADMAN_NTFY_TOPIC unset (see /etc/mini-deadman.env) — cannot page" >&2
  exit 2
fi

# ---- state helpers (flat key=val file; robust to missing keys) --------------
get() { sed -n "s/^$1=//p" "$STATE_FILE" 2>/dev/null | tail -1; }
status=$(get status);          status="${status:-up}"
consec=$(get consec);          consec="${consec:-0}"
down_since=$(get down_since);  down_since="${down_since:-0}"
last_page=$(get last_page);    last_page="${last_page:-0}"

write_state() {
  { echo "status=$1"; echo "consec=$2"; echo "down_since=$3"; echo "last_page=$4"; } > "$STATE_FILE"
}

# ---- DNS-resilient publish to the public relay -------------------------------
# mini hosts the primary DNS (AdGuard). If mini is down, ntfy.sh may not resolve
# via the normal path, so resolve it explicitly against a public resolver and
# hand curl a pinned --resolve. This keeps the off-mini page independent of mini.
resolve_host() {
  local host="$1" ip
  ip=$(getent ahostsv4 "$host" 2>/dev/null | awk '{print $1; exit}')
  [ -n "$ip" ] && { echo "$ip"; return 0; }
  for r in $FALLBACK_RESOLVERS; do
    ip=$(dig +short +time=3 +tries=1 @"$r" "$host" A 2>/dev/null | grep -E '^[0-9.]+$' | head -1)
    [ -n "$ip" ] && { echo "$ip"; return 0; }
  done
  return 1
}

publish() { # title body priority tags
  local title="$1" body="$2" prio="$3" tags="$4"
  local host ip base="${NTFY_URL#*://}"; host="${base%%/*}"
  local resolve_args=()
  if ip=$(resolve_host "$host"); then resolve_args=(--resolve "${host}:443:${ip}" --resolve "${host}:80:${ip}"); fi
  curl -fsS -m 15 --retry 2 "${resolve_args[@]}" \
    -H "Title: ${title}" -H "Priority: ${prio}" -H "Tags: ${tags}" \
    -d "${body}" "${NTFY_URL}/${NTFY_TOPIC}" -o /dev/null
}

# ---- probe -------------------------------------------------------------------
probe_ok() {
  [ "${MINI_DEADMAN_FORCE_DOWN:-0}" = "1" ] && return 1   # test hook (README/self-test)
  timeout "$PROBE_TIMEOUT" bash -c "exec 3<>/dev/tcp/${MINI_HOST}/${MINI_PORT}" 2>/dev/null
}

if probe_ok; then
  if [ "$status" = "down" ]; then
    dur=$(( (now - down_since) / 60 ))
    publish "mini RECOVERED" \
      "mini's TLS edge (${MINI_HOST}:${MINI_PORT}) answers again after ~${dur} min down. Self-hosted alerting plane back online. (off-mini watcher on rig)" \
      "default" "white_check_mark,mini" || true
    echo "mini-deadman: RECOVERED after ~${dur}m" >&2
  fi
  write_state up 0 0 0
  exit 0
fi

# probe failed
consec=$((consec + 1))
if [ "$status" != "down" ] && [ "$consec" -ge "$FAIL_THRESHOLD" ]; then
  down_since="$now"
  publish "MINI DOWN — self-hosted alerting is dark" \
    "rig cannot reach mini's TLS edge ${MINI_HOST}:${MINI_PORT} (${consec} consecutive probes). If mini is truly down, ALL https vhosts, primary DNS, ntfy, Healthchecks, Uptime Kuma and the verification runner are down with it — no self-hosted pager can report this. This page came from the rig via ntfy.sh (off-mini path). Go check mini." \
    "max" "rotating_light,mini,skull"
  last_page="$now"
  write_state down "$consec" "$down_since" "$last_page"
  echo "mini-deadman: PAGED (mini down, ${consec} consecutive fails)" >&2
  exit 0
fi

if [ "$status" = "down" ]; then
  if [ $((now - last_page)) -ge "$REPAGE_SECS" ]; then
    dur=$(( (now - down_since) / 60 ))
    publish "MINI STILL DOWN (~${dur} min)" \
      "mini's TLS edge ${MINI_HOST}:${MINI_PORT} still unreachable from rig after ~${dur} min. Self-hosted alerting remains dark. (off-mini watcher on rig)" \
      "max" "rotating_light,mini"
    last_page="$now"
    echo "mini-deadman: RE-PAGED (still down ~${dur}m)" >&2
  fi
  write_state down "$consec" "$down_since" "$last_page"
  exit 0
fi

# failing but not yet at threshold (blip) — record and wait for the next run
write_state "$status" "$consec" "$down_since" "$last_page"
echo "mini-deadman: probe failed (${consec}/${FAIL_THRESHOLD}) — below page threshold" >&2
exit 0
